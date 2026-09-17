from pydantic import BaseModel


class InterestRateResponse(BaseModel):
    rate_type: str
    period: str  # YYYYMM
    value_percent: float  # 연%
    value_ratio: float  # 비율 — 계산기 loan_rate 단위
