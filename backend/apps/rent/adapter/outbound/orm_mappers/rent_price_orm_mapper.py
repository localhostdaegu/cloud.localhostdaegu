"""Outbound Boundary Gate — entity ↔ ORM 변환 (Repository ↔ DB 경계)."""

from apps.rent.adapter.outbound.orms.rent_price_orm import RentPriceOrm
from apps.rent.domain.entities.rent_price_entity import RentPrice


def to_entity(orm: RentPriceOrm) -> RentPrice:
    return RentPrice(
        id=orm.id,
        building_type=orm.building_type,
        region_name=orm.region_name,
        region_level=orm.region_level,
        period=orm.period,
        rent_per_m2=orm.rent_per_m2,
        vacancy_rate=orm.vacancy_rate,
    )
