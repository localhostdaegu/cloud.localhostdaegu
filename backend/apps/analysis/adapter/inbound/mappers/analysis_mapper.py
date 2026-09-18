"""Inbound Boundary Gate — schema → AnalysisRequest, AgentEvent → SSE 와이어 포맷.

와이어 포맷은 프론트 mock(src/app/api/mock/analysis/[id]/events/route.ts)과 동일:
event: <type>\ndata: <JSON>\n\n  (JSON 이 개행을 이스케이프하므로 data 는 항상 한 줄)
"""

import json

from apps.analysis.adapter.inbound.api.schemas.analysis_schema import (
    AnalysisStartRequest,
    ConsultationContextRequest,
)
from apps.analysis.domain.agent_event import AgentEvent
from apps.analysis.domain.analysis_context import (
    AnalysisRequest,
    ConsultationContext,
    ConsultationProfile,
)


def to_request(body: AnalysisStartRequest) -> AnalysisRequest:
    return AnalysisRequest(
        region=body.region,
        industry=body.industry,
        question=body.question,
        finance=None if body.finance is None else body.finance.model_dump(),
        purpose=body.purpose,
        consultation=_to_consultation(body.consultation),
    )


def _to_consultation(body: ConsultationContextRequest | None) -> ConsultationContext | None:
    if body is None:
        return None
    return ConsultationContext(
        profile=ConsultationProfile(**body.profile.model_dump()),
        baseline_finance=None if body.baseline_finance is None else body.baseline_finance.model_dump(),
        change_reason=body.change_reason,
        assumptions=list(body.assumptions),
        open_questions=list(body.open_questions),
    )


def to_sse(event: AgentEvent) -> str:
    return f"event: {event.TYPE}\ndata: {json.dumps(event.to_payload(), ensure_ascii=False)}\n\n"
