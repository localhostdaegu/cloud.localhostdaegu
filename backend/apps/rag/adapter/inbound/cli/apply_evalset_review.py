"""검수 판정 반영 — data/eval/review/rag_evalset_review.csv 의 verdict 열을 평가셋 jsonl에 적용한다.

verdict 값: confirm(질문·정답 그대로 승격) · revise(revised_question으로 교체 후 승격) ·
reject(행 삭제) · 빈칸(candidate 유지). 원본은 같은 자리에 .bak 로 남긴다.

실행: python -m apps.rag.adapter.inbound.cli.apply_evalset_review
      [--review data/eval/review/rag_evalset_review.csv] [--evalset data/eval/rag_evalset.jsonl]
"""

import argparse
import csv
import json
import shutil
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[6]
VERDICTS = ("confirm", "revise", "reject")


def apply_verdicts(rows: list[dict], verdicts: dict[str, dict]) -> tuple[list[dict], dict[str, int]]:
    """rows(평가셋) × verdicts(chunk_id → {verdict, revised_question}) → (새 rows, 집계)."""
    out: list[dict] = []
    summary = {"confirm": 0, "revise": 0, "reject": 0, "pending": 0}
    for row in rows:
        key = row["relevant_ids"][0]
        verdict = (verdicts.get(key) or {}).get("verdict", "").strip().lower()
        if verdict not in VERDICTS:
            summary["pending"] += 1
            out.append(dict(row))
            continue
        summary[verdict] += 1
        if verdict == "reject":
            continue
        new = dict(row, status="confirmed")
        if verdict == "revise":
            revised = verdicts[key].get("revised_question", "").strip()
            if not revised:
                raise ValueError(f"{key}: verdict=revise 인데 revised_question 이 비어 있다")
            new["question"] = revised
        out.append(new)
    return out, summary


def _resolve(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else _REPO_ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", default="data/eval/review/rag_evalset_review.csv")
    parser.add_argument("--evalset", default="data/eval/rag_evalset.jsonl")
    args = parser.parse_args()

    review_path, evalset_path = _resolve(args.review), _resolve(args.evalset)
    with review_path.open(encoding="utf-8-sig", newline="") as fp:
        verdicts = {r["chunk_id"]: r for r in csv.DictReader(fp)}
    rows = [json.loads(line) for line in evalset_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    new_rows, summary = apply_verdicts(rows, verdicts)
    shutil.copy(evalset_path, evalset_path.with_suffix(".jsonl.bak"))
    evalset_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in new_rows), encoding="utf-8")
    print(f"반영: {summary} → {len(new_rows)}건 저장 ({evalset_path}), 백업 .bak", flush=True)


if __name__ == "__main__":
    main()
