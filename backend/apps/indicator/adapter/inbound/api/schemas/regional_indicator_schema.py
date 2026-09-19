from pydantic import BaseModel


class RegionalIndicatorResponse(BaseModel):
    indicator_key: str
    breakdown: str | None  # null = 슬라이스 없음
    period: str  # YYYYMM
    value: float
    unit: str | None
