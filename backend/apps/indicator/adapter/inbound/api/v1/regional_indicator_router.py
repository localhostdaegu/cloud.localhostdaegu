from fastapi import APIRouter, Depends

from apps.indicator.adapter.inbound.api.schemas.regional_indicator_schema import (
    RegionalIndicatorResponse,
)
from apps.indicator.adapter.inbound.mappers.regional_indicator_mapper import to_response
from apps.indicator.app.ports.input.regional_indicator_use_case import RegionalIndicatorUseCase
from apps.indicator.dependencies.regional_indicator_dependencies import (
    get_regional_indicator_use_case,
)

router = APIRouter(prefix="/indicators", tags=["indicator"])


@router.get("/myself", response_model=RegionalIndicatorResponse)
def myself(
    use_case: RegionalIndicatorUseCase = Depends(get_regional_indicator_use_case),
) -> RegionalIndicatorResponse:
    return to_response(use_case.myself())


@router.get("", response_model=list[RegionalIndicatorResponse])
def list_latest(
    region_code: str,
    use_case: RegionalIndicatorUseCase = Depends(get_regional_indicator_use_case),
) -> list[RegionalIndicatorResponse]:
    return [to_response(dto) for dto in use_case.list_latest(region_code)]
