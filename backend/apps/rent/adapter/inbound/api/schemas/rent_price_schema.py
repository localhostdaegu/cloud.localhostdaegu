from pydantic import BaseModel


class RentPriceResponse(BaseModel):
    """R-ONE 상권별 임대 시세 1행 — 값은 원천 단위 그대로(환산 없음).

    rent_per_m2 단위는 천원/㎡ (rent_price_orm·rone_gateway 주석 근거), vacancy_rate 는 %.
    """

    region_name: str
    region_level: int  # 1 대구 평균 / 2 개별 상권
    building_type: str  # "small" 소규모 상가 / "medium_large" 중대형 상가
    period: str  # YYYYQn
    rent_per_m2: float | None  # 천원/㎡ — 지표 미적재 시 null
    vacancy_rate: float | None  # %
