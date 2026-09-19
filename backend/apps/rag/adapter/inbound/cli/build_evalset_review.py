"""RAG 평가셋 검수 시트 생성 — 질문·정답 청크 원문·만료 여부·현재 검색 적중 여부를 나란히 놓는다.

산출 2개(data/eval/review/):
  rag_evalset_review.md  — 사람이 읽는 시트(정답 청크 전문, 오답 시 현재 1위 청크 첫 줄)
  rag_evalset_review.csv — 판정 기입용(verdict / revised_question / note). 적용은 apply_evalset_review.

실행: python -m apps.rag.adapter.inbound.cli.build_evalset_review
      [--evalset data/eval/rag_evalset.jsonl] [--results <embed_compare json>] [--candidate gemini-api@2560]
"""

import argparse
import csv
import json
from pathlib import Path

from sqlalchemy import select

from apps.funding.adapter.outbound.orms.funding_program_orm import FundingProgramOrm
from apps.rag.adapter.outbound.orms.rag_chunk_orm import RagChunkOrm
from core.matrix.grid_oracle_database_manager import session_scope

_REPO_ROOT = Path(__file__).resolve().parents[6]
_OUT_DIR = _REPO_ROOT / "data" / "eval" / "review"

_GUIDE = """# RAG 평가셋 검수 시트

기준: **질문만 읽고 이 정답 청크를 찾으려는 사람이 실제로 할 법한 질문인가**, 그리고 **코퍼스 안에서 이 청크가 유일한 정답인가**.

| verdict | 뜻 | 기입 |
|---|---|---|
| `confirm` | 질문·정답 그대로 승격 | verdict만 |
| `revise` | 질문을 고쳐 승격 | verdict + `revised_question` |
| `reject` | 평가셋에서 제외(정답이 모호·중복·질문 불가) | verdict (+note) |
| 빈칸 | 보류(candidate 유지) | — |

판정은 `rag_evalset_review.csv`에 적고 `python -m apps.rag.adapter.inbound.cli.apply_evalset_review`로 반영한다.
"만료" 표시 공고는 운영 검색의 만료 필터에 걸려 정답이 나올 수 없다 — 평가셋에는 두되(필터 OFF 평가용) 새 표본을 미만료 공고에서 뽑을 때 참고.
"검색 1위" 열은 {candidate} 결과({results})의 현재 순위다. 오답이면 1위 청크의 첫 줄을 같이 보여 준다 — 질문이 두 문서에 다 맞으면 `reject` 또는 `revise`.

"""


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _fetch_chunks(chunk_ids: set[str]) -> tuple[dict[str, str], dict[str, tuple[bool, str]]]:
    """chunk_id → content, funding program_id → (is_expired, deadline)."""
    with session_scope() as session:
        rows = session.execute(
            select(RagChunkOrm.chunk_id, RagChunkOrm.content).where(RagChunkOrm.chunk_id.in_(chunk_ids))
        ).all()
        contents = {r.chunk_id: r.content for r in rows}
        program_ids = [c.split(":", 1)[1] for c in chunk_ids if c.startswith("funding:")]
        expiry = {
            f"funding:{r.program_id}": (bool(r.is_expired), str(r.deadline or ""))
            for r in session.execute(
                select(FundingProgramOrm.program_id, FundingProgramOrm.is_expired, FundingProgramOrm.deadline)
                .where(FundingProgramOrm.program_id.in_(program_ids))
            ).all()
        }
    return contents, expiry


def _first_line(text: str, width: int = 80) -> str:
    line = (text or "").splitlines()[0] if text else ""
    return line if len(line) <= width else line[: width - 1] + "…"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evalset", default="data/eval/rag_evalset.jsonl")
    parser.add_argument("--results", default="data/eval/results/embed_compare_20260918_230428.json")
    parser.add_argument("--candidate", default="gemini-api@2560")
    args = parser.parse_args()

    evalset = _load_jsonl(_REPO_ROOT / args.evalset)
    per_row = json.load((_REPO_ROOT / args.results).open(encoding="utf-8"))["per_row"][args.candidate]
    ranked_by_q = {r["question"]: r["ranked"] for r in per_row}

    wanted = {row["relevant_ids"][0] for row in evalset} | {r[0] for r in ranked_by_q.values() if r}
    contents, expiry = _fetch_chunks(wanted)

    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    md = [_GUIDE.format(candidate=args.candidate, results=Path(args.results).name)]
    csv_rows = []
    for no, row in enumerate(evalset, 1):
        cid = row["relevant_ids"][0]
        ranked = ranked_by_q.get(row["question"], [])
        hit = "1위 적중" if ranked and ranked[0] == cid else ("상위5 안" if cid in ranked[:5] else "상위5 밖")
        expired, deadline = expiry.get(cid, (False, ""))
        tags = [row["source_type"], cid, f"검색 {hit}"] + ([f"만료({deadline})"] if expired else [])
        md.append(f"### {no}. " + " · ".join(tags) + "\n\n")
        md.append(f"**질문**: {row['question']}\n\n**정답 청크**:\n\n")
        md.append("".join(f"> {line}\n" for line in (contents.get(cid) or "(청크 없음 — 색인에서 사라짐)").splitlines()))
        if ranked and ranked[0] != cid:
            md.append(f"\n**현재 1위(오답)**: `{ranked[0]}` — {_first_line(contents.get(ranked[0], ''))}\n")
        md.append("\n---\n\n")
        csv_rows.append({
            "no": no, "source_type": row["source_type"], "chunk_id": cid, "expired": "Y" if expired else "",
            "search": hit, "question": row["question"], "verdict": "", "revised_question": "", "note": "",
        })

    (_OUT_DIR / "rag_evalset_review.md").write_text("".join(md), encoding="utf-8")
    with (_OUT_DIR / "rag_evalset_review.csv").open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)
    expired_n = sum(1 for r in csv_rows if r["expired"])
    print(f"검수 시트 {len(csv_rows)}건 (만료 공고 {expired_n}) → {_OUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
