"""consultation 인터랙터 — 가짜 리포지토리 주입(DB 불필요).

핵심 검증: 미입력(None)이 저장·조회 왕복에서 False·0으로 바뀌지 않는다 (전환계획 §4-2).
"""

from datetime import datetime

import pytest

from apps.consultation.app.dtos.consultation_dto import (
    ConsultationPlanDto,
    ConsultationSessionDto,
)
from apps.consultation.app.ports.output.consultation_port import ConsultationRepositoryPort
from apps.consultation.app.use_cases.consultation_interactor import ConsultationInteractor
from apps.consultation.domain.entities.consultation_entity import (
    ConsultationNote,
    ConsultationPlan,
    ConsultationSession,
)


class FakeConsultationRepository(ConsultationRepositoryPort):
    """in-memory Driven Adapter — Port 계약만 지키면 인터랙터는 DB와 구분하지 못한다."""

    def __init__(self) -> None:
        self.sessions: dict[str, ConsultationSession] = {}
        self.plans: dict[tuple[str, str], ConsultationPlan] = {}
        self.notes: list[ConsultationNote] = []

    def create_session(self, session: ConsultationSession) -> None:
        self.sessions[session.session_id] = session

    def find_session(self, session_id: str) -> ConsultationSession | None:
        return self.sessions.get(session_id)

    def list_plans(self, session_id: str) -> list[ConsultationPlan]:
        return [p for (sid, _), p in sorted(self.plans.items()) if sid == session_id]

    def list_notes(self, session_id: str) -> list[ConsultationNote]:
        return [n for n in self.notes if n.session_id == session_id]

    def replace_notes(self, session_id: str, notes: list[ConsultationNote]) -> None:
        self.notes = [n for n in self.notes if n.session_id != session_id] + list(notes)

    def upsert_plan(self, plan: ConsultationPlan) -> ConsultationPlan:
        key = (plan.session_id, plan.plan_kind)
        existing = self.plans.get(key)
        if existing is not None:
            plan.plan_id = existing.plan_id  # 갱신은 기존 plan_id 유지 (멱등)
        self.plans[key] = plan
        return plan


def _plan_dto(plan_kind: str = "current", **overrides) -> ConsultationPlanDto:
    values = dict(
        plan_kind=plan_kind,
        deposit=30_000_000,
        key_money=10_000_000,
        interior_cost=40_000_000,
        equipment_cost=20_000_000,
        monthly_rent=1_800_000,
        monthly_payroll=3_000_000,
        monthly_insurance=200_000,
        cost_ratio=0.35,
        fee_ratio=0.05,
        equity=60_000_000,
        desired_loan=50_000_000,
        loan_rate=0.045,
        expected_monthly_revenue=18_000_000,
    )
    values.update(overrides)
    return ConsultationPlanDto(**values)


@pytest.fixture
def interactor() -> ConsultationInteractor:
    return ConsultationInteractor(repository=FakeConsultationRepository())


def test_myself_returns_wiring_payload_without_touching_repository(interactor):
    detail = interactor.myself()
    assert detail.session.session_id == "myself"
    assert detail.plans == []
    assert detail.notes == []


def test_start_session_issues_uuid4_hex_session_id(interactor):
    session_id = interactor.start_session(ConsultationSessionDto(session_id=""))
    assert len(session_id) == 32
    assert session_id != ""


def test_unknown_profile_stays_none_through_round_trip(interactor):
    """'모름'은 0·아니오가 되지 않는다 — 사업자등록 전과 미확인은 다른 사실이다."""
    session_id = interactor.start_session(ConsultationSessionDto(session_id=""))

    detail = interactor.get_session(session_id)

    assert detail is not None
    assert detail.session.business_registered is None
    assert detail.session.owner_age is None
    assert detail.session.business_age_months is None
    assert detail.session.planned_opening_date is None
    assert detail.session.guarantee_status == "unknown"


def test_answered_profile_keeps_false_and_zero_distinct_from_none(interactor):
    """False·0은 '모름'이 아니라 답변이다 — None과 구분해 보존한다."""
    session_id = interactor.start_session(
        ConsultationSessionDto(
            session_id="", business_registered=False, business_age_months=0, owner_age=39
        )
    )

    detail = interactor.get_session(session_id)

    assert detail.session.business_registered is False
    assert detail.session.business_age_months == 0
    assert detail.session.owner_age == 39


def test_get_session_returns_none_for_unknown_session(interactor):
    assert interactor.get_session("does-not-exist") is None


def test_save_plan_returns_none_for_unknown_session(interactor):
    assert interactor.save_plan("does-not-exist", "current", _plan_dto()) is None


def test_save_plan_round_trips_finance_input(interactor):
    session_id = interactor.start_session(ConsultationSessionDto(session_id=""))

    saved = interactor.save_plan(session_id, "current", _plan_dto())

    assert saved.plan_kind == "current"
    assert saved.deposit == 30_000_000
    assert saved.loan_rate == 0.045
    assert saved.computed_at is not None
    assert interactor.get_session(session_id).plans[0].expected_monthly_revenue == 18_000_000


def test_save_plan_twice_with_same_kind_updates_in_place(interactor):
    session_id = interactor.start_session(ConsultationSessionDto(session_id=""))
    first = interactor.save_plan(session_id, "current", _plan_dto())

    second = interactor.save_plan(session_id, "current", _plan_dto(monthly_rent=2_500_000))

    assert second.plan_id == first.plan_id
    plans = interactor.get_session(session_id).plans
    assert len(plans) == 1
    assert plans[0].monthly_rent == 2_500_000


def test_interactor_does_not_compute_result_fields(interactor):
    """재무 엔진을 호출하지 않는다 — 호출자가 준 값을 그대로 저장한다 (T1 범위)."""
    session_id = interactor.start_session(ConsultationSessionDto(session_id=""))

    saved = interactor.save_plan(
        session_id, "baseline", _plan_dto("baseline", reserve_months=6, operating_reserve=42)
    )

    assert saved.reserve_months == 6
    assert saved.operating_reserve == 42
    assert saved.capex == 0  # 미제공 — 엔진에서 채우지 않는다
    assert saved.total_required_funds == 0


def test_start_session_records_assumptions_and_open_questions(interactor):
    """§5-1 — '모름'이 숫자 가정으로 바뀌며 사라지지 않게 노트로 남긴다."""
    session_id = interactor.start_session(
        ConsultationSessionDto(
            session_id="",
            assumptions=["원가율 57% 가정"],
            open_questions=["설비 견적 미확정", "보증기관 보증서 진행 상태 미확인"],
        )
    )

    notes = interactor.get_session(session_id).notes

    assert [(n.note_type, n.note_order, n.content) for n in notes] == [
        ("assumption", 1, "원가율 57% 가정"),
        ("open_question", 1, "설비 견적 미확정"),
        ("open_question", 2, "보증기관 보증서 진행 상태 미확인"),
    ]
