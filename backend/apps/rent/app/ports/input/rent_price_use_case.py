"""Driving Port — rent_price UseCase 인터페이스."""

from abc import ABC, abstractmethod

from apps.rent.app.dtos.rent_price_dto import RentPriceDto


class RentPriceUseCase(ABC):
    @abstractmethod
    def myself(self) -> RentPriceDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def latest(self) -> list[RentPriceDto]:
        """최신 분기의 (지역×상가유형) 전 행 — region_level·region_name·building_type 오름차순. 없으면 []."""
