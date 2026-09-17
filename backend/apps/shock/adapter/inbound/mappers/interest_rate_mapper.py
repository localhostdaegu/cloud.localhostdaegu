"""Inbound Boundary Gate — dto ↔ schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.shock.adapter.inbound.api.schemas.interest_rate_schema import InterestRateResponse
from apps.shock.app.dtos.interest_rate_dto import InterestRateDto


def to_response(dto: InterestRateDto) -> InterestRateResponse:
    return InterestRateResponse(**asdict(dto))
