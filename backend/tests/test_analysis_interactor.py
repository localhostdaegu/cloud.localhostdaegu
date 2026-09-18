"""AnalysisInteractor — 이벤트 순서(mock SSE 와 동일), 에이전트·LLM 장애 내성, 1회 소비."""

import re

import pytest

from apps.analysis.adapter.outbound.stores.in_memory_analysis_request_store import (
    InMemoryAnalysisRequestStore,
)
from apps.analysis.domain.agent_event import Citation
from apps.analysis.domain.analysis_context import AnalysisRequest
from apps.analysis.domain.errors import AnalysisNotFoundError
from apps.analysis.domain.report_text import FALLBACK_MARKDOWN
from tests.analysis_fakes import (
    FINANCE,
    FUNDING_DOC,
    NEWS_DOC,
    ExplodingMarketData,
    FailingWriter,
    build_interactor,
)

_REQUEST = AnalysisRequest(region="2711059500", industry="cafe")


def _shape(event) -> tuple[str, str, str]:
    p = event.to_payload()
    return (p["type"], p.get("agent") or p.get("section") or "", p.get("status") or p.get("tool") or "")


def _run(interactor, request=_REQUEST):
    analysis_id = interactor.start(request)
    return analysis_id, list(interactor.stream(analysis_id))


def test_stream_emits_events_in_mock_sse_order():
    _, events = _run(build_interactor())

    assert [_shape(e) for e in events] == [
        ("agent_status", "orchestrator", "running"),
        ("agent_status", "market", "running"),
        ("tool_call", "market", "region_metrics"),
        ("tool_call", "market", "risk_score"),
        ("agent_status", "market", "done"),
        ("agent_status", "shock", "running"),
        ("tool_call", "shock", "news_search"),
        ("agent_status", "shock", "done"),
        ("agent_status", "funding", "running"),
        # 재무 입력이 없는 기본 컨텍스트 — product_matching 은 발생하지 않는다 (§3-1)
        ("tool_call", "funding", "funding_search"),
        ("agent_status", "funding", "done"),
        ("report_delta", "verdict", ""),
        ("report_delta", "verdict", ""),
        ("report_delta", "market", ""),
        ("report_delta", "market", ""),
        ("report_delta", "shock", ""),
        ("report_delta", "shock", ""),
        ("report_delta", "funding", ""),
        ("report_delta", "funding", ""),
        ("agent_status", "orchestrator", "done"),
        ("report_done", "", ""),
    ]


def test_report_done_carries_analysis_id_and_citations():
    analysis_id, events = _run(build_interactor())
    done = events[-1].to_payload()
    assert done["report_id"] == analysis_id
    assert done["citations"] == [
        {"title": FUNDING_DOC.title, "url": FUNDING_DOC.url, "grade": "fact"},
        {"title": NEWS_DOC.title, "url": NEWS_DOC.url, "grade": "signal"},
    ]


def test_finance_input_adds_simulation_tool_and_calculator_section():
    _, events = _run(build_interactor(), AnalysisRequest(region="2711059500", industry="cafe", finance=FINANCE))
    shapes = [_shape(e) for e in events]
    assert ("tool_call", "funding", "finance_simulate") in shapes
    assert shapes.count(("report_delta", "calculator", "")) == 1


def test_failing_agent_reports_error_and_stream_still_completes():
    _, events = _run(build_interactor(market=ExplodingMarketData()))
    shapes = [_shape(e) for e in events]
    assert ("agent_status", "market", "error") in shapes
    assert ("agent_status", "market", "done") not in shapes
    assert shapes[-1] == ("report_done", "", "")
    verdict = [e.markdown for e in events if _shape(e) == ("report_delta", "verdict", "")]
    assert "위험도 데이터 없음" in verdict[0]


def test_llm_failure_uses_fallback_and_stream_still_completes():
    _, events = _run(build_interactor(writer=FailingWriter()))
    verdict = [e.markdown for e in events if _shape(e) == ("report_delta", "verdict", "")]
    assert verdict[1:] == ["부분", FALLBACK_MARKDOWN]
    assert _shape(events[-1]) == ("report_done", "", "")


def test_unknown_analysis_id_raises_before_streaming():
    with pytest.raises(AnalysisNotFoundError):
        build_interactor().stream("nope")


def test_request_is_consumed_once():
    interactor = build_interactor()
    analysis_id, _ = _run(interactor)
    with pytest.raises(AnalysisNotFoundError):
        interactor.stream(analysis_id)


def test_in_memory_store_issues_hex_id_and_take_removes():
    store = InMemoryAnalysisRequestStore()
    analysis_id = store.save(_REQUEST)
    assert re.fullmatch(r"[0-9a-f]{32}", analysis_id)
    assert store.take(analysis_id) == _REQUEST
    assert store.take(analysis_id) is None


def test_handoff_streams_consultation_sections_in_order():
    """전환계획 T4 — 상담자료는 선택안·비교가 앞에 오고 위험 판정 섹션이 없다."""
    from apps.analysis.domain.analysis_context import ConsultationContext, ConsultationProfile

    _, events = _run(
        build_interactor(),
        AnalysisRequest(
            region="2711059500",
            industry="cafe",
            finance=FINANCE,
            purpose="handoff",
            consultation=ConsultationContext(profile=ConsultationProfile()),
        ),
    )

    sections = [e.section for e in events if e.TYPE == "report_delta"]
    assert list(dict.fromkeys(sections)) == [
        "plan", "comparison", "calculator", "funding", "questions", "market",
    ]
    assert "verdict" not in sections
    assert "shock" not in sections
