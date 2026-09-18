from dataclasses import asdict
from datetime import datetime
from uuid import uuid4

from apps.consultation.app.dtos.consultation_dto import (
    ConsultationDocumentDto,
    ConsultationDetailDto,
    ConsultationNoteDto,
    ConsultationPlanDto,
    ConsultationSessionDto,
)
from apps.consultation.app.ports.input.consultation_use_case import ConsultationUseCase
from apps.consultation.app.ports.output.consultation_port import ConsultationRepositoryPort
from apps.consultation.domain.entities.consultation_entity import (
    ConsultationDocument,
    ConsultationNote,
    ConsultationPlan,
    ConsultationSession,
)

# FinanceInput 13필드 + 결과 8필드 — DTO ↔ 엔티티가 공유하는 이름 (plan_id·plan_kind는 별도 처리)
_PLAN_VALUE_FIELDS = (
    "deposit",
    "key_money",
    "interior_cost",
    "equipment_cost",
    "monthly_rent",
    "monthly_payroll",
    "monthly_insurance",
    "cost_ratio",
    "fee_ratio",
    "equity",
    "desired_loan",
    "loan_rate",
    "expected_monthly_revenue",
    "capex",
    "monthly_fixed",
    "bep_revenue",
    "funding_gap",
    "reserve_months",
    "operating_reserve",
    "total_required_funds",
    "external_funding_need",
)

_SESSION_PROFILE_FIELDS = (
    "region_code",
    "industry_id",
    "business_registered",
    "business_age_months",
    "planned_opening_date",
    "funds_needed_by",
    "owner_age",
    "guarantee_status",
    "policy_confirmation_status",
    "selected_plan_kind",
    "change_reason",
)


def _to_session_dto(entity: ConsultationSession) -> ConsultationSessionDto:
    return ConsultationSessionDto(**asdict(entity))


def _to_plan_dto(entity: ConsultationPlan) -> ConsultationPlanDto:
    return ConsultationPlanDto(**asdict(entity, dict_factory=_without_session_id))


def _without_session_id(pairs: list[tuple[str, object]]) -> dict:
    return {name: value for name, value in pairs if name != "session_id"}


def _to_note_dto(entity: ConsultationNote) -> ConsultationNoteDto:
    return ConsultationNoteDto(
        note_type=entity.note_type, note_order=entity.note_order, content=entity.content
    )


class ConsultationInteractor(ConsultationUseCase):
    """상담 세션 오케스트레이션 — 저장·조회만 한다.

    **재무 계산을 하지 않는다.** 결과 8필드는 호출자가 준 값을 그대로 저장하며, 여기서
    `operating_reserve` 등을 추정하거나 재무 엔진을 호출하지 않는다 (전환계획 T1의 범위).
    """

    def __init__(self, repository: ConsultationRepositoryPort) -> None:
        self._repository = repository

    def myself(self) -> ConsultationDetailDto:
        return ConsultationDetailDto(
            session=ConsultationSessionDto(
                session_id="myself",
                change_reason="consultation BC 배선 검증",
            )
        )

    def start_session(self, draft: ConsultationSessionDto) -> str:
        now = datetime.now()
        session_id = uuid4().hex
        self._repository.create_session(
            ConsultationSession(
                session_id=session_id,
                created_at=now,
                updated_at=now,
                **{name: getattr(draft, name) for name in _SESSION_PROFILE_FIELDS},
            )
        )
        self._repository.replace_notes(session_id, _to_notes(session_id, draft))
        return session_id

    def get_session(self, session_id: str) -> ConsultationDetailDto | None:
        session = self._repository.find_session(session_id)
        if session is None:
            return None
        return ConsultationDetailDto(
            session=_to_session_dto(session),
            plans=[_to_plan_dto(plan) for plan in self._repository.list_plans(session_id)],
            notes=[_to_note_dto(note) for note in self._repository.list_notes(session_id)],
        )

    def replace_session(self, session_id: str, draft: ConsultationSessionDto) -> bool:
        replaced = self._repository.replace_session(
            ConsultationSession(
                session_id=session_id,
                created_at=None,
                updated_at=datetime.now(),
                **{name: getattr(draft, name) for name in _SESSION_PROFILE_FIELDS},
            )
        )
        if replaced:
            self._repository.replace_notes(session_id, _to_notes(session_id, draft))
        return replaced

    def save_document(
        self, session_id: str, plan_kind: str, purpose: str, content_markdown: str
    ) -> ConsultationDocumentDto | None:
        plan = self._repository.find_plan(session_id, plan_kind)
        if plan is None or plan.plan_id is None:
            return None  # 세션이 없거나 그 계획안을 아직 저장하지 않았다
        saved = self._repository.save_document(
            ConsultationDocument(
                document_id=uuid4().hex,
                session_id=session_id,
                plan_id=plan.plan_id,
                purpose=purpose,
                generated_at=datetime.now(),
                content_markdown=content_markdown,
            )
        )
        return ConsultationDocumentDto(
            document_id=saved.document_id,
            session_id=saved.session_id,
            plan_id=saved.plan_id,
            purpose=saved.purpose,
            generated_at=saved.generated_at,
            content_hash=saved.content_hash,
        )

    def save_plan(
        self, session_id: str, plan_kind: str, plan: ConsultationPlanDto
    ) -> ConsultationPlanDto | None:
        if self._repository.find_session(session_id) is None:
            return None
        saved = self._repository.upsert_plan(
            ConsultationPlan(
                plan_id=plan.plan_id or uuid4().hex,  # 갱신이면 리포지토리가 기존 값을 유지한다
                session_id=session_id,
                plan_kind=plan_kind,
                computed_at=plan.computed_at or datetime.now(),
                **{name: getattr(plan, name) for name in _PLAN_VALUE_FIELDS},
            )
        )
        return _to_plan_dto(saved)


def _to_notes(session_id: str, draft: ConsultationSessionDto) -> list[ConsultationNote]:
    """가정·미확인 항목을 노트로 옮긴다. 순서는 1부터 종류별로 매긴다."""
    return [
        ConsultationNote(session_id, note_type, order, content)
        for note_type, contents in (
            ("assumption", draft.assumptions),
            ("open_question", draft.open_questions),
        )
        for order, content in enumerate(contents, start=1)
    ]
