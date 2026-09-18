"""Driven Adapter — metric BC UseCase 호출로 지표 스냅샷 취득 (cross-BC는 어댑터 레이어에서만)."""

from apps.master.app.dtos.region_dto import RegionMetricSnapshot
from apps.master.app.ports.output.region_port import RegionMetricSummaryPort
from apps.metric.dependencies.region_industry_metric_dependencies import (
    get_region_industry_metric_use_case,
)


class MetricSummaryGateway(RegionMetricSummaryPort):
    def fetch(
        self, region_code: str, industry_id: str, year: int | None = None
    ) -> RegionMetricSnapshot | None:
        # 연도 미지정 → 마지막 완결 연도 (부분 연도를 연간 카드로 보이지 않게)
        dto = get_region_industry_metric_use_case().find(region_code, industry_id, year)
        if dto is None:
            return None
        return RegionMetricSnapshot(
            store_count=dto.store_count,
            closure_rate=dto.closure_rate,
            growth_rate=dto.growth_rate,
        )
