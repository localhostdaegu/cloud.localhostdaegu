from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상 테이블이 메타데이터에 항상 존재하도록 보장
import apps.consultation.adapter.outbound.orms.consultation_session_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class ConsultationPlanOrm(OrmBase):
    """계획안(최초안/현재안) — FinanceInput 13필드 + 계산 결과 8필드.

    `UniqueConstraint(session_id, plan_kind)`가 세션당 baseline/current 각 1건을 보장한다.
    같은 plan_kind로 두 번 저장하면 새 행이 생기지 않고 갱신된다(멱등).

    **계산 결과 8필드는 감사·재현용 스냅샷이다.** 전환계획 §5-3 *"클라이언트가 보낸 계산
    결과를 리포트의 기준으로 삼지 않는다"* — 리포트 경로는 13필드로 서버에서 재계산한다.
    `scenarios`·`stress`는 13필드에서 파생되므로 저장하지 않는다(3NF).
    """

    __tablename__ = "consultation_plan"
    __table_args__ = (UniqueConstraint("session_id", "plan_kind"),)

    plan_id: Mapped[str] = mapped_column(primary_key=True)  # uuid4 hex
    session_id: Mapped[str] = mapped_column(
        ForeignKey("consultation_session.session_id"), index=True
    )
    plan_kind: Mapped[str]  # baseline(최초안) / current(현재안)

    # FinanceInput 13필드 — 금액은 원 단위 정수, 비율은 기존 FinanceInput 단위 유지
    deposit: Mapped[int]
    key_money: Mapped[int]
    interior_cost: Mapped[int]
    equipment_cost: Mapped[int]
    monthly_rent: Mapped[int]
    monthly_payroll: Mapped[int]
    monthly_insurance: Mapped[int]
    cost_ratio: Mapped[float]
    fee_ratio: Mapped[float]
    equity: Mapped[int]
    desired_loan: Mapped[int]
    loan_rate: Mapped[float]
    expected_monthly_revenue: Mapped[int]

    # 계산 결과 — 감사·재현용 스냅샷 (리포트 기준값 아님)
    capex: Mapped[int]
    monthly_fixed: Mapped[int]
    bep_revenue: Mapped[int]
    funding_gap: Mapped[int]  # 희망대출 반영 후 남는 부족액 (기존 산식 보존)
    reserve_months: Mapped[int]  # T1이 엔진에 추가할 값 — 그전에는 호출자가 준 값(미제공 시 0)
    operating_reserve: Mapped[int]  # monthly_fixed × reserve_months
    total_required_funds: Mapped[int]  # capex + operating_reserve
    external_funding_need: Mapped[int]  # max(0, total_required_funds − equity)
    computed_at: Mapped[datetime]
