from apps.metric.app.dtos.region_industry_metric_dto import RiskScoreDto
from apps.metric.app.ports.input.risk_use_case import RiskUseCase
from apps.metric.app.ports.output.region_industry_metric_port import (
    RegionIndustryMetricRepositoryPort,
    StoreStatsPort,
)
from apps.metric.app.use_cases.complete_year import complete_year_cap, resolve_year
from apps.metric.domain.entities.region_industry_metric_entity import (
    RegionIndustryMetric,
)
from apps.metric.domain.risk import percentile_rank, risk_score


def _rankable(rows: list[RegionIndustryMetric]) -> list[RegionIndustryMetric]:
    """closure_rate·growth_rate가 없는 행(전년 표본 부재, build 가드)은 백분위 풀에서 제외한다."""
    return [r for r in rows if r.closure_rate is not None and r.growth_rate is not None]


def _to_dto(row: RegionIndustryMetric, pool: list[RegionIndustryMetric]) -> RiskScoreDto:
    closure_pct = percentile_rank(row.closure_rate, [r.closure_rate for r in pool])
    density_pct = percentile_rank(row.store_count, [r.store_count for r in pool])
    growth_pct = percentile_rank(row.growth_rate, [r.growth_rate for r in pool])
    score = risk_score(closure_pct, density_pct, growth_pct)
    return RiskScoreDto(
        region_code=row.region_code,
        industry_id=row.industry_id,
        score=score.score,
        grade=score.grade,
        components=score.components,
    )


class RiskInteractor(RiskUseCase):
    def __init__(
        self, repository: RegionIndustryMetricRepositoryPort, store_stats: StoreStatsPort
    ) -> None:
        self._repository = repository
        self._store_stats = store_stats

    def rank_by_region(self, industry_id: str, year: int | None) -> list[RiskScoreDto]:
        target_year = resolve_year(year, industry_id, self._repository, self._store_stats)
        if target_year is None:
            return []
        pool = _rankable(self._repository.list_by_industry_year(industry_id, target_year))
        scored = [_to_dto(row, pool) for row in pool]
        return sorted(scored, key=lambda d: d.score, reverse=True)

    def score_for(
        self, region_code: str, industry_id: str, year: int | None
    ) -> RiskScoreDto | None:
        target_year = resolve_year(year, industry_id, self._repository, self._store_stats)
        if target_year is None:
            return None
        pool = _rankable(self._repository.list_by_industry_year(industry_id, target_year))
        row = next((r for r in pool if r.region_code == region_code), None)
        return None if row is None else _to_dto(row, pool)

    def rank_by_industry(self, region_code: str, year: int | None) -> list[RiskScoreDto]:
        # year 미지정 시 업종마다 최신 연도가 다를 수 있어(예: A업종 2025, B업종 2023)
        # 전역 latest_year() 하나로 필터링하면 다른 연도의 업종 행이 조용히 누락된다.
        # 각 행 자신의 year(list_latest_by_region가 업종별로 고른 최신 연도)를 그대로
        # 풀 조회에 사용해 업종별 연도 불일치를 허용한다. 단, 부분 연도는 마지막 완결 연도 상한으로 제외.
        if year is not None:
            region_rows = _rankable(self._repository.list_by_region_year(region_code, year))
        else:
            region_rows = _rankable(
                self._repository.list_latest_by_region(
                    region_code, until_year=complete_year_cap(self._store_stats)
                )
            )
        scored = [
            _to_dto(
                row,
                _rankable(self._repository.list_by_industry_year(row.industry_id, row.year)),
            )
            for row in region_rows
        ]
        return sorted(scored, key=lambda d: d.score, reverse=True)
