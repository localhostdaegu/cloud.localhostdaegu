"""로컬/외부 임베더 비교 하네스 — 같은 코퍼스·같은 질문으로 후보 모델을 나란히 평가 (CLI).

운영 DB 컬럼이 vector(1536) 고정이라 1024·2560차원 벡터는 저장할 수 없다. 그래서 이 하네스는
DB 밖에서 돈다: rag_chunk의 텍스트만 읽어 후보별로 전량 임베딩한 뒤 numpy 코사인으로 순위를 매긴다.
문서 벡터는 data/eval/cache/에 캐시해 재실행 시 임베딩을 반복하지 않는다.

- gemini-embedding-001은 MRL이라 지정 차원 벡터 == 3072 벡터의 앞부분(2026-09-18 실측 cos 1.0).
  API 호출을 아끼기 위해 3072만 호출하고 2560·1536·1024는 잘라서(정규화) 만든다.
- 지표: Top-1·Recall@5·MRR(evaluate_rag와 동일 정의)·쿼리 임베딩 p50 ms·문서 임베딩 처리량.
- 교차 일치(로컬 ↔ 같은 차원 Gemini, 그리고 ↔ gemini@3072): Top-1 일치율·Jaccard@5·Spearman ρ.
- 운영 검색의 만료 공고 제외(exclude_expired_funding)는 적용하지 않는다 — 모델 비교가 목적.

실행: python -m apps.rag.adapter.inbound.cli.compare_embedders [--evalset data/eval/rag_evalset.jsonl]
      [--candidates gemini@3072,gemini@2560,gemini-api@2560,qwen@2560,...]
  gemini@<dim>는 3072 절단 파생, gemini-api@<dim>은 API에 output_dimensionality를 직접 지정한 실호출.
"""

import argparse
import json
import statistics
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import numpy as np
from sqlalchemy import select

from apps.rag.adapter.inbound.cli.evaluate_rag import _load_evalset, _resolve, mrr, recall_at_k
from apps.rag.adapter.outbound.embeddings.gemini_embedding_adapter import GeminiEmbeddingAdapter
from apps.rag.adapter.outbound.embeddings.ollama_bge_m3_adapter import OllamaBgeM3EmbeddingAdapter
from apps.rag.adapter.outbound.embeddings.ollama_qwen3_adapter import OllamaQwen3EmbeddingAdapter
from apps.rag.adapter.outbound.orms.rag_chunk_orm import RagChunkOrm
from apps.rag.app.ports.output.rag_port import EmbeddingPort
from core.matrix.grid_oracle_database_manager import session_scope

_TOP_K = 10

# 실제 임베더를 호출하는 후보 — 이름 → 어댑터 팩토리 (dict 디스패치)
_ADAPTER_CANDIDATES: dict[str, Callable[[], EmbeddingPort]] = {
    "gemini@3072": lambda: GeminiEmbeddingAdapter(output_dimensionality=3072),
    # API에 차원을 직접 지정한 후보 — 로컬과 같은 차원에서 실호출로 비교 (절단 파생 후보와 등가성 검증 겸용)
    "gemini-api@2560": lambda: GeminiEmbeddingAdapter(output_dimensionality=2560),
    "gemini-api@1024": lambda: GeminiEmbeddingAdapter(output_dimensionality=1024),
    "qwen@2560": lambda: OllamaQwen3EmbeddingAdapter(dimensions=2560),
    "qwen@1536": lambda: OllamaQwen3EmbeddingAdapter(dimensions=1536),
    "bge-m3@1024": lambda: OllamaBgeM3EmbeddingAdapter(),
}
# 상위 후보 벡터를 잘라 만드는 후보 — 이름 → (원본 후보, 차원)
_DERIVED_CANDIDATES: dict[str, tuple[str, int]] = {
    "gemini@2560": ("gemini@3072", 2560),
    "gemini@1536": ("gemini@3072", 1536),
    "gemini@1024": ("gemini@3072", 1024),
}
# 교차 일치 비교 짝 — (로컬, 같은 차원 Gemini)
_PAIRS = [
    ("qwen@2560", "gemini@2560"),
    ("qwen@1536", "gemini@1536"),
    ("bge-m3@1024", "gemini@1024"),
    ("qwen@2560", "gemini-api@2560"),
    ("bge-m3@1024", "gemini-api@1024"),
    ("gemini-api@2560", "gemini@2560"),  # 실호출 vs 절단 파생 — 등가성
    ("gemini-api@1024", "gemini@1024"),
]
_REFERENCE = "gemini@3072"
_DEFAULT_ORDER = [
    "gemini@3072", "gemini@2560", "gemini-api@2560", "qwen@2560", "gemini@1536", "qwen@1536",
    "gemini@1024", "gemini-api@1024", "bge-m3@1024",
]


# ---------- 순수 함수 ----------


