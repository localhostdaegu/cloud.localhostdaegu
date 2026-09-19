from dataclasses import dataclass


@dataclass
class RegionalIndicatorDto:
    indicator_key: str
    breakdown: str | None  # None = 슬라이스 없음 (빈 문자열도 None으로 정규화)
    period: str  # YYYYMM — 지표마다 최신 기간이 다르다
    value: float
    unit: str | None
