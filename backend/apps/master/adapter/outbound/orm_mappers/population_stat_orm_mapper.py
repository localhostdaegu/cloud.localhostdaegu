"""Outbound Boundary Gate — entity ↔ ORM 변환 (Repository ↔ DB 경계)."""

from apps.master.adapter.outbound.orms.population_stat_orm import PopulationStatOrm
from apps.master.domain.entities.population_stat_entity import PopulationStat


def to_entity(orm: PopulationStatOrm) -> PopulationStat:
    return PopulationStat(
        region_code=orm.region_code,
        period=orm.period,
        gender=orm.gender,
        age_from=orm.age_from,
        age_to=orm.age_to,
        population=orm.population,
    )
