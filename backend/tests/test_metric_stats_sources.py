"""지표 원천 Strategy 검증 — 담배소매인 프록시·어린이집 원천·합성 게이트웨이 (테스트 DB, 먼 미래 연도로 격리 후 정리).

담배소매인은 편의점 인허가 대용이라 industry_id 가 convenience_store 로 고정된다(원천 ≠ 업종).
"""

from datetime import date, datetime

import pytest
from sqlalchemy import delete

from apps.childcare.adapter.outbound.orms.childcare_center_orm import ChildcareCenterOrm
from apps.metric.adapter.outbound.gateways.stats_sources.childcare_source import (
    ChildcareSource,
)
from apps.metric.adapter.outbound.gateways.stats_sources.tobacco_proxy_source import (
    TobaccoProxySource,
)
from apps.metric.adapter.outbound.gateways.stats_sources.yearly_stats_source import (
    YearlyStatsSource,
)
from apps.metric.adapter.outbound.gateways.store_stats_gateway import StoreStatsGateway
from apps.metric.app.dtos.region_industry_metric_dto import YearlyStoreStat
from apps.tobacco.adapter.outbound.orms.tobacco_retailer_orm import TobaccoRetailerOrm
from core.matrix.grid_oracle_database_manager import session_scope

_REGION = "2711059500"  # 중구 대신동 (시드 마스터)
_DISTRICT = "27110"
_YEAR = 3100
_TOBACCO_PREFIX = "test-metric-tobacco-"
_CENTER_PREFIX = "test-metric-cc-"


def _retailer(
    suffix: str,
    *,
    designated: date | None = None,
    permit: date | None = None,
    close: date | None = None,
    cancel: date | None = None,
    region_code: str | None = _REGION,
    status: tuple[str, str] = ("1", "정상영업"),
) -> TobaccoRetailerOrm:
    return TobaccoRetailerOrm(
        retailer_id=f"{_TOBACCO_PREFIX}{suffix}",
        name="시험담배소매인",
        district_code=_DISTRICT,
        region_code=region_code,
        status_code=status[0],
        status_name=status[1],
        designated_date=designated,
        permit_date=permit,
        close_date=close,
        cancel_date=cancel,
        lat=None,
        lng=None,
        road_address=None,
        jibun_address=None,
        source_updated_at=datetime(2026, 9, 19),
    )


def _center(
    suffix: str,
    *,
    approved: date | None,
    abolished: date | None = None,
    last_seen: date,
    region_code: str | None = _REGION,
) -> ChildcareCenterOrm:
    return ChildcareCenterOrm(
        center_id=f"{_CENTER_PREFIX}{suffix}",
        name="시험어린이집",
        type_name="국공립",
        status_name="정상",
        district_code=_DISTRICT,
        region_code=region_code,
        address="대구광역시 중구 시험로 1",
        zipcode=None,
        tel=None,
        lat=None,
        lng=None,
        approved_on=approved,
        paused_from=None,
        paused_until=None,
        abolished_on=abolished,
        first_seen_on=date(_YEAR - 1, 1, 1),
        last_seen_on=last_seen,
    )


def _merge(rows: list) -> None:
    with session_scope() as session:
        for row in rows:
            session.merge(row)


def _cleanup() -> None:
    with session_scope() as session:
        session.execute(
            delete(TobaccoRetailerOrm).where(
                TobaccoRetailerOrm.retailer_id.like(f"{_TOBACCO_PREFIX}%")
            )
        )
        session.execute(
            delete(ChildcareCenterOrm).where(
                ChildcareCenterOrm.center_id.like(f"{_CENTER_PREFIX}%")
            )
        )


def _stat_of(stats: list[YearlyStoreStat], industry_id: str) -> YearlyStoreStat:
    return next(
        s for s in stats if s.region_code == _REGION and s.industry_id == industry_id
    )


