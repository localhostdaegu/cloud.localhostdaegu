"""Inbound Boundary Gate — dto ↔ schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.rent.adapter.inbound.api.schemas.rent_price_schema import RentPriceResponse
from apps.rent.app.dtos.rent_price_dto import RentPriceDto


def to_response(dto: RentPriceDto) -> RentPriceResponse:
    return RentPriceResponse(**asdict(dto))
