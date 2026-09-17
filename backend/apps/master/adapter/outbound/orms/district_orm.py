from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_oracle_database_manager import OrmBase


class DistrictOrm(OrmBase):
    """구·군 (대구 8개) — 행정기관코드 앞 5자리."""

    __tablename__ = "district"

    district_code: Mapped[str] = mapped_column(primary_key=True)  # 예: 27110 (중구)
    name: Mapped[str]
    # 행안부 인허가 API의 개방자치단체코드 (예: 3410000 중구) — 2026-09-16 실호출로 8개 구·군 전수 확인
    opn_authority_code: Mapped[str | None] = mapped_column(unique=True)
