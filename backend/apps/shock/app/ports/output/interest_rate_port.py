"""Driven Port — interest_rate가 바깥 세계에 요구하는 계약."""

from abc import ABC, abstractmethod

from apps.shock.domain.entities.interest_rate_entity import InterestRate


class InterestRateRepositoryPort(ABC):
    @abstractmethod
    def find_latest(self, rate_type: str) -> InterestRate | None:
        """rate_type 안에서 period(YYYYMM)가 가장 늦은 1행 — 없으면 None."""
