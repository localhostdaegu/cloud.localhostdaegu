from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from apps.master.adapter.inbound.api.schemas.population_stat_schema import PopulationSummaryResponse
from apps.master.adapter.inbound.mappers.population_stat_mapper import to_response
from apps.master.app.ports.input.population_stat_use_case import PopulationStatUseCase
from apps.master.dependencies.population_stat_dependencies import get_population_stat_use_case

router = APIRouter(prefix="/populations", tags=["population"])


@router.get("/myself", response_model=PopulationSummaryResponse)
def myself(
    use_case: PopulationStatUseCase = Depends(get_population_stat_use_case),
) -> PopulationSummaryResponse:
    return to_response(use_case.myself())


@router.get("/{region_code}/summary", response_model=PopulationSummaryResponse)
def summary(
    region_code: str,
    use_case: PopulationStatUseCase = Depends(get_population_stat_use_case),
) -> PopulationSummaryResponse | JSONResponse:
    dto = use_case.summary(region_code)
    if dto is None:
        # 에러 바디 단일 형식 {error:{code,message}} (프론트엔드 계약)
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "POPULATION_NOT_FOUND",
                    "message": f"적재된 인구가 없는 region_code: {region_code}",
                }
            },
        )
    return to_response(dto)
