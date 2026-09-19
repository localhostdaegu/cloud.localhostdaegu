"""지표 원천 Strategy(GoF) — 원천별 개폐업 집계 계약과 원천 공통 집계 규칙.

원천마다 개업일·폐업일 컬럼과 업종 판정이 다르다(인허가 store / 담배소매인 / 어린이집).
if/elif 로 갈라 쓰지 않고 구현 클래스를 레지스트리에 등록해 합성 게이트웨이가 순회한다.
"""

from abc import ABC, abstractmethod
from datetime import date

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from apps.metric.app.dtos.region_industry_metric_dto import YearlyStoreStat
from apps.metric.domain.short_lived import SHORT_LIVED_MAX_DAYS


class YearlyStatsSource(ABC):
    @abstractmethod
    def yearly_stats(self, session: Session, years: list[int]) -> list[YearlyStoreStat]:
        """연도별 행정동×업종 카운트 (region_code 보유분만)."""

    @abstractmethod
    def latest_record_date(self, session: Session) -> date | None:
        """이 원천의 최신 개업·폐업일. 원천이 비어 있으면 None."""


def year_end_counts(year: int, opened, closed) -> tuple:
    """연도 말 영업 중 · 당해 개업 · 당해 폐업 카운트 3종 — 원천이 달라도 규칙은 하나다."""
    end_of_year = date(year, 12, 31)
    return (
        func.count().filter(opened <= end_of_year, or_(closed.is_(None), closed > end_of_year)),
        func.count().filter(func.extract("year", opened) == year),
        func.count().filter(func.extract("year", closed) == year),
    )


def not_short_lived(opened, closed):
    """개업 직후 종료 건 제외 (OPEN-008) — 기간을 알 수 없는 행(개업일·폐업일 없음)은 그대로 둔다."""
    return or_(
        opened.is_(None),
        closed.is_(None),
        closed - opened > SHORT_LIVED_MAX_DAYS,
    )
