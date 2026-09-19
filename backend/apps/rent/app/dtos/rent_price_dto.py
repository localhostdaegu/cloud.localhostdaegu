from dataclasses import dataclass


@dataclass
class RentPriceDto:
    region_name: str
    region_level: int  # 1 대구 평균 / 2 개별 상권
    building_type: str  # "small" / "medium_large"
    period: str  # YYYYQn
    rent_per_m2: float | None  # 천원/㎡ (R-ONE 원값)
    vacancy_rate: float | None  # %
