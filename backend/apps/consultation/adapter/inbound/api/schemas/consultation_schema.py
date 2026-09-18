from datetime import date, datetime

from pydantic import BaseModel


class ConsultationSessionCreateRequest(BaseModel):
    """세션 생성 입력 — 전 필드가 선택값이다.

    **미입력을 보내지 않으면 `None`으로 남는다.** 프론트엔드는 모르는 값을 `0`·`false`로
    채워 보내지 않는다 (전환계획 §4-2 — 연령 미입력을 자격 충족·미충족으로 단정하지 않는다).

    `region_code`는 행정동 10자리다. 구·군 5자리(`district_code`)를 넣으면 FK 위반이 된다.
    """

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
    assumptions: list[str] = []
    open_questions: list[str] = []


class ConsultationSessionCreatedResponse(BaseModel):
    session_id: str  # uuid4 hex — 이후 조회·저장에 쓰는 익명 세션키


class ConsultationSessionResponse(BaseModel):
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


class ConsultationPlanRequest(BaseModel):
    """계획안 저장 입력 — FinanceInput 13필드(필수) + 계산 결과 8필드(선택).

    결과 8필드는 **감사·재현용 스냅샷**으로만 저장된다. 서버는 이 값을 리포트의 기준으로
    쓰지 않으며, 보내지 않으면 0으로 남는다 (0을 계산 결과로 읽지 말 것 — 전환계획 §5-3).
    """

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
    capex: int = 0
    monthly_fixed: int = 0
    bep_revenue: int = 0
    funding_gap: int = 0
    reserve_months: int = 0
    operating_reserve: int = 0
    total_required_funds: int = 0
    external_funding_need: int = 0


class ConsultationPlanResponse(BaseModel):
    plan_id: str | None = None
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
    capex: int = 0
    monthly_fixed: int = 0
    bep_revenue: int = 0
    funding_gap: int = 0
    reserve_months: int = 0
    operating_reserve: int = 0
    total_required_funds: int = 0
    external_funding_need: int = 0
    computed_at: datetime | None = None


class ConsultationNoteResponse(BaseModel):
    note_type: str  # assumption / open_question
    note_order: int
    content: str


class ConsultationDetailResponse(BaseModel):
    session: ConsultationSessionResponse
    plans: list[ConsultationPlanResponse] = []
    notes: list[ConsultationNoteResponse] = []
