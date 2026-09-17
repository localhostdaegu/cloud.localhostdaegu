"""Outbound Boundary Gate — entity ↔ ORM 변환 (Repository ↔ DB 경계)."""

from apps.shock.adapter.outbound.orms.interest_rate_orm import InterestRateOrm
from apps.shock.domain.entities.interest_rate_entity import InterestRate


def to_entity(orm: InterestRateOrm) -> InterestRate:
    return InterestRate(
        id=orm.id,
        rate_type=orm.rate_type,
        period=orm.period,
        rate=orm.rate,
        unit=orm.unit,
        stat_code=orm.stat_code,
        item_code=orm.item_code,
    )
