"""Driven Adapters — finance 결정론 엔진·matching 도메인 함수를 analysis 포트로 노출 (ACL)."""

from collections.abc import Callable

from apps.analysis.app.ports.output.analysis_port import ProductMatchingPort, SimulationPort
from apps.analysis.domain.analysis_context import (
    ConsultationProfile,
    MatchedProduct,
    ScenarioLine,
    SimulationSummary,
)
from apps.finance.domain.engine import FinanceInput, simulate
from apps.matching.adapter.outbound.gateways.manual_product_gateway import (
    load_all_products,
    load_consultation_products,
)
from apps.matching.domain.consultation import build_consultation_candidates
from apps.matching.domain.matcher import match_products

_PRE_STARTUP_BUSINESS_AGE_MONTHS = 0  # 리포트 대상은 예비창업자 — 업력 0개월 전제


class EngineSimulationGateway(SimulationPort):
    def simulate(self, finance: dict) -> SimulationSummary:
        result = simulate(FinanceInput(**finance))
        return SimulationSummary(
            capex=result.capex,
            monthly_fixed=result.monthly_fixed,
            bep_revenue=result.bep_revenue,
            funding_gap=result.funding_gap,
            reserve_months=result.reserve_months,
            operating_reserve=result.operating_reserve,
            total_required_funds=result.total_required_funds,
            external_funding_need=result.external_funding_need,
            scenarios=[
                ScenarioLine(s.name, s.monthly_revenue, s.operating_profit, s.payback_months)
                for s in result.scenarios
            ],
        )


class ManualProductMatchingGateway(ProductMatchingPort):
    def __init__(
        self,
        load_products: Callable[[], list[dict]] = load_all_products,
        load_consultation: Callable[[], list[dict]] = load_consultation_products,
    ) -> None:
        self._load_products = load_products
        self._load_consultation = load_consultation

    def match(self, funding_gap: int, industry_id: str) -> list[MatchedProduct]:
        rows = match_products(
            self._load_products(), funding_gap, industry_id, _PRE_STARTUP_BUSINESS_AGE_MONTHS, None
        )
        return [
            MatchedProduct(p["provider"], p["product_name"], p["loan_limit"], p["interest_rate"]) for p in rows
        ]

    def consultation_candidates(
        self, external_funding_need: int, industry_id: str, profile: ConsultationProfile, district_code: str
    ) -> list[MatchedProduct]:
        # 화면의 'iM뱅크에서 상담할 상품'과 같은 함수·같은 입력 — 취급·연계 근거가 확인된 상품만(include_unverified=False).
        candidates = build_consultation_candidates(
            self._load_consultation(),
            external_funding_need=external_funding_need,
            category=industry_id,
            business_registered=profile.business_registered,
            business_age_months=profile.business_age_months,
            owner_age=profile.owner_age,
            district_code=district_code,
        )
        return [
            MatchedProduct(
                c.product["provider"], c.product["product_name"], c.product["loan_limit"], c.product["interest_rate"]
            )
            for c in candidates
        ]
