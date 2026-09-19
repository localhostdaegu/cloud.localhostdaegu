"""store 인허가 원천 — 업종이 행마다 다른 유일한 원천(store.industry_id 그대로)."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.metric.adapter.outbound.gateways.stats_sources.yearly_stats_source import (
    YearlyStatsSource,
    not_short_lived,
    year_end_counts,
)
from apps.metric.app.dtos.region_industry_metric_dto import YearlyStoreStat
from apps.store.adapter.outbound.orms.store_orm import StoreOrm


class StoreTableSource(YearlyStatsSource):
    def yearly_stats(self, session: Session, years: list[int]) -> list[YearlyStoreStat]:
        stats: list[YearlyStoreStat] = []
        for year in years:
            rows = session.execute(
                select(
                    StoreOrm.region_code,
                    StoreOrm.industry_id,
                    *year_end_counts(year, StoreOrm.open_date, StoreOrm.close_date),
                )
                .where(
                    StoreOrm.region_code.is_not(None),
                    not_short_lived(StoreOrm.open_date, StoreOrm.close_date),
                )
                .group_by(StoreOrm.region_code, StoreOrm.industry_id)
            ).all()
            stats.extend(
                YearlyStoreStat(
                    region_code=region_code,
                    industry_id=industry_id,
                    year=year,
                    store_count=store_count,
                    open_count=open_count,
                    close_count=close_count,
                )
                for region_code, industry_id, store_count, open_count, close_count in rows
            )
        return stats

    def latest_record_date(self, session: Session) -> date | None:
        # greatest()는 NULL 인자를 무시 — 폐업 이력이 없어도 최신 개업일을 돌려준다
        return session.execute(
            select(func.greatest(func.max(StoreOrm.open_date), func.max(StoreOrm.close_date)))
            .where(StoreOrm.region_code.is_not(None))
        ).scalar_one_or_none()
