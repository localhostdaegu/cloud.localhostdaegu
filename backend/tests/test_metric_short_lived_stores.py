"""OPEN-008 — 개업 30일 이내 종료 건은 개폐업 집계에서 뺀다 (테스트 DB, 먼 미래 연도로 격리 후 정리)."""

from datetime import date, datetime

from sqlalchemy import delete

from apps.metric.adapter.outbound.gateways.store_stats_gateway import StoreStatsGateway
from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from core.matrix.grid_oracle_database_manager import session_scope

_REGION = "2711059500"  # 중구 대신동 (시드 마스터)
_YEAR = 3100


def _store(suffix: str, open_date: date | None, close_date: date | None) -> StoreOrm:
    return StoreOrm(
        store_id=f"test-short-lived-{suffix}", name="단기 종료 테스트", industry_id="billiard",
        district_code="27110", region_code=_REGION, open_date=open_date, close_date=close_date,
        status_code="03" if close_date else "01", status_name="폐업" if close_date else "영업",
        source_updated_at=datetime(2026, 9, 19),
    )


def test_yearly_stats_excludes_stores_closed_within_30_days_of_opening():
    stores = [
        _store("30d", date(_YEAR, 3, 1), date(_YEAR, 3, 31)),   # 30일 — 제외
        _store("31d", date(_YEAR, 3, 1), date(_YEAR, 4, 1)),    # 31일 — 집계
        _store("open", date(_YEAR, 5, 1), None),                # 영업 중 — 집계
        _store("noopen", None, date(_YEAR, 6, 1)),              # 개업일 없음 — 기간을 알 수 없어 그대로 집계
    ]
    with session_scope() as session:
        for store in stores:
            session.merge(store)
    try:
        stat = next(
            s for s in StoreStatsGateway().yearly_stats([_YEAR])
            if s.region_code == _REGION and s.industry_id == "billiard"
        )
        assert (stat.open_count, stat.close_count, stat.store_count) == (2, 2, 1)
    finally:
        with session_scope() as session:
            session.execute(delete(StoreOrm).where(StoreOrm.store_id.like("test-short-lived-%")))
