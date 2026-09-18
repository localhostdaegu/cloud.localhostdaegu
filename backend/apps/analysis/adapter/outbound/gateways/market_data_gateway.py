"""Driven Adapter — master(region summary)·metric(risk) 유스케이스 결과를 MarketSnapshot 으로 변환 (ACL).

cross-BC 접근은 이 어댑터에서만 한다.
"""

from apps.analysis.app.ports.output.analysis_port import MarketDataPort
from apps.analysis.domain.analysis_context import MarketSnapshot, MetricCard, RiskView
from apps.master.adapter.outbound.orms.industry_orm import IndustryOrm
from apps.master.app.ports.input.region_use_case import RegionUseCase
from apps.master.domain.errors import RegionNotFoundError
from apps.metric.app.ports.input.risk_use_case import RiskUseCase
from core.matrix.grid_oracle_database_manager import session_scope


class MarketDataGateway(MarketDataPort):
    def __init__(self, region_use_case: RegionUseCase, risk_use_case: RiskUseCase) -> None:
        self._region = region_use_case
        self._risk = risk_use_case

    def fetch(
        self, region_code: str, industry_id: str, year: int | None = None
    ) -> MarketSnapshot | None:
        # 지도에서 고른 연도를 지표·위험도 양쪽에 같이 넘긴다 — 한쪽만 넘기면 카드와
        # 위험도의 기준연도가 어긋난다. 미지정이면 각 유스케이스의 마지막 완결 연도.
        try:
            summary = self._region.summary(region_code, industry_id, year)
        except RegionNotFoundError:
            return None
        risk = self._risk.score_for(region_code, industry_id, year)
        return MarketSnapshot(
            region_name=summary.name,
            industry_name=self._industry_name(industry_id),
            cards=[MetricCard(label=card.label, value=card.value) for card in summary.cards],
            risk=None if risk is None else RiskView(score=risk.score, grade=risk.grade, components=dict(risk.components)),
        )

    def _industry_name(self, industry_id: str) -> str:
        with session_scope() as session:
            orm = session.get(IndustryOrm, industry_id)
            return industry_id if orm is None else orm.name