def truncate_normalize(vectors: np.ndarray, dim: int) -> np.ndarray:
    out = vectors[:, :dim]
    return out / np.linalg.norm(out, axis=1, keepdims=True)


def rank_documents(
    query: np.ndarray,
    docs: np.ndarray,
    ids: list[str],
    source_types: list[str],
    source_type: str | None,
    top_k: int,
) -> list[str]:
    """코사인 내림차순 상위 top_k chunk_id — 운영 검색처럼 source_type으로 거른다."""
    q = query / np.linalg.norm(query)
    scores = docs @ q
    mask = np.array([st == source_type for st in source_types]) if source_type else np.ones(len(ids), bool)
    scores = np.where(mask, scores, -np.inf)
    order = np.argsort(-scores)[:top_k]
    return [ids[i] for i in order if np.isfinite(scores[i])]


def jaccard_at_k(a: list[str], b: list[str], k: int) -> float:
    sa, sb = set(a[:k]), set(b[:k])
    return len(sa & sb) / len(sa | sb) if sa | sb else 0.0


def spearman_rho(x: np.ndarray, y: np.ndarray) -> float:
    rx, ry = np.argsort(np.argsort(x)), np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])


# ---------- 코퍼스·캐시 ----------


def _load_corpus() -> tuple[list[str], list[str], list[str]]:
    with session_scope() as session:
        rows = session.execute(
            select(RagChunkOrm.chunk_id, RagChunkOrm.source_type, RagChunkOrm.content)
            .order_by(RagChunkOrm.chunk_id)
        ).all()
    return [r.chunk_id for r in rows], [r.source_type for r in rows], [r.content for r in rows]


def _embed_corpus_cached(
    name: str, embedder: EmbeddingPort, ids: list[str], contents: list[str], cache_dir: Path
) -> tuple[np.ndarray, dict]:
    cache_path = cache_dir / f"{name.replace('@', '_')}.npz"
    if cache_path.exists():
        cached = np.load(cache_path, allow_pickle=False)
        if list(cached["ids"]) == ids:
            meta = json.loads(str(cached["meta"]))
            meta["cached"] = True
            return cached["vectors"], meta
    started = time.monotonic()
    vectors = np.array(embedder.embed_documents(contents), dtype=np.float32)
    elapsed = time.monotonic() - started
    meta = {
        "model_name": embedder.model_name,
        "doc_embed_seconds": round(elapsed, 1),
        "docs_per_second": round(len(contents) / elapsed, 1),
        "cached": False,
    }
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.savez(cache_path, ids=np.array(ids), vectors=vectors, meta=json.dumps(meta))
    return vectors, meta


# ---------- 평가 ----------


def _evaluate_candidate(
    name: str, docs: np.ndarray, queries: np.ndarray, rows: list[dict], ids, source_types
) -> dict:
    per_row = []
    for row, q in zip(rows, queries, strict=True):
        relevant = set(row["relevant_ids"])
        ranked = rank_documents(q, docs, ids, source_types, row.get("source_type"), _TOP_K)
        per_row.append(
            {
                "question": row["question"],
                "source_type": row.get("source_type"),
                "top1": 1.0 if ranked[:1] and ranked[0] in relevant else 0.0,
                "recall_at_5": recall_at_k(relevant, ranked, 5),
                "mrr": mrr(relevant, ranked),
                "ranked": ranked,
            }
        )
    return {"name": name, "per_row": per_row, "summary": _summarize(per_row)}


def _summarize(per_row: list[dict]) -> dict:
    def block(items):
        return {
            "n": len(items),
            "top1": round(statistics.fmean(r["top1"] for r in items), 3) if items else None,
            "recall_at_5": round(statistics.fmean(r["recall_at_5"] for r in items), 3) if items else None,
            "mrr": round(statistics.fmean(r["mrr"] for r in items), 3) if items else None,
        }

    by_source = {}
    for st in sorted({r["source_type"] for r in per_row}):
        by_source[st] = block([r for r in per_row if r["source_type"] == st])
    return {"all": block(per_row), "by_source_type": by_source}


def _agreement(a: dict, b: dict, docs_a: np.ndarray, docs_b: np.ndarray, qa: np.ndarray, qb: np.ndarray, source_types) -> dict:
    top1, jac5, rhos = [], [], []
    for ra, rb, va, vb in zip(a["per_row"], b["per_row"], qa, qb, strict=True):
        top1.append(1.0 if ra["ranked"][:1] == rb["ranked"][:1] else 0.0)
        jac5.append(jaccard_at_k(ra["ranked"], rb["ranked"], 5))
        mask = np.array([st == ra["source_type"] for st in source_types])
        rhos.append(spearman_rho(docs_a[mask] @ (va / np.linalg.norm(va)), docs_b[mask] @ (vb / np.linalg.norm(vb))))
    return {
        "top1_agreement": round(statistics.fmean(top1), 3),
        "jaccard_at_5": round(statistics.fmean(jac5), 3),
        "spearman_rho": round(statistics.fmean(rhos), 3),
    }


