"""Driven Port — population_stat이 바깥 세계에 요구하는 계약."""

from abc import ABC, abstractmethod

from apps.master.domain.entities.population_stat_entity import PopulationStat


class PopulationStatRepositoryPort(ABC):
    @abstractmethod
    def find_periods(self, region_code: str) -> list[str]:
        """행정동에 적재된 연월(YYYYMM) 목록 — 없으면 빈 리스트."""

    @abstractmethod
    def find_by_periods(self, region_code: str, periods: list[str]) -> list[PopulationStat]:
        """행정동×지정 연월들의 전 행(성별×연령구간)."""
