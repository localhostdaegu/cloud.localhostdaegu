from pydantic import BaseModel


class PopulationAgeBandResponse(BaseModel):
    label: str  # "0~19세" 등
    latest: int
    base: int


class PopulationSummaryResponse(BaseModel):
    region_code: str
    latest_period: str  # YYYYMM
    base_period: str  # YYYYMM — 202012, 없으면 가장 이른 시점
    latest_total: int  # 남+여
    base_total: int
    age_bands: list[PopulationAgeBandResponse]
