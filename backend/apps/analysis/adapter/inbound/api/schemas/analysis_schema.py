from pydantic import BaseModel, Field

from apps.finance.adapter.inbound.api.schemas.finance_schema import SimulateRequest


class AnalysisStartRequest(BaseModel):
    """프론트 StartAnalysisParams {region, industry, question?} + 백엔드 선택 확장 finance."""

    region: str = Field(min_length=1)
    industry: str = Field(min_length=1)
    question: str | None = None
    finance: SimulateRequest | None = None


class AnalysisStartResponse(BaseModel):
    analysis_id: str
