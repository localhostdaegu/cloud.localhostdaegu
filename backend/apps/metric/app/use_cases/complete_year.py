"""연도 미지정 조회의 기본 연도 해석 — 마지막 완결 연도 상한 (risk·region summary 공용)."""

from apps.metric.app.ports.output.region_industry_metric_port import (
    RegionIndustryMetricRepositoryPort,
    StoreStatsPort,
)
from apps.metric.domain.reporting_year import last_complete_year


def complete_year_cap(store_stats: StoreStatsPort) -> int | None:
    """지표 원천(store·담배소매인·어린이집) 최신 기록일 기준 마지막 완결 연도. 원천이 비어 있으면 상한 없음(None)."""
    latest = store_stats.latest_record_date()
    return None if latest is None else last_complete_year(latest)


def resolve_year(
    year: int | None,
    industry_id: str,
    repository: RegionIndustryMetricRepositoryPort,
    store_stats: StoreStatsPort,
) -> int | None:
    """명시 연도는 그대로, 미지정이면 완결 연도 상한 안에서 해당 업종의 최신 연도."""
    if year is not None:
        return year
    return repository.latest_year(industry_id, until_year=complete_year_cap(store_stats))