@pytest.fixture
def tobacco_rows():
    _merge(
        [
            # 지정일자로 3100 개업 · 미폐업 → 연말 영업 중. 상태명이 '지정취소'여도 폐업일이 없으면 영업 중이다
            _retailer("open", designated=date(_YEAR, 5, 1), status=("5", "지정취소")),
            # 인허가일자만 있는 개업(지정일자 공란) + 3100 폐업
            _retailer("permit-only", permit=date(_YEAR, 2, 1), close=date(_YEAR, 6, 1)),
            # 폐업일자 공란 + 인허가취소일자 → 취소일이 폐업
            _retailer("cancelled", designated=date(_YEAR - 1, 1, 1), cancel=date(_YEAR, 3, 1)),
            # 19일 만에 종료 — 30일 규칙으로 개업·폐업 양쪽에서 제외
            _retailer("short", designated=date(_YEAR, 7, 1), close=date(_YEAR, 7, 20)),
            # 행정동 미배정 — 집계 제외
            _retailer("noregion", designated=date(_YEAR, 8, 1), region_code=None),
        ]
    )
    yield
    _cleanup()


@pytest.fixture
def childcare_rows():
    observed = date(_YEAR, 9, 19)  # 구·군 최신 관측일
    _merge(
        [
            _center("open", approved=date(_YEAR, 4, 1), last_seen=observed),
            _center("running", approved=date(_YEAR - 1, 1, 1), last_seen=observed),
            # 구 최신 관측일보다 앞선 last_seen_on → 소실(폐원 추정) 3100-06-01
            _center("lost", approved=date(_YEAR - 1, 1, 1), last_seen=date(_YEAR, 6, 1)),
            _center("abolished", approved=date(_YEAR - 1, 2, 1), abolished=date(_YEAR, 3, 1), last_seen=observed),
            # 9일 만에 폐지 — 30일 규칙으로 제외
            _center("short", approved=date(_YEAR, 8, 1), abolished=date(_YEAR, 8, 10), last_seen=observed),
        ]
    )
    yield
    _cleanup()


def test_tobacco_proxy_counts_convenience_store_by_designation_dates(tobacco_rows):
    with session_scope() as session:
        stats = TobaccoProxySource().yearly_stats(session, [_YEAR])

    stat = _stat_of(stats, "convenience_store")
    assert (stat.open_count, stat.close_count, stat.store_count) == (2, 2, 1)


def test_childcare_source_treats_vanished_center_as_closed(childcare_rows):
    with session_scope() as session:
        stats = ChildcareSource().yearly_stats(session, [_YEAR])

    stat = _stat_of(stats, "childcare")
    # 개업 1(인가) · 폐업 2(소실 추정 + 폐지) · 연말 운영 중 2 — 9일 폐지 건은 30일 규칙 제외
    assert (stat.open_count, stat.close_count, stat.store_count) == (1, 2, 2)


def test_gateway_merges_all_sources(tobacco_rows, childcare_rows):
    stats = StoreStatsGateway().yearly_stats([_YEAR])
    industries = {s.industry_id for s in stats if s.region_code == _REGION}

    assert {"convenience_store", "childcare"} <= industries
    assert _stat_of(stats, "convenience_store").store_count == 1
    assert _stat_of(stats, "childcare").store_count == 2


class _StubSource(YearlyStatsSource):
    def __init__(self, stats: list[YearlyStoreStat], latest: date | None) -> None:
        self._stats = stats
        self._latest = latest

    def yearly_stats(self, session, years: list[int]) -> list[YearlyStoreStat]:
        return self._stats

    def latest_record_date(self, session) -> date | None:
        return self._latest


def _stub_stat(industry_id: str) -> YearlyStoreStat:
    return YearlyStoreStat(
        region_code=_REGION, industry_id=industry_id, year=_YEAR,
        store_count=1, open_count=0, close_count=0,
    )


def test_gateway_concatenates_every_source_result():
    gateway = StoreStatsGateway(
        sources=[
            _StubSource([_stub_stat("cafe")], None),
            _StubSource([_stub_stat("convenience_store")], None),
            _StubSource([_stub_stat("childcare")], None),
        ]
    )
    assert [s.industry_id for s in gateway.yearly_stats([_YEAR])] == [
        "cafe", "convenience_store", "childcare",
    ]


def test_latest_record_date_is_max_across_sources_ignoring_none():
    gateway = StoreStatsGateway(
        sources=[
            _StubSource([], date(2026, 9, 17)),
            _StubSource([], None),
            _StubSource([], date(2026, 9, 19)),
        ]
    )
    assert gateway.latest_record_date() == date(2026, 9, 19)


def test_latest_record_date_is_none_when_every_source_is_empty():
    gateway = StoreStatsGateway(sources=[_StubSource([], None), _StubSource([], None)])
    assert gateway.latest_record_date() is None
