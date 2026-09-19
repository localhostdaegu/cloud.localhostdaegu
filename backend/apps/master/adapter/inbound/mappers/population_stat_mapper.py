"""Inbound Boundary Gate — dto ↔ schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.master.adapter.inbound.api.schemas.population_stat_schema import PopulationSummaryResponse
from apps.master.app.dtos.population_stat_dto import PopulationSummaryDto


def to_response(dto: PopulationSummaryDto) -> PopulationSummaryResponse:
    return PopulationSummaryResponse(**asdict(dto))
