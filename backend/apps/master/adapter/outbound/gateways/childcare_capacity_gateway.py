"""Driven Adapter — childcare BC 테이블에서 행정동 정원·현원 합계 취득 (cross-BC 접근은 어댑터에서만).

운영 중 = 그 구·군의 최신 관측일(max last_seen_on)에 관측된 시설. 전역 최대가 아니라 구·군 단위라
한 구의 수집이 실패해도 그 구 시설이 통째로 사라지지 않는다. 현황은 시설별 최신 base_date 1건만 쓴다
(Metabole operating_centers_with_latest_stat 전례).
"""

from sqlalchemy import and_, func, select

from apps.childcare.adapter.outbound.orms.childcare_center_orm import ChildcareCenterOrm
from apps.childcare.adapter.outbound.orms.childcare_center_stat_orm import (
    ChildcareCenterStatOrm,
)
from apps.master.app.dtos.childcare_capacity_dto import (
    ChildcareCapacityDto,
    ChildcareCenterCapacity,
)
from apps.master.app.ports.output.childcare_capacity_port import ChildcareCapacityPort
from core.matrix.grid_oracle_database_manager import session_scope


def _operating_center_stats(region_code: str):
    district_latest = (
        select(
            ChildcareCenterOrm.district_code,
            func.max(ChildcareCenterOrm.last_seen_on).label("seen_on"),
        )
        .group_by(ChildcareCenterOrm.district_code)
        .subquery()
    )
    stat_latest = (
        select(
            ChildcareCenterStatOrm.center_id,
            func.max(ChildcareCenterStatOrm.base_date).label("base_date"),
        )
        .group_by(ChildcareCenterStatOrm.center_id)
        .subquery()
    )
    return (
        select(
            ChildcareCenterStatOrm.capacity,
            ChildcareCenterStatOrm.child_count,
            ChildcareCenterStatOrm.waiting_count,
            ChildcareCenterStatOrm.base_date,
        )
        .select_from(ChildcareCenterOrm)
        .join(
            district_latest,
            and_(
                district_latest.c.district_code == ChildcareCenterOrm.district_code,
                district_latest.c.seen_on == ChildcareCenterOrm.last_seen_on,
            ),
        )
        .join(stat_latest, stat_latest.c.center_id == ChildcareCenterOrm.center_id)
        .join(
            ChildcareCenterStatOrm,
            and_(
                ChildcareCenterStatOrm.center_id == stat_latest.c.center_id,
                ChildcareCenterStatOrm.base_date == stat_latest.c.base_date,
            ),
        )
        .where(ChildcareCenterOrm.region_code == region_code)
    )


class ChildcareCapacityGateway(ChildcareCapacityPort):
    def region_summary(self, region_code: str) -> ChildcareCapacityDto | None:
        with session_scope() as session:
            rows = session.execute(_operating_center_stats(region_code)).all()
        return ChildcareCapacityDto.of(
            [
                ChildcareCenterCapacity(
                    capacity=capacity,
                    child_count=child_count,
                    waiting_count=waiting_count,
                    base_date=base_date,
                )
                for capacity, child_count, waiting_count, base_date in rows
            ]
        )
