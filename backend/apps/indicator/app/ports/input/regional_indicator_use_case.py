"""Driving Port — regional_indicator UseCase 인터페이스."""

from abc import ABC, abstractmethod

from apps.indicator.app.dtos.regional_indicator_dto import RegionalIndicatorDto


class RegionalIndicatorUseCase(ABC):
    @abstractmethod
    def myself(self) -> RegionalIndicatorDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def list_latest(self, region_code: str) -> list[RegionalIndicatorDto]:
        """행정동의 지표 — indicator_key마다 가장 늦은 기간의 행만 (그 기간의 슬라이스는 전부)."""
