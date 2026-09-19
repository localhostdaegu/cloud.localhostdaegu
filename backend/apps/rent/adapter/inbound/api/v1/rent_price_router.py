from fastapi import APIRouter, Depends

from apps.rent.adapter.inbound.api.schemas.rent_price_schema import RentPriceResponse
from apps.rent.adapter.inbound.mappers.rent_price_mapper import to_response
from apps.rent.app.ports.input.rent_price_use_case import RentPriceUseCase
from apps.rent.dependencies.rent_price_dependencies import get_rent_price_use_case

router = APIRouter(prefix="/rents", tags=["rent"])


@router.get("/myself", response_model=RentPriceResponse)
def myself(
    use_case: RentPriceUseCase = Depends(get_rent_price_use_case),
) -> RentPriceResponse:
    return to_response(use_case.myself())


@router.get("/latest", response_model=list[RentPriceResponse])
def latest(
    use_case: RentPriceUseCase = Depends(get_rent_price_use_case),
) -> list[RentPriceResponse]:
    return [to_response(dto) for dto in use_case.latest()]
