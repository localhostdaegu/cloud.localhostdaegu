"""Composition Root (DIP) — interest_rate 조회 Port에 Adapter를 주입한다 (FastAPI Depends)."""

from apps.shock.adapter.outbound.repositories.interest_rate_repository import (
    SqlAlchemyInterestRateRepository,
)
from apps.shock.app.ports.input.interest_rate_use_case import InterestRateUseCase
from apps.shock.app.use_cases.interest_rate_interactor import InterestRateInteractor


def get_interest_rate_use_case() -> InterestRateUseCase:
    return InterestRateInteractor(repository=SqlAlchemyInterestRateRepository())
