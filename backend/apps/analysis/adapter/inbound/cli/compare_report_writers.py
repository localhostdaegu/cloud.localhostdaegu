"""리포트 작성기 비교 하네스 — 온라인(Gemini)·오프라인(Ollama) LLM에 같은 시스템 지시·프롬프트를 주고 게이트로 잰다.

입력은 운영 에이전트(build_agents)로 실제 DB에서 채운 AnalysisContext 3개(review 재무 있음·review 재무 없음·handoff)와
verdict 방향 일치 짝(위험 등급 red/green 치환). LLM 섹션(verdict·market·shock·funding·plan·questions)의 프롬프트는
report_sections·report_text 를 그대로 쓴다.

게이트(결정론, LLM-as-judge 없음):
- 완료(예외·빈 출력 없음) / '#' 제목 금지 / 불릿·문장·질문 수 상한 / 대괄호 인용 금지
- 숫자 환각: 프롬프트에 없는 2자리 이상 숫자 / 인용 환각: 「」 제목이 문서 제목과 맞지 않음 / 한국어 비율
- 방향 일치(PCA): red 짝은 첫 문장이 주의·위험, green 짝은 양호·안정
- 지연: 첫 조각(TTFT)·총 시간 p50, Ollama eval tok/s
- VRAM 동주: qwen3-embedding:4b(2560)를 먼저 올려 두고 LLM 실행 뒤 /api/ps 에 둘 다 남는지

실행: python -m apps.analysis.adapter.inbound.cli.compare_report_writers [--repeat 2] [--candidates gemini,gemma4:12b,...]
"""

import argparse
import dataclasses
import json
import re
import statistics
import subprocess
import time
from datetime import datetime
from pathlib import Path

import httpx
from google import genai

from apps.analysis.adapter.outbound.llm.gemini_report_writer import GeminiReportWriter
from apps.analysis.adapter.outbound.llm.ollama_report_writer import OllamaReportWriter
from apps.analysis.app.use_cases.report_sections import InterpretedSection, sections_for
from apps.analysis.dependencies.analysis_dependencies import build_agents
from apps.analysis.domain.analysis_context import (
    AnalysisContext,
    AnalysisRequest,
    ConsultationContext,
    ConsultationProfile,
    RiskView,
)
from apps.analysis.domain.report_text import system_instruction
from apps.rag.adapter.outbound.embeddings.ollama_qwen3_adapter import OllamaQwen3EmbeddingAdapter
from core.matrix.grid_keymaker_secret_manager import get_settings
from core.matrix.grid_region_config import REGION_NAME

_REPO_ROOT = Path(__file__).resolve().parents[6]
_OLLAMA = "http://127.0.0.1:11434"
_EMBEDDING_MODEL = "qwen3-embedding:4b"

_FINANCE = {
    "deposit": 10_000_000, "key_money": 0, "interior_cost": 20_000_000, "equipment_cost": 10_000_000,
    "monthly_rent": 1_000_000, "monthly_payroll": 2_000_000, "monthly_insurance": 100_000,
    "cost_ratio": 0.35, "fee_ratio": 0.05, "equity": 30_000_000, "desired_loan": 10_000_000,
    "loan_rate": 0.05, "expected_monthly_revenue": 8_000_000,
}
_CONSULTATION = ConsultationContext(
    profile=ConsultationProfile(business_registered=None, guarantee_status="unknown"),
    change_reason="월세를 낮춘 자리로 바꿨습니다",
    assumptions=["원가율 35%는 업종 벤치마크 기본값"],
    open_questions=["설비 견적 미확정"],
)
_REQUESTS = {
    "review_finance": AnalysisRequest(region="2711059500", industry="cafe", finance=_FINANCE, question="원두값 오르면?"),
    "review_nofinance": AnalysisRequest(region="2711054500", industry="restaurant"),
    "handoff": AnalysisRequest(
        region="2711059500", industry="cafe", finance=_FINANCE, purpose="handoff", consultation=_CONSULTATION
    ),
}
# 섹션별 상한 — (불릿 상한, 문장 상한, 질문 상한). None 은 검사 안 함.
_LIMITS = {
    "verdict": (None, 3, None),
    "market": (3, None, None),
    "shock": (3, None, None),
    "funding": (3, None, None),
    "plan": (None, 4, None),
    "questions": (5, None, 5),
}
_RED_WORDS = ("주의", "위험", "높", "어렵", "신중", "부담")
_GREEN_WORDS = ("양호", "낮", "안정", "좋", "유리", "무난")


