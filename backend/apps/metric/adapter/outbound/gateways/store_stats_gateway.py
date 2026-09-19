"""Driven Adapter — 지표 원천 Strategy 합성 (cross-BC 접근은 어댑터 레이어에서만).

포트는 하나지만 원천은 여럿이다(인허가 store / 담배소매인 → 편의점 / 어린이집).
새 원천을 붙일 때 이 파일에 if 를 더하지 않고 `_SOURCES` 레지스트리에 클래스를 추가한다(OCP).
"""

from datetime import date

from apps.metric.adapter.outbound.gateways.stats_sources.childcare_source import (
    ChildcareSource,
)
from apps.metric.adapter.outbound.gateways.stats_sources.store_table_source import (
    StoreTableSource,
)
from apps.metric.adapter.outbound.gateways.stats_sources.tobacco_proxy_source import (
    TobaccoProxySource,
)
from apps.metric.adapter.outbound.gateways.stats_sources.yearly_stats_source import (
    YearlyStatsSource,
)
from apps.metric.app.dtos.region_industry_metric_dto import YearlyStoreStat
from apps.metric.app.ports.output.region_industry_metric_port import StoreStatsPort
from core.matrix.grid_oracle_database_manager import session_scope

_SOURCES: list[type[YearlyStatsSource]] = [
    StoreTableSource,
    TobaccoProxySource,
    ChildcareSource,
]


class StoreStatsGateway(StoreStatsPort):
    def __init__(self, sources: list[YearlyStatsSource] | None = None) -> None:
        self._sources = sources if sources is not None else [cls() for cls in _SOURCES]

    def yearly_stats(self, years: list[int]) -> list[YearlyStoreStat]:
        with session_scope() as session:
            return [
                stat
                for source in self._sources
                for stat in source.yearly_stats(session, years)
            ]

    def latest_record_date(self) -> date | None:
        with session_scope() as session:
            dates = [
                latest
                for source in self._sources
                if (latest := source.latest_record_date(session)) is not None
            ]
        return max(dates, default=None)
