from apps.shock.app.dtos.interest_rate_dto import InterestRateDto
from apps.shock.app.ports.input.interest_rate_use_case import InterestRateUseCase
from apps.shock.app.ports.output.interest_rate_port import InterestRateRepositoryPort
from apps.shock.domain.entities.interest_rate_entity import InterestRate


def _to_dto(entity: InterestRate) -> InterestRateDto:
    return InterestRateDto(
        rate_type=entity.rate_type,
        period=entity.period,
        value_percent=entity.rate,
        value_ratio=entity.ratio,
    )


class InterestRateInteractor(InterestRateUseCase):
    def __init__(self, repository: InterestRateRepositoryPort) -> None:
        self._repository = repository

    def myself(self) -> InterestRateDto:
        return InterestRateDto(rate_type="myself", period="202609", value_percent=1.0, value_ratio=0.01)

    def latest(self, rate_type: str) -> InterestRateDto | None:
        entity = self._repository.find_latest(rate_type)
        return _to_dto(entity) if entity else None
