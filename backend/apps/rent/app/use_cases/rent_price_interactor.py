from apps.rent.app.dtos.rent_price_dto import RentPriceDto
from apps.rent.app.ports.input.rent_price_use_case import RentPriceUseCase
from apps.rent.app.ports.output.rent_price_port import RentPriceRepositoryPort
from apps.rent.domain.entities.rent_price_entity import RentPrice


def _to_dto(entity: RentPrice) -> RentPriceDto:
    return RentPriceDto(
        region_name=entity.region_name,
        region_level=entity.region_level,
        building_type=entity.building_type,
        period=entity.period,
        rent_per_m2=entity.rent_per_m2,
        vacancy_rate=entity.vacancy_rate,
    )


class RentPriceInteractor(RentPriceUseCase):
    def __init__(self, repository: RentPriceRepositoryPort) -> None:
        self._repository = repository

    def myself(self) -> RentPriceDto:
        return RentPriceDto(
            region_name="myself",
            region_level=1,
            building_type="small",
            period="2026Q2",
            rent_per_m2=1.0,
            vacancy_rate=1.0,
        )

    def latest(self) -> list[RentPriceDto]:
        # 정렬은 여기서 — DB 콜레이션에 따라 한글 지역명 순서가 달라지지 않게 (코드포인트 = 가나다순)
        entities = sorted(
            self._repository.find_latest(),
            key=lambda e: (e.region_level, e.region_name, e.building_type),
        )
        return [_to_dto(entity) for entity in entities]
