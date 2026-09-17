"""Driving Port — interest_rate UseCase 인터페이스."""

from abc import ABC, abstractmethod

from apps.shock.app.dtos.interest_rate_dto import InterestRateDto


class InterestRateUseCase(ABC):
    @abstractmethod
    def myself(self) -> InterestRateDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12)."""

    @abstractmethod
    def latest(self, rate_type: str) -> InterestRateDto | None:
        """rate_type(base·loan_corp·loan_sme·loan_facility)의 최신 월 금리 — 없으면 None."""
