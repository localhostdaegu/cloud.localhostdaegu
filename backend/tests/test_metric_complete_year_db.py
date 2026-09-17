"""완결 연도 상한 — 저장소 until_year 필터·store 원천 최신 기록일 SQL (테스트 DB, 먼 미래 연도로 격리 후 정리)."""

from datetime import date, datetime

from sqlalchemy import delete

from apps.metric.adapter.outbound.gateways.store_stats_gateway import StoreStatsGateway
from apps.metric.adapter.outbound.orms.region_industry_metric_orm import RegionIndustryMetricOrm
from apps.metric.adapter.outbound.repositories.region_industry_metric_repository import (
    SqlAlchemyRegionIndustryMetricRepository,
)
from apps.metric.domain.entities.region_industry_metric_entity import RegionIndustryMetric
from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from core.matrix.grid_oracle_database_manager import session_scope

_REGION = "2711059500"  # 중구 대신동 (시드 마스터)
_YEARS = (3000, 3001)


def _metric(year: int) -> RegionIndustryMetric:
    return RegionIndustryMetric(
        region_code=_REGION, industry_id="billiard", year=year,
        store_count=1, open_count=0, close_count=0, closure_rate=0.0, growth_rate=0.0,
    )


def test_repository_caps_latest_year_at_until_year():
    repository = SqlAlchemyRegionIndustryMetricRepository()
    repository.upsert([_metric(year) for year in _YEARS])
    try:
        assert repository.latest_year("billiard", until_year=3000) == 3000
        assert repository.latest_year("billiard") == 3001
        latest_rows = repository.list_latest_by_region(_REGION, until_year=3000)
        assert [(m.industry_id, m.year) for m in latest_rows if m.industry_id == "billiard"] == [("billiard", 3000)]
    finally:
        with session_scope() as session:
            session.execute(delete(RegionIndustryMetricOrm).where(RegionIndustryMetricOrm.year.in_(_YEARS)))


def test_store_stats_latest_record_date_takes_max_of_open_and_close():
    store = StoreOrm(
        store_id="test-complete-year-1", name="완결연도 테스트", industry_id="billiard",
        district_code="27110", region_code=_REGION, open_date=date(2999, 1, 1), close_date=date(3001, 5, 1),
        status_code="03", status_name="폐업", source_updated_at=datetime(2026, 9, 18),
    )
    with session_scope() as session:
        session.merge(store)
    try:
        assert StoreStatsGateway().latest_record_date() == date(3001, 5, 1)
    finally:
        with session_scope() as session:
            session.execute(delete(StoreOrm).where(StoreOrm.store_id == store.store_id))
