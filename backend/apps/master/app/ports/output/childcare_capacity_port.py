"""Driven Port — 지도 패널이 어린이집 정원·현원 합계를 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod

from apps.master.app.dtos.childcare_capacity_dto import ChildcareCapacityDto


class ChildcareCapacityPort(ABC):
    @abstractmethod
    def region_summary(self, region_code: str) -> ChildcareCapacityDto | None:
        """해당 행정동의 운영 중 어린이집 정원·현원 합계. 시설이 없으면 None."""
