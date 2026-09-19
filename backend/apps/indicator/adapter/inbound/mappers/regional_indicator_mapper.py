"""Inbound Boundary Gate — dto ↔ schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.indicator.adapter.inbound.api.schemas.regional_indicator_schema import (
    RegionalIndicatorResponse,
)
from apps.indicator.app.dtos.regional_indicator_dto import RegionalIndicatorDto


def to_response(dto: RegionalIndicatorDto) -> RegionalIndicatorResponse:
    return RegionalIndicatorResponse(**asdict(dto))
