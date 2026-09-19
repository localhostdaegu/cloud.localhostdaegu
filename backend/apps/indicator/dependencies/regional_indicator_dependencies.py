"""Composition Root (DIP) — regional_indicator 조회 Port에 Adapter를 주입한다 (FastAPI Depends)."""

from apps.indicator.adapter.outbound.repositories.regional_indicator_repository import (
    SqlAlchemyRegionalIndicatorRepository,
)
from apps.indicator.app.ports.input.regional_indicator_use_case import RegionalIndicatorUseCase
from apps.indicator.app.use_cases.regional_indicator_interactor import RegionalIndicatorInteractor


def get_regional_indicator_use_case() -> RegionalIndicatorUseCase:
    return RegionalIndicatorInteractor(repository=SqlAlchemyRegionalIndicatorRepository())
