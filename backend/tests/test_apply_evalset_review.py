"""검수 판정(csv) → 평가셋(jsonl) 반영 순수 함수 — confirm/revise/reject/빈칸 4케이스. DB 없음."""

import pytest

from apps.rag.adapter.inbound.cli.apply_evalset_review import apply_verdicts

ROWS = [
    {"question": "q1", "relevant_ids": ["funding:A"], "source_type": "funding", "status": "candidate"},
    {"question": "q2", "relevant_ids": ["news:B"], "source_type": "news", "status": "candidate"},
    {"question": "q3", "relevant_ids": ["funding:C"], "source_type": "funding", "status": "candidate"},
]


def test_confirm은_status만_confirmed로_올리고_질문은_그대로():
    out, summary = apply_verdicts(ROWS, {"funding:A": {"verdict": "confirm", "revised_question": ""}})

    assert out[0]["status"] == "confirmed" and out[0]["question"] == "q1"
    assert summary == {"confirm": 1, "revise": 0, "reject": 0, "pending": 2}


def test_revise는_질문을_바꾸고_confirmed로_올린다():
    out, _ = apply_verdicts(ROWS, {"news:B": {"verdict": "revise", "revised_question": "새 질문"}})

    assert out[1]["question"] == "새 질문" and out[1]["status"] == "confirmed"


def test_reject는_행을_제거하고_빈칸은_candidate로_남긴다():
    out, summary = apply_verdicts(ROWS, {"funding:C": {"verdict": "reject", "revised_question": ""}})

    assert [r["relevant_ids"][0] for r in out] == ["funding:A", "news:B"]
    assert out[0]["status"] == "candidate"
    assert summary["reject"] == 1 and summary["pending"] == 2


def test_revise인데_새_질문이_비어_있으면_거부한다():
    with pytest.raises(ValueError, match="funding:A"):
        apply_verdicts(ROWS, {"funding:A": {"verdict": "revise", "revised_question": " "}})
