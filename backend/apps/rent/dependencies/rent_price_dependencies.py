"""Composition Root (DIP) — rent_price 조회 Port에 Adapter를 주입한다 (FastAPI Depends)."""

from apps.rent.adapter.outbound.repositories.rent_price_repository import (
    SqlAlchemyRentPriceRepository,
)
from apps.rent.app.ports.input.rent_price_use_case import RentPriceUseCase
from apps.rent.app.use_cases.rent_price_interactor import RentPriceInteractor


def get_rent_price_use_case() -> RentPriceUseCase:
    return RentPriceInteractor(repository=SqlAlchemyRentPriceRepository())
