from pydantic import BaseModel, Field

from apps.finance.adapter.inbound.api.schemas.finance_schema import SimulateRequest


class AnalysisStartRequest(BaseModel):
    """프론트 StartAnalysisParams {region, industry, question?} + 백엔드 선택 확장 finance."""

    region: str = Field(min_length=1, max_length=32)
    industry: str = Field(min_length=1, max_length=32)
    question: str | None = Field(default=None, max_length=500)  # 프롬프트 4개·임베딩 질의 2개에 들어간다
    finance: SimulateRequest | None = None


class AnalysisStartResponse(BaseModel):
    analysis_id: str
