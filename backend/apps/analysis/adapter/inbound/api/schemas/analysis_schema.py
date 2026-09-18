from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from apps.finance.adapter.inbound.api.schemas.finance_schema import SimulateRequest

PreparationStatus = Literal["not_started", "in_progress", "issued", "unknown"]


class ConsultationProfileRequest(BaseModel):
    """전환계획 §5-1 — 모르는 값은 null·"unknown" 으로 보존한다."""

    business_registered: bool | None = None
    business_age_months: int | None = Field(default=None, ge=0)
    planned_opening_date: str | None = Field(default=None, max_length=10)
    funds_needed_by: str | None = Field(default=None, max_length=10)
    owner_age: int | None = Field(default=None, ge=0, le=120)
    guarantee_status: PreparationStatus = "unknown"
    policy_confirmation_status: PreparationStatus = "unknown"


class ConsultationContextRequest(BaseModel):
    profile: ConsultationProfileRequest
    baseline_finance: SimulateRequest | None = None
    change_reason: str = Field(default="", max_length=1000)
    assumptions: list[str] = Field(default_factory=list, max_length=20)
    open_questions: list[str] = Field(default_factory=list, max_length=20)


class AnalysisStartRequest(BaseModel):
    """프론트 StartAnalysisParams {region, industry, question?} + 선택 확장 finance·purpose·consultation."""

    region: str = Field(min_length=1, max_length=32)
    industry: str = Field(min_length=1, max_length=32)
    question: str | None = Field(default=None, max_length=500)  # 프롬프트 4개·임베딩 질의 2개에 들어간다
    finance: SimulateRequest | None = None
    year: int | None = Field(default=None, ge=2000, le=2100)  # 지도에서 고른 기준연도
    purpose: Literal["review", "handoff"] = "review"
    consultation: ConsultationContextRequest | None = None

    @model_validator(mode="after")
    def _handoff_needs_finance_and_consultation(self) -> Self:
        """상담자료는 선택안과 상담 정보 없이 만들 수 없다 — 빈 값으로 완성본을 내지 않는다(§5-1)."""
        if self.purpose == "handoff" and (self.finance is None or self.consultation is None):
            raise ValueError("purpose=handoff 는 finance 와 consultation 이 모두 필요합니다")
        return self


class AnalysisStartResponse(BaseModel):
    analysis_id: str
