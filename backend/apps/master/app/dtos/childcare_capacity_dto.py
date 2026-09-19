"""행정동 어린이집 정원·현원 합계 — 지도 패널 카드 단위 (Metabole ChildcareRegionSummary 전례)."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ChildcareCenterCapacity:
    """시설 1곳의 최신 정원·현원·대기 — 어댑터가 ACL 로 넘기는 입력 단위."""

    capacity: int  # 정원
    child_count: int  # 현원
    waiting_count: int | None  # 입소대기 — 원천 공란은 None 보존
    base_date: date  # 원천 기준일


@dataclass(frozen=True)
class ChildcareCapacityDto:
    center_count: int
    capacity: int
    child_count: int
    occupancy_rate: float | None  # 현원 ÷ 정원 — 정원 0이면 None
    waiting_count: int | None  # 대기 합 — 전 시설 공란이면 None (중복 신청 포함 건수)
    base_date: date  # 합산된 현황 중 최신 기준일

    @classmethod
    def of(cls, centers: list[ChildcareCenterCapacity]) -> "ChildcareCapacityDto | None":
        """운영 중 시설 목록을 합산한다 — 시설이 없으면 None(0으로 꾸미지 않는다)."""
        if not centers:
            return None
        capacity = sum(c.capacity for c in centers)
        child_count = sum(c.child_count for c in centers)
        waitings = [c.waiting_count for c in centers if c.waiting_count is not None]
        return cls(
            center_count=len(centers),
            capacity=capacity,
            child_count=child_count,
            occupancy_rate=round(child_count / capacity, 4) if capacity else None,
            waiting_count=sum(waitings) if waitings else None,
            base_date=max(c.base_date for c in centers),
        )
