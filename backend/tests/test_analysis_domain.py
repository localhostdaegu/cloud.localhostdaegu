"""analysis 도메인 — SSE 페이로드가 프론트 AgentEvent(types.ts)와 1:1인지, 컨텍스트 라벨 폴백."""

from apps.analysis.domain.agent_event import (
    AgentStatusEvent,
    Citation,
    ReportDeltaEvent,
    ReportDoneEvent,
    ToolCallEvent,
)
from tests.analysis_fakes import MARKET, SIMULATION, bare_context


def test_agent_status_payload_matches_frontend_contract():
    assert AgentStatusEvent(agent="market", status="running").to_payload() == {
        "type": "agent_status",
        "agent": "market",
        "status": "running",
    }


def test_tool_call_payload_matches_frontend_contract():
    assert ToolCallEvent(agent="shock", tool="news_search", summary="뉴스 RAG 검색 — 3건").to_payload() == {
        "type": "tool_call",
        "agent": "shock",
        "tool": "news_search",
        "summary": "뉴스 RAG 검색 — 3건",
    }


def test_report_delta_payload_matches_frontend_contract():
    assert ReportDeltaEvent(section="verdict", markdown="### 종합 진단").to_payload() == {
        "type": "report_delta",
        "section": "verdict",
        "markdown": "### 종합 진단",
    }


def test_report_done_payload_serializes_citations_as_objects():
    event = ReportDoneEvent(report_id="abc", citations=[Citation(title="공고", url="https://x", grade="fact")])
    assert event.to_payload() == {
        "type": "report_done",
        "report_id": "abc",
        "citations": [{"title": "공고", "url": "https://x", "grade": "fact"}],
    }


def test_context_labels_fall_back_to_codes_without_market():
    ctx = bare_context()
    assert (ctx.region_label, ctx.industry_label) == ("2711059500", "cafe")
    assert ctx.risk is None
    assert ctx.cards == []


def test_context_labels_use_market_names():
    ctx = bare_context()
    ctx.market = MARKET
    assert (ctx.region_label, ctx.industry_label) == ("대신동", "카페")
    assert ctx.risk == MARKET.risk
    assert ctx.cards == MARKET.cards


def test_context_funding_gap_is_zero_without_simulation_and_uses_simulation_when_present():
    ctx = bare_context()
    assert ctx.funding_gap == 0
    ctx.simulation = SIMULATION
    assert ctx.funding_gap == 18_849_996
