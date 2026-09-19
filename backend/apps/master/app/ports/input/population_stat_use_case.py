"""Driving Port — population_stat UseCase 인터페이스."""

from abc import ABC, abstractmethod

from apps.master.app.dtos.population_stat_dto import PopulationSummaryDto


class PopulationStatUseCase(ABC):
    @abstractmethod
    def myself(self) -> PopulationSummaryDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def summary(self, region_code: str) -> PopulationSummaryDto | None:
        """행정동의 최신 vs 기준 시점 인구 요약(남+여, 4개 연령대) — 적재 행이 없으면 None."""
