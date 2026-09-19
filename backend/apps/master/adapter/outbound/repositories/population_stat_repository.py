from sqlalchemy import select

from apps.master.adapter.outbound.orm_mappers.population_stat_orm_mapper import to_entity
from apps.master.adapter.outbound.orms.population_stat_orm import PopulationStatOrm
from apps.master.app.ports.output.population_stat_port import PopulationStatRepositoryPort
from apps.master.domain.entities.population_stat_entity import PopulationStat
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyPopulationStatRepository(PopulationStatRepositoryPort):
    def find_periods(self, region_code: str) -> list[str]:
        with session_scope() as session:
            return list(
                session.execute(
                    select(PopulationStatOrm.period)
                    .where(PopulationStatOrm.region_code == region_code)
                    .distinct()
                ).scalars()
            )

    def find_by_periods(self, region_code: str, periods: list[str]) -> list[PopulationStat]:
        with session_scope() as session:
            orms = session.execute(
                select(PopulationStatOrm).where(
                    PopulationStatOrm.region_code == region_code,
                    PopulationStatOrm.period.in_(periods),
                )
            ).scalars()
            return [to_entity(orm) for orm in orms]
