"""어린이집 정원·현원 카드 — 합산 규칙(순수) + 실 DB 게이트웨이 + summary 추가 카드.

합산 규칙은 Metabole ChildcareRegionSummary.of 전례를 따른다: 정원 0이면 가동률 None,
입소대기가 전 시설 공란이면 합계도 None(0으로 추정하지 않는다).
"""

from datetime import date

import pytest
from sqlalchemy import delete

from apps.childcare.adapter.outbound.orms.childcare_center_orm import ChildcareCenterOrm
from apps.childcare.adapter.outbound.orms.childcare_center_stat_orm import (
    ChildcareCenterStatOrm,
)
from apps.master.adapter.outbound.gateways.childcare_capacity_gateway import (
    ChildcareCapacityGateway,
)
from apps.master.app.dtos.childcare_capacity_dto import (
    ChildcareCapacityDto,
    ChildcareCenterCapacity,
)
from apps.master.app.dtos.region_dto import RegionMetricSnapshot
from apps.master.app.ports.output.childcare_capacity_port import ChildcareCapacityPort
from apps.master.app.use_cases.region_interactor import RegionInteractor
from core.matrix.grid_oracle_database_manager import session_scope
from tests.test_master_region_summary import (
    FakeBoundaryReader,
    FakeMetricSummary,
    FakeRepository,
    _YEOKSAM1,
)

_REGION = "2711059500"  # 중구 대신동 (시드 마스터)
_OTHER_REGION = "2711051700"  # 중구 동인동
_DISTRICT = "27110"
_PREFIX = "test-capacity-"
_OBSERVED = date(3100, 9, 19)  # 구·군 최신 관측일 — 실데이터(2026)보다 뒤라 격리된다


def _capacity(capacity: int, child: int, waiting: int | None, base_date: date = date(3100, 9, 19)):
    return ChildcareCenterCapacity(
        capacity=capacity, child_count=child, waiting_count=waiting, base_date=base_date
    )


# --- 합산 규칙 (순수) --------------------------------------------------------


def test_of_sums_capacity_and_takes_latest_base_date():
    dto = ChildcareCapacityDto.of(
        [
            _capacity(39, 25, 3, date(3100, 8, 1)),
            _capacity(20, 20, 5, date(3100, 9, 19)),
        ]
    )
    assert (dto.center_count, dto.capacity, dto.child_count) == (2, 59, 45)
    assert dto.occupancy_rate == 0.7627  # 45 ÷ 59, 소수 4자리
    assert dto.waiting_count == 8
    assert dto.base_date == date(3100, 9, 19)


def test_of_returns_none_occupancy_when_capacity_is_zero():
    assert ChildcareCapacityDto.of([_capacity(0, 0, None)]).occupancy_rate is None


def test_of_keeps_waiting_none_when_every_center_is_blank():
    """입소대기 공란을 0으로 추정하지 않는다 — '대기 없음'과 '미공개'는 다른 사실이다."""
    dto = ChildcareCapacityDto.of([_capacity(39, 25, None), _capacity(20, 20, None)])
    assert dto.waiting_count is None


def test_of_sums_only_disclosed_waiting_counts():
    dto = ChildcareCapacityDto.of([_capacity(39, 25, None), _capacity(20, 20, 4)])
    assert dto.waiting_count == 4


def test_of_returns_none_without_centers():
    assert ChildcareCapacityDto.of([]) is None


# --- 실 DB 게이트웨이 --------------------------------------------------------


def _center(suffix: str, *, region_code: str, last_seen: date) -> ChildcareCenterOrm:
    return ChildcareCenterOrm(
        center_id=f"{_PREFIX}{suffix}",
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
        approved_on=date(2001, 3, 2),
        paused_from=None,
        paused_until=None,
        abolished_on=None,
        first_seen_on=date(3099, 1, 1),
        last_seen_on=last_seen,
    )


