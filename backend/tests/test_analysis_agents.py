"""수집 에이전트 3종 — Fake 포트로 컨텍스트 채움·tool_call 이벤트 검증."""

from apps.analysis.app.use_cases.analysis_agents import FundingAgent, MarketAgent, ShockAgent
from apps.analysis.domain.analysis_context import AnalysisContext, AnalysisRequest
from tests.analysis_fakes import (
    FINANCE,
    FUNDING_DOC,
    MARKET,
    NEWS_DOC,
    PRODUCT,
    SIMULATION,
    FakeEvidenceSearch,
    FakeMarketData,
    FakeMatching,
    FakeSimulation,
)


def _context(question: str | None = None, finance: dict | None = None) -> AnalysisContext:
    return AnalysisContext(
        analysis_id="abc",
        request=AnalysisRequest(region="2711059500", industry="cafe", question=question, finance=finance),
    )


def test_market_agent_fetches_snapshot_and_reports_two_tools():
    market = FakeMarketData()
    ctx = _context()

    events = list(MarketAgent(market).collect(ctx))

    assert market.calls == [("2711059500", "cafe")]
    assert ctx.market == MARKET
    assert [(e.agent, e.tool) for e in events] == [("market", "region_metrics"), ("market", "risk_score")]
    assert events[0].summary == "대신동 카페 점포수·폐업률·성장률 조회"


def test_shock_agent_searches_news_with_question():
    search = FakeEvidenceSearch()
    ctx = _context(question="원두값 오르면?")
    ctx.market = MARKET

    events = list(ShockAgent(search, "대구").collect(ctx))

    assert search.calls == [("대구 카페 소상공인 원가 금리 경기 원두값 오르면?", "news", 5)]
    assert ctx.news == [NEWS_DOC]
    assert [(e.agent, e.tool, e.summary) for e in events] == [("shock", "news_search", "뉴스 RAG 검색 — 1건")]


def test_funding_agent_without_finance_skips_simulation_and_matches_with_zero_gap():
    search, simulation, matching = FakeEvidenceSearch(), FakeSimulation(), FakeMatching()
    ctx = _context()
    ctx.market = MARKET

    events = list(FundingAgent(search, simulation, matching, "대구").collect(ctx))

    assert simulation.calls == []
    assert matching.calls == [(0, "cafe")]
    assert search.calls == [("대구 카페 소상공인 창업 정책자금 보증 대출", "funding", 5)]
    assert ctx.products == [PRODUCT]
    assert ctx.funding_docs == [FUNDING_DOC]
    assert [e.tool for e in events] == ["product_matching", "funding_search"]


def test_funding_agent_with_finance_simulates_first_and_matches_with_gap():
    search, simulation, matching = FakeEvidenceSearch(), FakeSimulation(), FakeMatching()
    ctx = _context(finance=FINANCE)

    events = list(FundingAgent(search, simulation, matching, "대구").collect(ctx))

    assert simulation.calls == [FINANCE]
    assert ctx.simulation == SIMULATION
    assert matching.calls == [(18_849_996, "cafe")]
    assert [e.tool for e in events] == ["finance_simulate", "product_matching", "funding_search"]
    assert events[0].summary == "재무 시뮬레이션 — 부족 자금 18,849,996원"
