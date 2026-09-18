"""Inbound Boundary Gate — dto ↔ schema 변환 (Router ↔ Interactor 경계).

값을 이름으로만 옮긴다. 여기서 `None`을 채우거나 계산하지 않는다 (전환계획 §4-2·§5-3).
"""

from dataclasses import asdict

from apps.consultation.adapter.inbound.api.schemas.consultation_schema import (
    ConsultationDetailResponse,
    ConsultationNoteResponse,
    ConsultationPlanRequest,
    ConsultationPlanResponse,
    ConsultationSessionCreateRequest,
    ConsultationSessionResponse,
)
from apps.consultation.app.dtos.consultation_dto import (
    ConsultationDetailDto,
    ConsultationPlanDto,
    ConsultationSessionDto,
)


def to_session_dto(request: ConsultationSessionCreateRequest) -> ConsultationSessionDto:
    # session_id는 인터랙터가 uuid4로 발급한다 — 클라이언트가 세션키를 정하지 못하게 빈 값으로 둔다
    return ConsultationSessionDto(session_id="", **request.model_dump())


def to_plan_dto(plan_kind: str, request: ConsultationPlanRequest) -> ConsultationPlanDto:
    return ConsultationPlanDto(plan_kind=plan_kind, **request.model_dump())


def to_plan_response(dto: ConsultationPlanDto) -> ConsultationPlanResponse:
    return ConsultationPlanResponse(**asdict(dto))


def to_detail_response(dto: ConsultationDetailDto) -> ConsultationDetailResponse:
    return ConsultationDetailResponse(
        session=ConsultationSessionResponse(**asdict(dto.session)),
        plans=[to_plan_response(plan) for plan in dto.plans],
        notes=[ConsultationNoteResponse(**asdict(note)) for note in dto.notes],
    )
