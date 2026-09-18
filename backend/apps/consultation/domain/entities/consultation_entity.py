"""상담 세션 애그리게이트 — 루트는 ConsultationSession, 나머지는 세션 ID로만 묶인다.

전환계획 §4-2·§5-1의 핵심 불변식: **모름을 0·아니오로 바꾸지 않는다.**
`business_registered`·`owner_age`·`business_age_months`·날짜 필드는 미입력이면 `None`으로 남기며,
어느 계층도 이를 `False`·`0`으로 치환하지 않는다. 사업자등록 전(등록=False, 업력=0)과
미확인(등록=None, 업력=None)은 서로 다른 사실이다.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime

# 전환계획 §5-1 PreparationStatus — 모름은 버리지 않고 "unknown"으로 보존한다
PREPARATION_STATUSES = frozenset({"not_started", "in_progress", "issued", "unknown"})
UNKNOWN_STATUS = "unknown"

# 최초안(baseline) / 현재안(current) — 전환계획 §5-3. 그 외 값은 계획안이 아니다
PLAN_KINDS = frozenset({"baseline", "current"})

# 가정(출처·기준시점) / 미확인 항목 — 전환계획 §5-1
NOTE_TYPES = frozenset({"assumption", "open_question"})

# 상담자료의 용도 — review(AI 계획 점검) / handoff(최종 상담자료)
DOCUMENT_PURPOSES = frozenset({"review", "handoff"})


@dataclass
class ConsultationSession:
    """익명 상담 세션 + 프로필(1:1 인라인).

    `session_id`는 uuid4 hex다 — 로그인·계정이 없으므로 이 키가 유일한 식별자이며,
    추측 가능한 값(순번·이메일 등)을 쓰지 않는다.

    `region_code`는 **행정동 10자리**다. intent 해석 결과의 구·군 5자리(`district_code`)를
    그대로 넣으면 `region` FK 위반이 된다 (전환계획 §1).

    `region_code`·`industry_id`가 `None`일 수 있는 근거: 지역·업종 미정 사용자가 지도에서
    선택한 뒤 합류하는 동선이 있어, 세션이 그보다 먼저 시작될 수 있다.
    """

    session_id: str
    created_at: datetime
    updated_at: datetime
    region_code: str | None = None
    industry_id: str | None = None
    # ConsultationProfile — 미입력은 None으로 보존한다 (0·False 변환 금지)
    business_registered: bool | None = None
    business_age_months: int | None = None
    planned_opening_date: date | None = None
    funds_needed_by: date | None = None
    owner_age: int | None = None
    guarantee_status: str = UNKNOWN_STATUS
    policy_confirmation_status: str = UNKNOWN_STATUS
    selected_plan_kind: str | None = None  # baseline / current / None(미선택)
    change_reason: str = ""  # 조건을 바꾼 이유 — 상담자료의 설명 근거


@dataclass
class ConsultationPlan:
    """계획안 1건 — FinanceInput 13필드(입력) + 계산 결과 8필드(스냅샷).

    **계산 결과 8필드는 감사·재현용 스냅샷이다.** 전환계획 §5-3은 *"클라이언트가 보낸 계산
    결과를 리포트의 기준으로 삼지 않는다"*고 규정한다. 리포트 생성 경로는 이 값을 읽지 말고
    13필드로 서버에서 다시 계산해야 한다.

    `reserve_months`·`operating_reserve`·`total_required_funds`·`external_funding_need`는
    전환계획 T1이 재무 엔진에 추가할 값이다. 이번 범위에서 엔진은 수정하지 않으므로
    **호출자가 준 값을 그대로 저장**하며, 미제공이면 0으로 남는다 (0을 계산 결과로 읽지 말 것).
    """

    plan_id: str
    session_id: str
    plan_kind: str  # baseline(최초안) / current(현재안)
    # FinanceInput 13필드 — 금액은 원 단위 정수, 비율은 기존 FinanceInput 단위 유지
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
    computed_at: datetime
    # 계산 결과 — 감사·재현용 스냅샷 (리포트 기준값 아님)
    capex: int = 0
    monthly_fixed: int = 0
    bep_revenue: int = 0
    funding_gap: int = 0  # 희망대출 반영 후 남는 부족액
    reserve_months: int = 0  # T1 이전에는 0 — 엔진 상수 6을 여기서 추정하지 않는다
    operating_reserve: int = 0
    total_required_funds: int = 0
    external_funding_need: int = 0


@dataclass
class ConsultationNote:
    """가정·미확인 항목 1건.

    전환계획 §5-1: *"단계폼에서 '모름'을 선택한 사실이 숫자 가정으로 바뀌면서 사라지지 않게 한다."*
    그 기록의 저장소이므로, 노트가 비어 있다는 사실을 "확인 완료"로 읽어서는 안 된다.
    """

    session_id: str
    note_type: str  # assumption / open_question
    note_order: int
    content: str
    note_id: int | None = None  # DB autoincrement — 저장 전에는 None


@dataclass
class ConsultationDocument:
    """생성된 상담자료 1건 — 어떤 선택안(plan_id)으로 만들었는지 함께 남긴다.

    `content_hash`는 sha256(content_markdown)이며 **내용 변경 여부 확인용**이다.
    블록체인 앵커링은 구현하지 않으며, 해시의 존재를 블록체인 연동으로 설명하지 않는다.
    """

    document_id: str
    session_id: str
    plan_id: str
    purpose: str  # review / handoff
    generated_at: datetime
    content_markdown: str
    content_hash: str = field(default="")

    def __post_init__(self) -> None:
        if not self.content_hash:
            self.content_hash = content_hash_of(self.content_markdown)


def content_hash_of(content_markdown: str) -> str:
    """sha256(content_markdown) — 상담자료 내용 변경 여부 확인용 (앵커링 아님)."""
    return hashlib.sha256(content_markdown.encode("utf-8")).hexdigest()
