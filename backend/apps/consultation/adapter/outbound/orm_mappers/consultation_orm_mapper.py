"""Outbound Boundary Gate — entity ↔ ORM 변환 (Repository ↔ DB 경계).

프로필의 `None`은 어느 방향에서도 `False`·`0`으로 바뀌지 않는다 (전환계획 §4-2).
필드를 이름으로만 옮기므로 기본값 채우기·추정이 끼어들 자리가 없다.
"""

from apps.consultation.adapter.outbound.orms.consultation_document_orm import (
    ConsultationDocumentOrm,
)
from apps.consultation.adapter.outbound.orms.consultation_note_orm import ConsultationNoteOrm
from apps.consultation.adapter.outbound.orms.consultation_plan_orm import ConsultationPlanOrm
from apps.consultation.adapter.outbound.orms.consultation_session_orm import (
    ConsultationSessionOrm,
)
from apps.consultation.domain.entities.consultation_entity import (
    ConsultationDocument,
    ConsultationNote,
    ConsultationPlan,
    ConsultationSession,
)

_SESSION_FIELDS = (
    "session_id",
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
    "created_at",
    "updated_at",
)

_PLAN_FIELDS = (
    "plan_id",
    "session_id",
    "plan_kind",
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
    "computed_at",
)

_NOTE_FIELDS = ("note_id", "session_id", "note_type", "note_order", "content")

_DOCUMENT_FIELDS = (
    "document_id",
    "session_id",
    "plan_id",
    "purpose",
    "generated_at",
    "content_markdown",
    "content_hash",
)


def session_to_orm(entity: ConsultationSession) -> ConsultationSessionOrm:
    return ConsultationSessionOrm(**{name: getattr(entity, name) for name in _SESSION_FIELDS})


def session_to_entity(orm: ConsultationSessionOrm) -> ConsultationSession:
    return ConsultationSession(**{name: getattr(orm, name) for name in _SESSION_FIELDS})


def plan_to_orm(entity: ConsultationPlan) -> ConsultationPlanOrm:
    return ConsultationPlanOrm(**{name: getattr(entity, name) for name in _PLAN_FIELDS})


def plan_to_entity(orm: ConsultationPlanOrm) -> ConsultationPlan:
    return ConsultationPlan(**{name: getattr(orm, name) for name in _PLAN_FIELDS})


def apply_plan_to_orm(entity: ConsultationPlan, orm: ConsultationPlanOrm) -> None:
    """멱등 upsert 갱신 — plan_id·session_id·plan_kind는 행의 식별자이므로 덮어쓰지 않는다."""
    for name in _PLAN_FIELDS:
        if name in ("plan_id", "session_id", "plan_kind"):
            continue
        setattr(orm, name, getattr(entity, name))


def note_to_orm(entity: ConsultationNote) -> ConsultationNoteOrm:
    return ConsultationNoteOrm(**{name: getattr(entity, name) for name in _NOTE_FIELDS})


def note_to_entity(orm: ConsultationNoteOrm) -> ConsultationNote:
    return ConsultationNote(**{name: getattr(orm, name) for name in _NOTE_FIELDS})


def document_to_orm(entity: ConsultationDocument) -> ConsultationDocumentOrm:
    return ConsultationDocumentOrm(**{name: getattr(entity, name) for name in _DOCUMENT_FIELDS})


def document_to_entity(orm: ConsultationDocumentOrm) -> ConsultationDocument:
    return ConsultationDocument(**{name: getattr(orm, name) for name in _DOCUMENT_FIELDS})
