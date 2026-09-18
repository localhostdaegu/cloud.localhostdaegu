"""Application DTO — Router ↔ Interactor 사이를 오가는 값. 프레임워크 타입을 담지 않는다."""

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class ConsultationSessionDto:
    """세션 + 프로필. 미입력은 None으로 보존한다 (0·False 변환 금지)."""

    session_id: str
    region_code: str | None = None
    industry_id: str | None = None
    business_registered: bool | None = None
    business_age_months: int | None = None
    planned_opening_date: date | None = None
    funds_needed_by: date | None = None
    owner_age: int | None = None
    guarantee_status: str = "unknown"
    policy_confirmation_status: str = "unknown"
    selected_plan_kind: str | None = None
    change_reason: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class ConsultationPlanDto:
    """계획안. 결과 8필드는 감사·재현용 스냅샷 — 리포트의 기준값이 아니다 (전환계획 §5-3)."""

    plan_kind: str
    deposit: int
    key_money: int
    interior_cost: int
    equipment_cost: int
    monthly_rent: int
    monthly_payroll: int
    monthly_insurance: int
    cost_ratio: float
    fee_ratio: float
    equity: int
    desired_loan: int
    loan_rate: float
    expected_monthly_revenue: int
    plan_id: str | None = None  # 저장 전에는 None (upsert가 기존 plan_id를 유지)
    capex: int = 0
    monthly_fixed: int = 0
    bep_revenue: int = 0
    funding_gap: int = 0
    reserve_months: int = 0
    operating_reserve: int = 0
    total_required_funds: int = 0
    external_funding_need: int = 0
    computed_at: datetime | None = None


@dataclass
class ConsultationNoteDto:
    note_type: str  # assumption / open_question
    note_order: int
    content: str


@dataclass
class ConsultationDetailDto:
    """세션 조회 응답 — 세션 + 계획안 + 노트를 한 번에 돌려준다."""

    session: ConsultationSessionDto
    plans: list[ConsultationPlanDto] = field(default_factory=list)
    notes: list[ConsultationNoteDto] = field(default_factory=list)
