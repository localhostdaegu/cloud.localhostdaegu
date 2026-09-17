from dataclasses import dataclass


@dataclass
class Region:
    """행정동 (대구 144개, 읍·면·출장소 포함) — 행정기관코드 10자리."""

    region_code: str
    district_code: str
    name: str
    geometry_ref: str | None = None  # 경계 GeoJSON 경로 (repo root 상대)