def _stat(suffix: str, base_date: date, capacity: int, child: int, waiting: int | None):
    return ChildcareCenterStatOrm(
        center_id=f"{_PREFIX}{suffix}",
        base_date=base_date,
        capacity=capacity,
        child_count=child,
        waiting_count=waiting,
        class_count=7,
        staff_count=10,
    )


@pytest.fixture
def centers():
    with session_scope() as session:
        for row in [
            _center("a", region_code=_REGION, last_seen=_OBSERVED),
            _center("b", region_code=_REGION, last_seen=_OBSERVED),
            # 구 최신 관측일에 보이지 않음 — 운영 중이 아니므로 합산에서 빠진다
            _center("gone", region_code=_REGION, last_seen=date(3100, 6, 1)),
            _center("other", region_code=_OTHER_REGION, last_seen=_OBSERVED),
        ]:
            session.merge(row)
        for row in [
            _stat("a", date(3100, 1, 1), 39, 10, 0),  # 옛 기준일 — 최신에 밀린다
            _stat("a", _OBSERVED, 39, 25, 3),
            _stat("b", _OBSERVED, 20, 20, None),
            _stat("gone", _OBSERVED, 100, 90, 50),
            _stat("other", _OBSERVED, 77, 70, 7),
        ]:
            session.merge(row)
    yield
    with session_scope() as session:
        session.execute(
            delete(ChildcareCenterStatOrm).where(
                ChildcareCenterStatOrm.center_id.like(f"{_PREFIX}%")
            )
        )
        session.execute(
            delete(ChildcareCenterOrm).where(ChildcareCenterOrm.center_id.like(f"{_PREFIX}%"))
        )


def test_gateway_sums_latest_stat_of_operating_centers_in_region(centers):
    dto = ChildcareCapacityGateway().region_summary(_REGION)

    assert (dto.center_count, dto.capacity, dto.child_count) == (2, 59, 45)
    assert dto.waiting_count == 3  # 공란 시설은 합에서 제외, 다른 행정동·소실 시설도 제외
    assert dto.base_date == _OBSERVED


def test_gateway_returns_none_for_region_without_centers():
    assert ChildcareCapacityGateway().region_summary("2711054500") is None


# --- summary 추가 카드 -------------------------------------------------------


class FakeChildcareCapacity(ChildcareCapacityPort):
    def __init__(self, dto: ChildcareCapacityDto | None) -> None:
        self._dto = dto

    def region_summary(self, region_code: str) -> ChildcareCapacityDto | None:
        return self._dto


def _interactor(dto: ChildcareCapacityDto | None) -> RegionInteractor:
    return RegionInteractor(
        repository=FakeRepository([_YEOKSAM1]),
        boundary_reader=FakeBoundaryReader(),
        metric_summary=FakeMetricSummary(
            RegionMetricSnapshot(store_count=62, closure_rate=0.0, growth_rate=0.0)
        ),
        childcare_capacity=FakeChildcareCapacity(dto),
    )


def test_summary_appends_capacity_cards_for_childcare():
    dto = ChildcareCapacityDto.of([_capacity(2059, 1663, 120)])
    cards = _interactor(dto).summary("1168064000", "childcare").cards

    assert [(c.label, c.value) for c in cards[3:]] == [
        ("정원 대비 현원", "1663/2059 (80.8%)"),
        ("입소대기", "120명"),
    ]


def test_summary_marks_waiting_undisclosed_when_source_is_blank():
    dto = ChildcareCapacityDto.of([_capacity(39, 25, None)])
    cards = _interactor(dto).summary("1168064000", "childcare").cards
    assert (cards[4].label, cards[4].value) == ("입소대기", "미공개")


def test_summary_keeps_three_cards_for_other_industries():
    cards = _interactor(ChildcareCapacityDto.of([_capacity(39, 25, 3)])).summary(
        "1168064000", "cafe"
    ).cards
    assert len(cards) == 3
