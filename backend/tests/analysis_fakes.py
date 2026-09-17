"""analysis BC 테스트 공용 샘플·Fake 포트 — DB·네트워크·LLM 없음.

SIMULATION 수치는 FINANCE 입력을 apps.finance.domain.engine.simulate로 계산한 실측값(2026-09-17).
"""

from apps.analysis.domain.analysis_context import (
    AnalysisContext,
    AnalysisRequest,
    EvidenceDoc,
    MarketSnapshot,
    MatchedProduct,
    MetricCard,
    RiskView,
    ScenarioLine,
    SimulationSummary,
)

MARKET = MarketSnapshot(
    region_name="대신동",
    industry_name="카페",
    cards=[MetricCard("점포수", "120개"), MetricCard("폐업률", "6.4%"), MetricCard("성장률", "+2.1%")],
    risk=RiskView(score=72.5, grade="red", components={"closure": 30.0, "density": 28.5, "growth": 14.0}),
)
NEWS_DOC = EvidenceDoc(
    source_type="news",
    title="원두값 급등에 카페 원가 압박",
    snippet="원두 선물 가격이 전년 대비 8% 상승했다.",
    url="https://news.example/1",
    org="매일신문",
    published_at="2026-09-10",
)
FUNDING_DOC = EvidenceDoc(
    source_type="funding",
    title="대구 청년창업 지원사업",
    snippet="만 39세 이하 예비창업자 대상 최대 5천만원",
    url="https://funding.example/1",
    org="대구광역시",
    published_at="2026-09-01",
)
PRODUCT = MatchedProduct(
    provider="대구신용보증재단", product_name="소상공인 창업 보증", loan_limit=50_000_000, interest_rate=3.2
)
FINANCE = {
    "deposit": 10_000_000,
    "key_money": 0,
    "interior_cost": 20_000_000,
    "equipment_cost": 10_000_000,
    "monthly_rent": 1_000_000,
    "monthly_payroll": 2_000_000,
    "monthly_insurance": 100_000,
    "cost_ratio": 0.35,
    "fee_ratio": 0.05,
    "equity": 30_000_000,
    "desired_loan": 10_000_000,
    "loan_rate": 0.05,
    "expected_monthly_revenue": 8_000_000,
}
SIMULATION = SimulationSummary(
    capex=40_000_000,
    monthly_fixed=3_141_666,
    bep_revenue=5_236_109,
    funding_gap=18_849_996,
    scenarios=[
        ScenarioLine("비관", 4_800_000, -261_665, None),
        ScenarioLine("기준", 8_000_000, 1_658_335, 24.1),
        ScenarioLine("낙관", 12_800_000, 4_538_334, 8.8),
    ],
)


def bare_context() -> AnalysisContext:
    """수집 전 — request 만 채워진 최소 컨텍스트."""
    return AnalysisContext(analysis_id="abc", request=AnalysisRequest(region="2711059500", industry="cafe"))


def full_context() -> AnalysisContext:
    """에이전트 수집이 모두 끝난 상태의 컨텍스트."""
    return AnalysisContext(
        analysis_id="abc",
        request=AnalysisRequest(region="2711059500", industry="cafe", question="원두값 오르면?", finance=FINANCE),
        market=MARKET,
        news=[NEWS_DOC],
        funding_docs=[FUNDING_DOC],
        products=[PRODUCT],
        simulation=SIMULATION,
    )
