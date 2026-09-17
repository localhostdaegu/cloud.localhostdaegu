from sqlalchemy import func, select

from apps.metric.adapter.outbound.orm_mappers.region_industry_metric_orm_mapper import (
    to_entity,
    to_orm,
)
from apps.metric.adapter.outbound.orms.region_industry_metric_orm import (
    RegionIndustryMetricOrm,
)
from apps.metric.app.ports.output.region_industry_metric_port import (
    RegionIndustryMetricRepositoryPort,
)
from apps.metric.domain.entities.region_industry_metric_entity import (
    RegionIndustryMetric,
)
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyRegionIndustryMetricRepository(RegionIndustryMetricRepositoryPort):
    def upsert(self, metrics: list[RegionIndustryMetric]) -> int:
        if not metrics:
            return 0
        with session_scope() as session:
            for metric in metrics:
                session.merge(to_orm(metric))
        return len(metrics)

    def list_by_industry_year(
        self, industry_id: str, year: int
    ) -> list[RegionIndustryMetric]:
        with session_scope() as session:
            rows = (
                session.execute(
                    select(RegionIndustryMetricOrm)
                    .where(
                        RegionIndustryMetricOrm.industry_id == industry_id,
                        RegionIndustryMetricOrm.year == year,
                    )
                    .order_by(RegionIndustryMetricOrm.region_code)
                )
                .scalars()
                .all()
            )
            return [to_entity(row) for row in rows]

    def find(
        self, region_code: str, industry_id: str, year: int
    ) -> RegionIndustryMetric | None:
        with session_scope() as session:
            orm = session.get(RegionIndustryMetricOrm, (region_code, industry_id, year))
            return None if orm is None else to_entity(orm)

    def latest_year(
        self, industry_id: str | None = None, until_year: int | None = None
    ) -> int | None:
        with session_scope() as session:
            stmt = select(func.max(RegionIndustryMetricOrm.year))
            if industry_id is not None:
                stmt = stmt.where(RegionIndustryMetricOrm.industry_id == industry_id)
            if until_year is not None:
                stmt = stmt.where(RegionIndustryMetricOrm.year <= until_year)
            return session.execute(stmt).scalar_one_or_none()

    def list_by_region_year(
        self, region_code: str, year: int
    ) -> list[RegionIndustryMetric]:
        with session_scope() as session:
            rows = (
                session.execute(
                    select(RegionIndustryMetricOrm)
                    .where(
                        RegionIndustryMetricOrm.region_code == region_code,
                        RegionIndustryMetricOrm.year == year,
                    )
                    .order_by(RegionIndustryMetricOrm.industry_id)
                )
                .scalars()
                .all()
            )
            return [to_entity(row) for row in rows]

    def list_latest_by_region(
        self, region_code: str, until_year: int | None = None
    ) -> list[RegionIndustryMetric]:
        with session_scope() as session:
            latest = select(
                RegionIndustryMetricOrm.industry_id,
                func.max(RegionIndustryMetricOrm.year).label("year"),
            ).where(RegionIndustryMetricOrm.region_code == region_code)
            if until_year is not None:
                latest = latest.where(RegionIndustryMetricOrm.year <= until_year)
            latest_year_by_industry = (
                latest
                .group_by(RegionIndustryMetricOrm.industry_id)
                .subquery()
            )
            rows = (
                session.execute(
                    select(RegionIndustryMetricOrm)
                    .join(
                        latest_year_by_industry,
                        (
                            RegionIndustryMetricOrm.industry_id
                            == latest_year_by_industry.c.industry_id
                        )
                        & (RegionIndustryMetricOrm.year == latest_year_by_industry.c.year),
                    )
                    .where(RegionIndustryMetricOrm.region_code == region_code)
                    .order_by(RegionIndustryMetricOrm.industry_id)
                )
                .scalars()
                .all()
            )
            return [to_entity(row) for row in rows]
