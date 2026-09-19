from apps.indicator.app.dtos.regional_indicator_dto import RegionalIndicatorDto
from apps.indicator.app.ports.input.regional_indicator_use_case import RegionalIndicatorUseCase
from apps.indicator.app.ports.output.regional_indicator_port import (
    RegionalIndicatorRepositoryPort,
)
from apps.indicator.domain.entities.regional_indicator_entity import RegionalIndicator


def _to_dto(entity: RegionalIndicator) -> RegionalIndicatorDto:
    return RegionalIndicatorDto(
        indicator_key=entity.indicator_key,
        breakdown=entity.breakdown or None,  # 공공데이터 로더는 슬라이스 없음을 ""로 적재한다
        period=entity.period,
        value=entity.value,
        unit=entity.unit,
    )


def latest_per_key(indicators: list[RegionalIndicator]) -> list[RegionalIndicatorDto]:
    """indicator_key마다 가장 늦은 기간의 행만 남긴다 — 지표마다 갱신 주기가 달라 최신 기간이 다르다."""
    latest: dict[str, str] = {}
    for indicator in indicators:
        # YYYYMM 문자열 — 사전순 = 시간순
        latest[indicator.indicator_key] = max(latest.get(indicator.indicator_key, ""), indicator.period)
    dtos = [_to_dto(i) for i in indicators if i.period == latest[i.indicator_key]]
    return sorted(dtos, key=lambda dto: (dto.indicator_key, dto.breakdown or ""))  # 슬라이스 없음이 먼저


class RegionalIndicatorInteractor(RegionalIndicatorUseCase):
    def __init__(self, repository: RegionalIndicatorRepositoryPort) -> None:
        self._repository = repository

    def myself(self) -> RegionalIndicatorDto:
        return _to_dto(self._repository.myself())

    def list_latest(self, region_code: str) -> list[RegionalIndicatorDto]:
        return latest_per_key(self._repository.find_by_region(region_code))
