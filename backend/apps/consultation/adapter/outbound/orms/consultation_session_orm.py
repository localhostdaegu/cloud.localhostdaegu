from datetime import date, datetime

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상(마스터 허브) 테이블이 메타데이터에 항상 존재하도록 보장
import apps.master.adapter.outbound.orms.industry_orm  # noqa: F401
import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class ConsultationSessionOrm(OrmBase):
    """익명 상담 세션 + 프로필(1:1 인라인, 3NF 위반 아님 — 전 필드가 session_id에 완전 함수 종속).

    **미입력은 NULL이다.** `business_registered`·`owner_age`·`business_age_months`를
    `False`·`0`으로 채우지 않는다 — 사업자등록 전과 미확인은 다른 사실이다 (전환계획 §4-2).

    `region_code`는 **행정동 10자리**(`region.region_code`)다. intent의 구·군 5자리
    (`district_code`)를 넣으면 FK 위반이 된다 (전환계획 §1).
    """

    __tablename__ = "consultation_session"
    __table_args__ = (
        # 최근 갱신 순 조회 — 세션 정리·운영 점검용
        Index("ix_consultation_session_updated", "updated_at"),
    )

    session_id: Mapped[str] = mapped_column(primary_key=True)  # uuid4 hex — 로그인 없는 익명 세션키
    region_code: Mapped[str | None] = mapped_column(ForeignKey("region.region_code"))
    industry_id: Mapped[str | None] = mapped_column(ForeignKey("industry.industry_id"))
    # ConsultationProfile — 모름은 NULL로 보존 (전환계획 §5-1)
    business_registered: Mapped[bool | None]
    business_age_months: Mapped[int | None]
    planned_opening_date: Mapped[date | None]
    funds_needed_by: Mapped[date | None]
    owner_age: Mapped[int | None]
    guarantee_status: Mapped[str]  # not_started / in_progress / issued / unknown
    policy_confirmation_status: Mapped[str]
    selected_plan_kind: Mapped[str | None]  # baseline / current / NULL(미선택)
    change_reason: Mapped[str]  # 조건 변경 이유 (기본 "")
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
