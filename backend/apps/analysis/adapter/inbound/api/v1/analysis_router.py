from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from apps.analysis.adapter.inbound.api.schemas.analysis_schema import (
    AnalysisStartRequest,
    AnalysisStartResponse,
)
from apps.analysis.adapter.inbound.mappers.analysis_mapper import to_request, to_sse
from apps.analysis.app.ports.input.analysis_use_case import AnalysisUseCase
from apps.analysis.dependencies.analysis_dependencies import get_analysis_use_case
from apps.analysis.domain.errors import AnalysisNotFoundError

router = APIRouter(prefix="/analysis", tags=["analysis"])

# X-Accel-Buffering: 배포 시 리버스 프록시가 스트림을 모아 보내지 않도록.
_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


@router.get("/myself")
def myself() -> dict:
    return {"app": "analysis", "status": "wired"}


@router.post("", response_model=AnalysisStartResponse)
def start_analysis(
    body: AnalysisStartRequest,
    use_case: AnalysisUseCase = Depends(get_analysis_use_case),
) -> AnalysisStartResponse:
    return AnalysisStartResponse(analysis_id=use_case.start(to_request(body)))


@router.get("/{analysis_id}/events", response_model=None)
def stream_events(
    analysis_id: str,
    use_case: AnalysisUseCase = Depends(get_analysis_use_case),
) -> StreamingResponse | JSONResponse:
    """SSE — 동기 제너레이터는 Starlette 가 스레드풀에서 순회한다(DB·LLM 동기 호출 허용)."""
    try:
        events = use_case.stream(analysis_id)
    except AnalysisNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "ANALYSIS_NOT_FOUND", "message": f"분석 요청 없음 또는 이미 소비됨: {analysis_id}"}},
        )
    return StreamingResponse(
        (to_sse(event) for event in events), media_type="text/event-stream", headers=_SSE_HEADERS
    )