# ---------- 게이트 (순수 함수) ----------


def has_heading(text: str) -> bool:
    return any(line.lstrip().startswith("#") for line in text.splitlines())


def has_bracket_citation(text: str) -> bool:
    return re.search(r"\[\d+\]", text) is not None


def count_bullets(text: str) -> int:
    return sum(1 for line in text.splitlines() if re.match(r"\s*([-*•]|\d+[.)])\s+", line))


def count_sentences(text: str) -> int:
    body = re.sub(r"\s*([-*•]|\d+[.)])\s+", " ", text)  # 불릿 기호는 문장 종결이 아니다
    ends = re.findall(r"(?<!\d)[.!?。](?=\s|$|\*)", body)
    tail = body.strip()
    return len(ends) + (1 if tail and not re.search(r"[.!?。]\s*\**$", tail) else 0)


def count_questions(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip().rstrip("*").endswith("?"))


def _numbers(text: str) -> list[str]:
    return [n for n in re.findall(r"\d+(?:\.\d+)?", text.replace(",", "")) if len(n.replace(".", "")) >= 2]


def foreign_numbers(text: str, prompt: str) -> list[str]:
    allowed = set(_numbers(prompt))
    # 만·억 단위 환산(4000만원 = 40,000,000)은 허용 — 원 단위 숫자를 만 단위로 줄여 쓴 것
    for n in list(allowed):
        if n.isdigit() and len(n) > 4:
            allowed.add(str(int(n) // 10_000))
    return [n for n in _numbers(text) if n not in allowed]


def _normalize(text: str) -> str:
    """인용 대조용 — 문장부호·괄호·공백을 뺀다 ('[내년 최저임금] 대구…' 를 '내년 최저임금 대구…' 로 인용해도 정당)."""
    return re.sub(r"[^0-9A-Za-z가-힣]", "", text)


def unknown_citations(text: str, titles: list[str]) -> list[str]:
    cited = [c.strip() for c in re.findall(r"「([^」]+)」", text)]
    normalized_titles = [_normalize(t) for t in titles]
    return [
        c for c in cited
        if len(_normalize(c)) < 6 or not any(_normalize(c) in t or t in _normalize(c) for t in normalized_titles)
    ]


def hangul_ratio(text: str) -> float:
    hangul = len(re.findall(r"[가-힣]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    return hangul / (hangul + latin) if hangul + latin else 0.0


def direction_ok(text: str, grade: str) -> bool:
    first = re.split(r"(?<!\d)[.!?。]", text.strip(), maxsplit=1)[0]
    words = _RED_WORDS if grade == "red" else _GREEN_WORDS
    return any(w in first for w in words)


# ---------- 컨텍스트·프롬프트 ----------


def _build_contexts() -> dict[str, AnalysisContext]:
    agents = build_agents()
    contexts = {}
    for name, request in _REQUESTS.items():
        ctx = AnalysisContext(analysis_id=name, request=request)
        for agent in agents:
            for _ in agent.collect(ctx):
                pass
        contexts[name] = ctx
    return contexts


def _polarity_contexts(ctx: AnalysisContext) -> dict[str, AnalysisContext]:
    """verdict 방향 일치 짝 — 위험 등급만 red/green 으로 치환한 복사본."""
    base = ctx.market.risk.components if ctx.market and ctx.market.risk else {"closure": 0.5, "density": 0.5, "growth": 0.5}
    out = {}
    for grade, score in (("red", 82.0), ("green", 18.0)):
        market = dataclasses.replace(ctx.market, risk=RiskView(score=score, grade=grade, components=base))
        out[grade] = dataclasses.replace(ctx, analysis_id=f"polarity_{grade}", market=market)
    return out


def _prompts(contexts: dict[str, AnalysisContext]) -> list[dict]:
    system = system_instruction(REGION_NAME)
    items = []
    for name, ctx in contexts.items():
        titles = [d.title for d in [*ctx.news, *ctx.funding_docs]]
        for section in sections_for(ctx.request.purpose, REGION_NAME):
            if isinstance(section, InterpretedSection):
                items.append({"context": name, "section": section.key, "system": system, "prompt": section.prompt(ctx), "titles": titles, "grade": None})
    for grade, pctx in _polarity_contexts(contexts["review_finance"]).items():
        section = next(s for s in sections_for("review", REGION_NAME) if s.key == "verdict")
        items.append({"context": f"polarity_{grade}", "section": "verdict", "system": system, "prompt": section.prompt(pctx), "titles": [], "grade": grade})
    return items


# ---------- 실행·측정 ----------


def _generate(writer, system: str, prompt: str) -> dict:
    started = time.perf_counter()
    ttft = None
    parts = []
    error = None
    try:
        for chunk in writer.stream(system, prompt):
            if ttft is None:
                ttft = time.perf_counter() - started
            parts.append(chunk)
    except Exception as exc:  # 게이트 집계용 — 실패도 결과다
        error = f"{type(exc).__name__}: {exc}"[:200]
    total = time.perf_counter() - started
    stats = getattr(writer, "last_stats", {}) or {}
    tok_s = round(stats["eval_count"] / stats["eval_duration"] * 1e9, 1) if stats.get("eval_duration") else None
    return {"text": "".join(parts), "ttft_s": round(ttft, 2) if ttft else None, "total_s": round(total, 2), "tok_s": tok_s, "error": error}


def _gate(item: dict, gen: dict) -> dict:
    text = gen["text"]
    bullets_max, sentences_max, questions_max = _LIMITS[item["section"]]
    bullets, sentences, questions = count_bullets(text), count_sentences(text), count_questions(text)
    checks = {
        "completed": gen["error"] is None and bool(text.strip()),
        "no_heading": not has_heading(text),
        "no_bracket": not has_bracket_citation(text),
        "bullets_ok": bullets_max is None or bullets <= bullets_max,
        "sentences_ok": sentences_max is None or sentences <= sentences_max,
        "questions_ok": questions_max is None or questions <= questions_max,
        "no_foreign_numbers": not foreign_numbers(text, item["prompt"]),
        "citations_ok": not unknown_citations(text, item["titles"]),
        "hangul_ok": hangul_ratio(text) >= 0.9,
    }
    if item["grade"]:
        checks["direction_ok"] = direction_ok(text, item["grade"])
    return {
        **checks,
        "all_ok": all(checks.values()),
        "counts": {"bullets": bullets, "sentences": sentences, "questions": questions, "chars": len(text)},
        "foreign_numbers": foreign_numbers(text, item["prompt"]),
        "unknown_citations": unknown_citations(text, item["titles"]),
        "hangul_ratio": round(hangul_ratio(text), 3),
    }


def _ollama_ps() -> list[dict]:
    try:
        models = httpx.get(f"{_OLLAMA}/api/ps", timeout=5).json().get("models", [])
    except Exception:
        return []
    return [{"name": m["name"], "vram_gib": round(m.get("size_vram", 0) / 2**30, 2)} for m in models]


def _gpu_used_mib() -> int | None:
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5)
        return int(out.stdout.strip().splitlines()[0])
    except Exception:
        return None


def _warm_embedding() -> None:
    OllamaQwen3EmbeddingAdapter(dimensions=2560).embed_query("워밍업")


def _candidates(names: list[str]) -> dict:
    settings = get_settings()
    out = {}
    for n in names:
        if n == "gemini":
            out[f"gemini:{settings.gemini_report_model}"] = GeminiReportWriter(
                client=genai.Client(api_key=settings.gemini_api_key), model=settings.gemini_report_model
            )
        else:
            out[n] = OllamaReportWriter(model=n)
    return out


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.fmean(xs), 3) if xs else None


def _p50(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 2) if xs else None


def _summarize(runs: list[dict]) -> dict:
    gates = [r["gate"] for r in runs]
    polar = [r for r in runs if r["grade"]]
    return {
        "n": len(runs),
        "completed": _mean([g["completed"] for g in gates]),
        "all_gates_ok": _mean([g["all_ok"] for g in gates]),
        "no_heading": _mean([g["no_heading"] for g in gates]),
        "length_ok": _mean([g["bullets_ok"] and g["sentences_ok"] and g["questions_ok"] for g in gates]),
        "no_bracket": _mean([g["no_bracket"] for g in gates]),
        "no_foreign_numbers": _mean([g["no_foreign_numbers"] for g in gates]),
        "citations_ok": _mean([g["citations_ok"] for g in gates]),
        "hangul_ratio": _mean([g["hangul_ratio"] for g in gates]),
        "direction_ok": _mean([r["gate"].get("direction_ok") for r in polar]),
        "ttft_p50_s": _p50([r["gen"]["ttft_s"] for r in runs]),
        "total_p50_s": _p50([r["gen"]["total_s"] for r in runs]),
        "tok_s_p50": _p50([r["gen"]["tok_s"] for r in runs]),
        "chars_mean": _mean([g["counts"]["chars"] for g in gates]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--candidates", default="gemini,gemma4:12b,exaone3.5:7.8b,kanana1.5:8b-q4km")
    args = parser.parse_args()

    contexts = _build_contexts()
    items = _prompts(contexts)
    for name, ctx in contexts.items():
        print(f"context {name}: cards {len(ctx.cards)} risk {ctx.risk.grade if ctx.risk else None} news {len(ctx.news)} funding_docs {len(ctx.funding_docs)} products {len(ctx.products)} sim {'있음' if ctx.simulation else '없음'}", flush=True)
    print(f"prompts {len(items)} × repeat {args.repeat}", flush=True)

    results = {}
    for name, writer in _candidates([c.strip() for c in args.candidates.split(",")]).items():
        _warm_embedding()
        gpu_before = _gpu_used_mib()
        runs = []
        started = time.monotonic()
        for item in items:
            for rep in range(args.repeat):
                gen = _generate(writer, item["system"], item["prompt"])
                runs.append({"context": item["context"], "section": item["section"], "grade": item["grade"], "rep": rep, "gen": gen, "gate": _gate(item, gen)})
        ps = _ollama_ps()
        resident = {m["name"] for m in ps}
        is_local = not name.startswith("gemini")
        results[name] = {
            "summary": _summarize(runs),
            "vram": {
                "gpu_used_mib_before": gpu_before,
                "gpu_used_mib_after": _gpu_used_mib(),
                "ollama_ps_after": ps,
                # 외부 API 후보는 GPU와 무관 — None
                "coresident_with_embedding": (_EMBEDDING_MODEL in resident and name in resident) if is_local else None,
                "elapsed_s": round(time.monotonic() - started, 1),
            },
            "runs": runs,
        }
        s = results[name]["summary"]
        print(f"  {name}: 완료 {s['completed']} 게이트전부 {s['all_gates_ok']} 숫자OK {s['no_foreign_numbers']} 인용OK {s['citations_ok']} 방향 {s['direction_ok']} TTFT {s['ttft_p50_s']}s 총 {s['total_p50_s']}s tok/s {s['tok_s_p50']} | ps {[m['name'] for m in ps]}", flush=True)

    print("\n| 후보 | 완료 | 게이트 전부 통과 | 제목 없음 | 분량 | 대괄호 없음 | 숫자 환각 없음 | 인용 OK | 한국어 비율 | 방향 일치 | TTFT p50 | 총 p50 | tok/s | 임베딩과 동주 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for name, r in results.items():
        s, v = r["summary"], r["vram"]
        print(f"| {name} | {s['completed']} | {s['all_gates_ok']} | {s['no_heading']} | {s['length_ok']} | {s['no_bracket']} | {s['no_foreign_numbers']} | {s['citations_ok']} | {s['hangul_ratio']} | {s['direction_ok']} | {s['ttft_p50_s']}s | {s['total_p50_s']}s | {s['tok_s_p50'] or '—'} | {v['coresident_with_embedding']} ({v['gpu_used_mib_after']} MiB) |")

    results_dir = _REPO_ROOT / "data/eval/results"
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = results_dir / f"llm_compare_{timestamp}.json"
    out_path.write_text(
        json.dumps({"timestamp": timestamp, "repeat": args.repeat, "prompts": [{k: v for k, v in i.items() if k != "system"} for i in items], "candidates": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n결과 저장: {out_path}", flush=True)


if __name__ == "__main__":
    main()
