from dataclasses import dataclass


@dataclass
class InterestRateDto:
    rate_type: str
    period: str  # YYYYMM
    value_percent: float  # 연% (ECOS 원값)
    value_ratio: float  # 비율 — 계산기 loan_rate 단위
