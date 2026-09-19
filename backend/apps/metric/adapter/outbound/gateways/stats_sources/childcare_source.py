"""어린이집 원천 → childcare 업종 지표.

원천(어린이집정보공개포털)은 폐지 시설을 아예 반환하지 않는다. 그래서 폐원은 두 경로로 잡는다:
폐지일(abolished_on)이 있으면 그 날, 없으면 **소실 추정** — 그 구·군의 최신 관측일에 다시 보이지
않은 시설의 마지막 관측일(last_seen_on)을 폐원일로 본다. 전역 최대가 아니라 구·군 최대를 쓰므로
한 구의 수집이 실패해도 그 구 시설이 통째로 폐원 처리되지 않는다 (Metabole 전례).
"""

from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from apps.childcare.adapter.outbound.orms.childcare_center_orm import ChildcareCenterOrm
from apps.metric.adapter.outbound.gateways.stats_sources.yearly_stats_source import (
    YearlyStatsSource,
    not_short_lived,
    year_end_counts,
)
from apps.metric.app.dtos.region_industry_metric_dto import YearlyStoreStat

_INDUSTRY_ID = "childcare"
_OPENED = ChildcareCenterOrm.approved_on


def _district_latest():
    """구·군별 최신 관측일."""
    return (
        select(
            ChildcareCenterOrm.district_code,
            func.max(ChildcareCenterOrm.last_seen_on).label("seen_on"),
        )
        .group_by(ChildcareCenterOrm.district_code)
        .subquery()
    )


def _closed(district_latest):
    return func.coalesce(
        ChildcareCenterOrm.abolished_on,
        case(
            (ChildcareCenterOrm.last_seen_on < district_latest.c.seen_on,
             ChildcareCenterOrm.last_seen_on),
        ),
    )


def _observed(district_latest):
    return select(ChildcareCenterOrm).join(
        district_latest, district_latest.c.district_code == ChildcareCenterOrm.district_code
    )


class ChildcareSource(YearlyStatsSource):
    def yearly_stats(self, session: Session, years: list[int]) -> list[YearlyStoreStat]:
        district_latest = _district_latest()
        closed = _closed(district_latest)
        stats: list[YearlyStoreStat] = []
        for year in years:
            rows = session.execute(
                _observed(district_latest)
                .with_only_columns(
                    ChildcareCenterOrm.region_code,
                    *year_end_counts(year, _OPENED, closed),
                )
                .where(
                    ChildcareCenterOrm.region_code.is_not(None),
                    not_short_lived(_OPENED, closed),
                )
                .group_by(ChildcareCenterOrm.region_code)
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
        district_latest = _district_latest()
        return session.execute(
            _observed(district_latest)
            .with_only_columns(
                func.greatest(func.max(_OPENED), func.max(_closed(district_latest)))
            )
            .where(ChildcareCenterOrm.region_code.is_not(None))
        ).scalar_one_or_none()
