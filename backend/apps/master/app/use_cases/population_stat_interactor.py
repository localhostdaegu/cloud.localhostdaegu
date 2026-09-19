from apps.master.app.dtos.population_stat_dto import PopulationAgeBandDto, PopulationSummaryDto
from apps.master.app.ports.input.population_stat_use_case import PopulationStatUseCase
from apps.master.app.ports.output.population_stat_port import PopulationStatRepositoryPort
from apps.master.domain.entities.population_stat_entity import (
    AGE_BANDS,
    select_base_period,
    sum_by_band,
)


class PopulationStatInteractor(PopulationStatUseCase):
    def __init__(self, repository: PopulationStatRepositoryPort) -> None:
        self._repository = repository

    def myself(self) -> PopulationSummaryDto:
        return PopulationSummaryDto(
            region_code="myself",
            latest_period="202606",
            base_period="202012",
            latest_total=1,
            base_total=1,
            age_bands=[PopulationAgeBandDto(label="myself", latest=1, base=1)],
        )

    def summary(self, region_code: str) -> PopulationSummaryDto | None:
        periods = self._repository.find_periods(region_code)
        if not periods:
            return None
        latest_period = max(periods)  # YYYYMM 문자열 — 사전순 = 시간순
        base_period = select_base_period(periods)
        stats = self._repository.find_by_periods(region_code, [latest_period, base_period])
        latest = sum_by_band(stats, latest_period)
        base = sum_by_band(stats, base_period)
        return PopulationSummaryDto(
            region_code=region_code,
            latest_period=latest_period,
            base_period=base_period,
            latest_total=sum(latest),
            base_total=sum(base),
            age_bands=[
                PopulationAgeBandDto(label=label, latest=latest_sum, base=base_sum)
                for (label, _, _), latest_sum, base_sum in zip(AGE_BANDS, latest, base)
            ],
        )
