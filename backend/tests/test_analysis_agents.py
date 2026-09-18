"""수집 에이전트 3종 — Fake 포트로 컨텍스트 채움·tool_call 이벤트 검증."""

from dataclasses import replace

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

    assert market.calls == [("2711059500", "cafe", None)]
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


def test_funding_agent_without_finance_skips_simulation_and_matching():
    """전환계획 §3-1 — 재무 입력이 없으면 0원으로 상품을 매칭하지 않는다.
    개인별 상품 안내를 건너뛰고, 지역 공통 정책자금 공고 검색만 남긴다."""
    search, simulation, matching = FakeEvidenceSearch(), FakeSimulation(), FakeMatching()
    ctx = _context()
    ctx.market = MARKET

    events = list(FundingAgent(search, simulation, matching, "대구").collect(ctx))

    assert simulation.calls == []
    assert matching.calls == []
    assert ctx.products == []
    assert search.calls == [("대구 카페 소상공인 창업 정책자금 보증 대출", "funding", 5)]
    assert ctx.funding_docs == [FUNDING_DOC]
    assert [e.tool for e in events] == ["funding_search"]


def test_funding_agent_with_finance_simulates_first_and_matches_with_gap():
    search, simulation, matching = FakeEvidenceSearch(), FakeSimulation(), FakeMatching()
    ctx = _context(finance=FINANCE)

    events = list(FundingAgent(search, simulation, matching, "대구").collect(ctx))

    assert simulation.calls == [FINANCE]
    assert ctx.simulation == SIMULATION
    # §4-1 — 상담 주제가 되는 금액은 조달 필요액이다. 희망대출 반영 후 부족액이 아니다.
    assert matching.calls == [(28_849_996, "cafe")]
    assert [e.tool for e in events] == ["finance_simulate", "product_matching", "funding_search"]
    assert events[0].summary == "재무 시뮬레이션 — 조달 필요 28,849,996원"


def test_funding_agent_recalculates_baseline_plan_on_the_server():
    """전환계획 §5-1 — 비교 원본도 서버 엔진으로 다시 계산한다.
    클라이언트가 보낸 계산 결과를 리포트의 기준으로 삼지 않는다."""
    from apps.analysis.domain.analysis_context import ConsultationContext, ConsultationProfile

    search, simulation, matching = FakeEvidenceSearch(), FakeSimulation(), FakeMatching()
    baseline = {**FINANCE, "monthly_rent": 2_000_000}
    ctx = _context(finance=FINANCE)
    ctx.request = replace(
        ctx.request,
        consultation=ConsultationContext(profile=ConsultationProfile(), baseline_finance=baseline),
    )

    list(FundingAgent(search, simulation, matching, "대구").collect(ctx))

    assert simulation.calls == [FINANCE, baseline]
    assert ctx.baseline_simulation is not None


def test_funding_agent_skips_baseline_when_there_is_nothing_to_compare():
    search, simulation, matching = FakeEvidenceSearch(), FakeSimulation(), FakeMatching()
    ctx = _context(finance=FINANCE)

    list(FundingAgent(search, simulation, matching, "대구").collect(ctx))

    assert simulation.calls == [FINANCE]
    assert ctx.baseline_simulation is None


def test_market_agent_passes_the_selected_year_to_the_data_port():
    """지도에서 고른 연도가 리포트 지역 근거에 그대로 쓰여야 한다(§7-3).
    전달하지 않으면 화면과 리포트의 기준연도가 어긋난다."""
    market = FakeMarketData()
    ctx = _context()
    ctx.request = replace(ctx.request, year=2024)

    list(MarketAgent(market).collect(ctx))

    assert market.calls == [("2711059500", "cafe", 2024)]


def test_market_agent_leaves_year_unset_when_not_chosen():
    market = FakeMarketData()

    list(MarketAgent(market).collect(_context()))

    assert market.calls == [("2711059500", "cafe", None)]
