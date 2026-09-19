"""Composition Root (DIP) — population_stat 조회 Port에 Adapter를 주입한다 (FastAPI Depends)."""

from apps.master.adapter.outbound.repositories.population_stat_repository import (
    SqlAlchemyPopulationStatRepository,
)
from apps.master.app.ports.input.population_stat_use_case import PopulationStatUseCase
from apps.master.app.use_cases.population_stat_interactor import PopulationStatInteractor


def get_population_stat_use_case() -> PopulationStatUseCase:
    return PopulationStatInteractor(repository=SqlAlchemyPopulationStatRepository())
