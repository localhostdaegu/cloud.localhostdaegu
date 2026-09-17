from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_oracle_database_manager import OrmBase


class RegionOrm(OrmBase):
    """행정동 (대구 144개, 읍·면·출장소 포함) — 행정기관코드 10자리."""

    __tablename__ = "region"

    region_code: Mapped[str] = mapped_column(primary_key=True)  # 예: 2711059500 (대신동)
    district_code: Mapped[str] = mapped_column(ForeignKey("district.district_code"))
    name: Mapped[str]
    geometry_ref: Mapped[str | None]  # 경계 GeoJSON 경로 (브이월드 WFS 적재 후 기입)
