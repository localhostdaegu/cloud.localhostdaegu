from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from apps.metric.adapter.inbound.api.schemas.region_industry_metric_schema import (
    MetricValueResponse,
    RegionIndustryMetricResponse,
)
from apps.metric.adapter.inbound.mappers.region_industry_metric_mapper import (
    to_industry_risk_response,
    to_metric_value_response,
    to_region_risk_response,
    to_response,
)
from apps.metric.app.ports.input.region_industry_metric_use_case import (
    RegionIndustryMetricUseCase,
)
from apps.metric.app.ports.input.risk_use_case import RiskUseCase
from apps.metric.dependencies.region_industry_metric_dependencies import (
    get_region_industry_metric_use_case,
    get_risk_use_case,
)
from apps.metric.domain.errors import IndustryNotFoundError, MetricNotFoundError

router = APIRouter(prefix="/metrics", tags=["metrics"])


def _not_found(code: str, message: str) -> JSONResponse:
    """에러 바디 단일 형식 {error:{code,message}} (프론트엔드 계약)."""
    return JSONResponse(
        status_code=404, content={"error": {"code": code, "message": message}}
    )


def _bad_request(code: str, message: str) -> JSONResponse:
    """에러 바디 단일 형식 {error:{code,message}} (프론트엔드 계약)."""
    return JSONResponse(
        status_code=400, content={"error": {"code": code, "message": message}}
    )


@router.get("/myself", response_model=RegionIndustryMetricResponse)
def myself(
    use_case: RegionIndustryMetricUseCase = Depends(get_region_industry_metric_use_case),
) -> RegionIndustryMetricResponse:
    return to_response(use_case.myself())


@router.get("", response_model=list[MetricValueResponse])
def list_metric_values(
    industry: str,
    metric: str,
    year: int,
    use_case: RegionIndustryMetricUseCase = Depends(get_region_industry_metric_use_case),
) -> list[MetricValueResponse] | JSONResponse:
    try:
        values = use_case.list_metric_values(industry, metric, year)
    except MetricNotFoundError:
        return _not_found("METRIC_NOT_FOUND", f"지원하지 않는 metric: {metric}")
    except IndustryNotFoundError:
        return _not_found("INDUSTRY_NOT_FOUND", f"지원하지 않는 industry: {industry}")
    return [to_metric_value_response(value) for value in values]


@router.get("/risk", response_model=None)
def get_risk(
    industry: str | None = None,
    region_code: str | None = None,
    year: int | None = None,
    use_case: RiskUseCase = Depends(get_risk_use_case),
) -> dict | list[dict] | JSONResponse:
    """위험도 스코어 — 3형태 지원 (사용자 흐름 B유형 랭킹의 원천).

    - industry만: 해당 업종 전 region 랭킹(내림차순 배열)
    - industry + region_code: 해당 region×industry 단건
    - region_code만: 해당 region의 업종별 랭킹(내림차순 배열)
    데이터가 없으면 (아직 미시딩 포함) 배열 형태는 빈 배열 200을 반환한다.
    """
    if industry and region_code:
        dto = use_case.score_for(region_code, industry, year)
        if dto is None:
            return _not_found(
                "RISK_NOT_FOUND", f"위험도 데이터 없음: region={region_code}, industry={industry}"
            )
        return to_region_risk_response(dto)
    if industry:
        return [to_region_risk_response(d) for d in use_case.rank_by_region(industry, year)]
    if region_code:
        return [to_industry_risk_response(d) for d in use_case.rank_by_industry(region_code, year)]
    return _bad_request("RISK_QUERY_INVALID", "industry 또는 region_code 중 최소 하나는 필요합니다")
