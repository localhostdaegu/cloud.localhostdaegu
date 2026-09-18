"""Driven Adapters — finance 결정론 엔진·matching 도메인 함수를 analysis 포트로 노출 (ACL)."""

from collections.abc import Callable

from apps.analysis.app.ports.output.analysis_port import ProductMatchingPort, SimulationPort
from apps.analysis.domain.analysis_context import MatchedProduct, ScenarioLine, SimulationSummary
from apps.finance.domain.engine import FinanceInput, simulate
from apps.matching.adapter.outbound.gateways.manual_product_gateway import load_all_products
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
    def __init__(self, load_products: Callable[[], list[dict]] = load_all_products) -> None:
        self._load_products = load_products

    def match(self, funding_gap: int, industry_id: str) -> list[MatchedProduct]:
        rows = match_products(
            self._load_products(), funding_gap, industry_id, _PRE_STARTUP_BUSINESS_AGE_MONTHS, None
        )
        return [
            MatchedProduct(p["provider"], p["product_name"], p["loan_limit"], p["interest_rate"]) for p in rows
        ]
