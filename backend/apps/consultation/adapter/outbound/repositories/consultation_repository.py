from sqlalchemy import delete, select

from apps.consultation.adapter.outbound.orm_mappers.consultation_orm_mapper import (
    apply_plan_to_orm,
    document_to_orm,
    note_to_entity,
    note_to_orm,
    plan_to_entity,
    plan_to_orm,
    session_to_entity,
    session_to_orm,
)
from apps.consultation.adapter.outbound.orms.consultation_note_orm import ConsultationNoteOrm
from apps.consultation.adapter.outbound.orms.consultation_plan_orm import ConsultationPlanOrm
from apps.consultation.adapter.outbound.orms.consultation_session_orm import (
    ConsultationSessionOrm,
)
from apps.consultation.app.ports.output.consultation_port import ConsultationRepositoryPort
from apps.consultation.domain.entities.consultation_entity import (
    NOTE_TYPES,
    ConsultationDocument,
    ConsultationNote,
    ConsultationPlan,
    ConsultationSession,
)
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyConsultationRepository(ConsultationRepositoryPort):
    """상담 세션 애그리게이트의 PostgreSQL 저장소.

    **계산 결과 8필드(capex·monthly_fixed·bep_revenue·funding_gap·reserve_months·
    operating_reserve·total_required_funds·external_funding_need)는 감사·재현용 스냅샷이다.**
    전환계획 §5-3은 *"클라이언트가 보낸 계산 결과를 리포트의 기준으로 삼지 않는다"*고 규정한다.
    **리포트 생성 경로가 `list_plans()`로 읽은 이 8필드를 리포트의 기준값으로 써서는 안 된다** —
    리포트는 FinanceInput 13필드로 서버에서 다시 계산한다.

    프로필의 `None`은 그대로 NULL로 저장·복원한다. 여기서 기본값을 채우지 않는다.
    """

    def create_session(self, session_entity: ConsultationSession) -> None:
        with session_scope() as session:
            session.add(session_to_orm(session_entity))

    def find_session(self, session_id: str) -> ConsultationSession | None:
        with session_scope() as session:
            orm = session.get(ConsultationSessionOrm, session_id)
            return None if orm is None else session_to_entity(orm)

    def list_plans(self, session_id: str) -> list[ConsultationPlan]:
        with session_scope() as session:
            orms = session.execute(
                select(ConsultationPlanOrm)
                .where(ConsultationPlanOrm.session_id == session_id)
                .order_by(ConsultationPlanOrm.plan_kind)  # baseline, current
            ).scalars()
            return [plan_to_entity(orm) for orm in orms]

    def list_notes(self, session_id: str) -> list[ConsultationNote]:
        with session_scope() as session:
            orms = session.execute(
                select(ConsultationNoteOrm)
                .where(ConsultationNoteOrm.session_id == session_id)
                .order_by(ConsultationNoteOrm.note_type, ConsultationNoteOrm.note_order)
            ).scalars()
            return [note_to_entity(orm) for orm in orms]

    def replace_session(self, session_entity: ConsultationSession) -> bool:
        """교체 — 부분 병합이 아니다. 클라이언트가 늘 전체 초안을 들고 있다."""
        with session_scope() as session:
            orm = session.get(ConsultationSessionOrm, session_entity.session_id)
            if orm is None:
                return False
            for name in _SESSION_REPLACEABLE:
                setattr(orm, name, getattr(session_entity, name))
            orm.updated_at = session_entity.updated_at
            return True

    def find_plan(self, session_id: str, plan_kind: str) -> ConsultationPlan | None:
        with session_scope() as session:
            orm = session.scalars(
                select(ConsultationPlanOrm)
                .where(ConsultationPlanOrm.session_id == session_id)
                .where(ConsultationPlanOrm.plan_kind == plan_kind)
            ).one_or_none()
            return None if orm is None else plan_to_entity(orm)

    def save_document(self, document: ConsultationDocument) -> ConsultationDocument:
        with session_scope() as session:
            session.add(document_to_orm(document))
        return document

    def replace_notes(self, session_id: str, notes: list[ConsultationNote]) -> None:
        """통째로 교체 — 같은 세션에 다시 보내도 행이 누적되지 않는다."""
        for note in notes:
            if note.note_type not in NOTE_TYPES:
                raise ValueError(
                    f"note_type 은 {'/'.join(sorted(NOTE_TYPES))} 중 하나여야 합니다: {note.note_type!r}"
                )
        with session_scope() as session:
            session.execute(
                delete(ConsultationNoteOrm).where(ConsultationNoteOrm.session_id == session_id)
            )
            session.flush()  # 교체 전 삭제 확정
            session.add_all([note_to_orm(note) for note in notes])

    def upsert_plan(self, plan: ConsultationPlan) -> ConsultationPlan:
        with session_scope() as session:
            existing = session.execute(
                select(ConsultationPlanOrm).where(
                    ConsultationPlanOrm.session_id == plan.session_id,
                    ConsultationPlanOrm.plan_kind == plan.plan_kind,
                )
            ).scalar_one_or_none()
            if existing is None:
                orm = plan_to_orm(plan)
                session.add(orm)
            else:
                # 같은 plan_kind 재저장 — UNIQUE(session_id, plan_kind) 위반 없이 갱신(멱등)
                apply_plan_to_orm(plan, existing)
                orm = existing
            session.flush()
            return plan_to_entity(orm)


# 교체 대상 — session_id·created_at 은 바뀌지 않는다.
_SESSION_REPLACEABLE = (
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