def _embed_queries_timed(embedder: EmbeddingPort, questions: list[str]) -> tuple[np.ndarray, float]:
    vectors, latencies = [], []
    for q in questions:
        started = time.perf_counter()
        vectors.append(embedder.embed_query(q))
        latencies.append((time.perf_counter() - started) * 1000)
    return np.array(vectors, dtype=np.float32), round(statistics.median(latencies), 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evalset", default="data/eval/rag_evalset.jsonl")
    parser.add_argument("--candidates", default=",".join(_DEFAULT_ORDER))
    parser.add_argument("--cache-dir", default="data/eval/cache")
    args = parser.parse_args()

    names = [n.strip() for n in args.candidates.split(",") if n.strip()]
    rows = _load_evalset(_resolve(args.evalset))
    questions = [r["question"] for r in rows]
    ids, source_types, contents = _load_corpus()
    cache_dir = _resolve(args.cache_dir)
    print(f"corpus {len(ids)}건, evalset {len(rows)}건, candidates {names}", flush=True)

    docs: dict[str, np.ndarray] = {}
    queries: dict[str, np.ndarray] = {}
    meta: dict[str, dict] = {}
    # 1) 실제 어댑터 후보 — 파생 후보의 원본이 먼저 필요하므로 어댑터 후보를 먼저 돈다
    for name in names:
        if name not in _ADAPTER_CANDIDATES:
            continue
        embedder = _ADAPTER_CANDIDATES[name]()
        docs[name], meta[name] = _embed_corpus_cached(name, embedder, ids, contents, cache_dir)
        queries[name], meta[name]["query_p50_ms"] = _embed_queries_timed(embedder, questions)
        print(f"  {name}: docs {docs[name].shape} {meta[name]}", flush=True)
    # 2) 파생 후보 — 원본을 잘라 정규화
    for name in names:
        if name not in _DERIVED_CANDIDATES:
            continue
        parent, dim = _DERIVED_CANDIDATES[name]
        if parent not in docs:
            raise SystemExit(f"{name}의 원본 후보 {parent}가 candidates에 없다")
        docs[name] = truncate_normalize(docs[parent], dim)
        queries[name] = truncate_normalize(queries[parent], dim)
        meta[name] = {"derived_from": parent, "dim": dim, "query_p50_ms": meta[parent]["query_p50_ms"]}
    # 문서 벡터는 코사인용으로 정규화(Gemini 지정 차원 응답은 정규화돼 있지 않다)
    for name in docs:
        docs[name] = docs[name] / np.linalg.norm(docs[name], axis=1, keepdims=True)

    results = {n: _evaluate_candidate(n, docs[n], queries[n], rows, ids, source_types) for n in names if n in docs}
    agreements = {}
    for local, remote in _PAIRS + [(n, _REFERENCE) for n in names if n != _REFERENCE]:
        if local in results and remote in results:
            agreements[f"{local} vs {remote}"] = _agreement(
                results[local], results[remote], docs[local], docs[remote], queries[local], queries[remote], source_types
            )

    print("\n| 후보 | dim | Top-1 | Recall@5 | MRR | funding Top-1 | news Top-1 | 쿼리 p50 ms | 문서 docs/s |")
    print("|---|---|---|---|---|---|---|---|---|")
    for n in names:
        if n not in results:
            continue
        s = results[n]["summary"]
        f = s["by_source_type"].get("funding", {})
        nw = s["by_source_type"].get("news", {})
        print(
            f"| {n} | {docs[n].shape[1]} | {s['all']['top1']} | {s['all']['recall_at_5']} | {s['all']['mrr']} "
            f"| {f.get('top1')} | {nw.get('top1')} | {meta[n]['query_p50_ms']} | {meta[n].get('docs_per_second', '—')} |"
        )
    print("\n| 비교 짝 | Top-1 일치 | Jaccard@5 | Spearman ρ |")
    print("|---|---|---|---|")
    for k, v in agreements.items():
        print(f"| {k} | {v['top1_agreement']} | {v['jaccard_at_5']} | {v['spearman_rho']} |")

    results_dir = _resolve("data/eval/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = results_dir / f"embed_compare_{timestamp}.json"
    out_path.write_text(
        json.dumps(
            {
                "timestamp": timestamp,
                "evalset": str(_resolve(args.evalset)),
                "corpus_size": len(ids),
                "candidates": {n: {"meta": meta[n], "summary": results[n]["summary"]} for n in results},
                "agreements": agreements,
                "per_row": {n: results[n]["per_row"] for n in results},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n결과 저장: {out_path}", flush=True)


if __name__ == "__main__":
    main()
