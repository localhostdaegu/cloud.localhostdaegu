"""담배소매인 지정 현황 → 편의점(convenience_store) 대용 원천.

편의점은 LOCALDATA 단일 인허가 코드가 없어 담배소매인 지정이 사실상 출점 가능 여부를 결정한다
(tobacco_retailer ORM 주석). 대용이므로 슈퍼마켓·마트 등 담배 판매점이 함께 섞인다 — 화면·리포트는
"담배소매인 기준"임을 라벨에 드러낸다.

개업 = 지정일자(공란이면 인허가일자), 폐업 = 폐업일자(공란이면 인허가취소일자).
status_code 는 쓰지 않는다 — 영업상태명은 원천 갱신이 늦고 폐업일이 진실이다.
"""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.metric.adapter.outbound.gateways.stats_sources.yearly_stats_source import (
    YearlyStatsSource,
    not_short_lived,
    year_end_counts,
)
from apps.metric.app.dtos.region_industry_metric_dto import YearlyStoreStat
from apps.tobacco.adapter.outbound.orms.tobacco_retailer_orm import TobaccoRetailerOrm

_INDUSTRY_ID = "convenience_store"
_OPENED = func.coalesce(TobaccoRetailerOrm.designated_date, TobaccoRetailerOrm.permit_date)
_CLOSED = func.coalesce(TobaccoRetailerOrm.close_date, TobaccoRetailerOrm.cancel_date)


class TobaccoProxySource(YearlyStatsSource):
    def yearly_stats(self, session: Session, years: list[int]) -> list[YearlyStoreStat]:
        stats: list[YearlyStoreStat] = []
        for year in years:
            rows = session.execute(
                select(
                    TobaccoRetailerOrm.region_code,
                    *year_end_counts(year, _OPENED, _CLOSED),
                )
                .where(
                    TobaccoRetailerOrm.region_code.is_not(None),
                    not_short_lived(_OPENED, _CLOSED),
                )
                .group_by(TobaccoRetailerOrm.region_code)
            ).all()
            stats.extend(
                YearlyStoreStat(
                    region_code=region_code,
                    industry_id=_INDUSTRY_ID,
                    year=year,
                    store_count=store_count,
                    open_count=open_count,
                    close_count=close_count,
                )
                for region_code, store_count, open_count, close_count in rows
            )
        return stats

    def latest_record_date(self, session: Session) -> date | None:
        return session.execute(
            select(func.greatest(func.max(_OPENED), func.max(_CLOSED)))
            .where(TobaccoRetailerOrm.region_code.is_not(None))
        ).scalar_one_or_none()
