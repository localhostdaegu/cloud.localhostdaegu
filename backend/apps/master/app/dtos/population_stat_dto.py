from dataclasses import dataclass


@dataclass
class PopulationAgeBandDto:
    label: str  # "0~19세" 등
    latest: int
    base: int


@dataclass
class PopulationSummaryDto:
    region_code: str
    latest_period: str  # YYYYMM
    base_period: str  # YYYYMM
    latest_total: int
    base_total: int
    age_bands: list[PopulationAgeBandDto]
