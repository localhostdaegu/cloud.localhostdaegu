from dataclasses import asdict

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from apps.consultation.adapter.inbound.api.schemas.consultation_schema import (
    ConsultationDetailResponse,
    ConsultationDocumentRequest,
    ConsultationDocumentResponse,
    ConsultationPlanRequest,
    ConsultationPlanResponse,
    ConsultationSessionCreateRequest,
    ConsultationSessionCreatedResponse,
)
from apps.consultation.adapter.inbound.mappers.consultation_mapper import (
    to_detail_response,
    to_plan_dto,
    to_plan_response,
    to_session_dto,
)
from apps.consultation.app.ports.input.consultation_use_case import ConsultationUseCase
from apps.consultation.dependencies.consultation_dependencies import (
    get_consultation_use_case,
)
from apps.consultation.domain.entities.consultation_entity import DOCUMENT_PURPOSES, PLAN_KINDS

router = APIRouter(prefix="/consultation", tags=["consultation"])


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    # 에러 바디 단일 형식 {error:{code,message}} (프론트엔드 계약)
    return JSONResponse(
        status_code=status_code, content={"error": {"code": code, "message": message}}
    )


@router.get("/myself", response_model=ConsultationDetailResponse)
def myself(
    use_case: ConsultationUseCase = Depends(get_consultation_use_case),
) -> ConsultationDetailResponse:
    """배선 검증 — router → use_case → interactor → port → repository 조립만 확인한다(DB 미사용)."""
    return to_detail_response(use_case.myself())


@router.post("", response_model=ConsultationSessionCreatedResponse, status_code=201)
def create_session(
    request: ConsultationSessionCreateRequest,
    use_case: ConsultationUseCase = Depends(get_consultation_use_case),
) -> ConsultationSessionCreatedResponse:
    """세션 생성 — 보내지 않은 프로필 값은 None으로 저장된다 (0·false로 채우지 않는다)."""
    session_id = use_case.start_session(to_session_dto(request))
    return ConsultationSessionCreatedResponse(session_id=session_id)


@router.get("/{session_id}", response_model=ConsultationDetailResponse)
def get_session(
    session_id: str,
    use_case: ConsultationUseCase = Depends(get_consultation_use_case),
) -> ConsultationDetailResponse | JSONResponse:
    detail = use_case.get_session(session_id)
    if detail is None:
        return _error(404, "SESSION_NOT_FOUND", f"상담 세션을 찾을 수 없습니다: {session_id}")
    return to_detail_response(detail)


@router.put("/{session_id}", response_model=ConsultationDetailResponse)
def replace_session(
    session_id: str,
    request: ConsultationSessionCreateRequest,
    use_case: ConsultationUseCase = Depends(get_consultation_use_case),
) -> ConsultationDetailResponse | JSONResponse:
    """세션 상태 교체 — 선택안을 바꿔 다시 상담자료를 만들어도 세션이 쌓이지 않게 한다.

    부분 병합이 아니라 교체다. 보내지 않은 필드는 기본값으로 덮인다.
    """
    if not use_case.replace_session(session_id, to_session_dto(request)):
        return _error(404, "SESSION_NOT_FOUND", f"상담 세션을 찾을 수 없습니다: {session_id}")
    return to_detail_response(use_case.get_session(session_id))


@router.put("/{session_id}/plans/{plan_kind}", response_model=ConsultationPlanResponse)
def save_plan(
    session_id: str,
    plan_kind: str,
    request: ConsultationPlanRequest,
    use_case: ConsultationUseCase = Depends(get_consultation_use_case),
) -> ConsultationPlanResponse | JSONResponse:
    """계획안 멱등 upsert — 같은 plan_kind로 다시 보내면 새 행 없이 갱신된다."""
    if plan_kind not in PLAN_KINDS:
        return _error(
            400,
            "INVALID_PLAN_KIND",
            f"plan_kind는 {'/'.join(sorted(PLAN_KINDS))} 중 하나여야 합니다: {plan_kind}",
        )
    saved = use_case.save_plan(session_id, plan_kind, to_plan_dto(plan_kind, request))
    if saved is None:
        return _error(404, "SESSION_NOT_FOUND", f"상담 세션을 찾을 수 없습니다: {session_id}")
    return to_plan_response(saved)


@router.post(
    "/{session_id}/documents", response_model=ConsultationDocumentResponse, status_code=201
)
def save_document(
    session_id: str,
    request: ConsultationDocumentRequest,
    use_case: ConsultationUseCase = Depends(get_consultation_use_case),
) -> ConsultationDocumentResponse | JSONResponse:
    """생성된 상담자료를 남긴다 — 어떤 선택안으로 만든 자료인지 함께 기록한다.

    content_hash 는 sha256 으로 내용 변경 여부를 확인하기 위한 것이며,
    블록체인 앵커링이 아니다(이번 범위 밖).
    """
    if request.plan_kind not in PLAN_KINDS:
        return _error(
            400,
            "INVALID_PLAN_KIND",
            f"plan_kind는 {'/'.join(sorted(PLAN_KINDS))} 중 하나여야 합니다: {request.plan_kind}",
        )
    if request.purpose not in DOCUMENT_PURPOSES:
        return _error(
            400,
            "INVALID_PURPOSE",
            f"purpose는 {'/'.join(sorted(DOCUMENT_PURPOSES))} 중 하나여야 합니다: {request.purpose}",
        )
    saved = use_case.save_document(
        session_id, request.plan_kind, request.purpose, request.content_markdown
    )
    if saved is None:
        return _error(
            404,
            "PLAN_NOT_FOUND",
            f"세션 또는 계획안을 찾을 수 없습니다: {session_id}/{request.plan_kind}",
        )
    return ConsultationDocumentResponse(**asdict(saved))
