from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from apps.shock.adapter.inbound.api.schemas.interest_rate_schema import InterestRateResponse
from apps.shock.adapter.inbound.mappers.interest_rate_mapper import to_response
from apps.shock.app.ports.input.interest_rate_use_case import InterestRateUseCase
from apps.shock.dependencies.interest_rate_dependencies import get_interest_rate_use_case

router = APIRouter(prefix="/shocks/rates", tags=["shock"])


@router.get("/myself", response_model=InterestRateResponse)
def myself(
    use_case: InterestRateUseCase = Depends(get_interest_rate_use_case),
) -> InterestRateResponse:
    return to_response(use_case.myself())


@router.get("/latest", response_model=InterestRateResponse)
def latest(
    rate_type: str,
    use_case: InterestRateUseCase = Depends(get_interest_rate_use_case),
) -> InterestRateResponse | JSONResponse:
    dto = use_case.latest(rate_type)
    if dto is None:
        # 에러 바디 단일 형식 {error:{code,message}} (프론트엔드 계약)
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "RATE_NOT_FOUND",
                    "message": f"적재된 금리가 없는 rate_type: {rate_type}",
                }
            },
        )
    return to_response(dto)
