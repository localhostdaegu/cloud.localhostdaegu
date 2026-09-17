"""위험도 스코어 검증 — 도메인 함수·백분위·인터랙터 3형태·GET /metrics/risk (프론트엔드 계약)."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from apps.metric.app.dtos.region_industry_metric_dto import YearlyStoreStat

from apps.metric.app.dtos.region_industry_metric_dto import RiskScoreDto
from apps.metric.app.ports.output.region_industry_metric_port import (
    RegionIndustryMetricRepositoryPort,
    StoreStatsPort,
)
from apps.metric.app.use_cases.risk_interactor import RiskInteractor
from apps.metric.dependencies.region_industry_metric_dependencies import get_risk_use_case
from apps.metric.domain.entities.region_industry_metric_entity import RegionIndustryMetric
from apps.metric.domain.risk import percentile_rank, risk_score
from main import app

# ---------------------------------------------------------------------------
# Step 1: 도메인 함수 — risk_score (브리프 verbatim)
# ---------------------------------------------------------------------------


def test_weights_sum():
    # 대구 조정 산식: 폐업률 0.4 + 경쟁밀도 0.4 + 신규진입 급증 0.2 (백분위 0~1 입력)
    # (부트캠프 원식의 매출감소·프랜차이즈포화 축은 카드매출 부재로 로드맵 — docs/daegunavi.md §8)
    s = risk_score(closure_pct=1.0, density_pct=1.0, growth_pct=1.0)
    assert s.score == 100


def test_grade_bands():
    assert risk_score(0.9, 0.9, 0.9).grade == "red"  # >= 70
    assert risk_score(0.5, 0.5, 0.5).grade == "yellow"  # 40~69
    assert risk_score(0.1, 0.1, 0.1).grade == "green"  # < 40


def test_components_reported():
    s = risk_score(0.8, 0.2, 0.5)
    assert s.components == {"closure": 32.0, "density": 8.0, "growth": 10.0}


# ---------------------------------------------------------------------------
# 백분위 순수 함수 — percentile_rank (동순위 중간값, N=1 → 0.5)
# ---------------------------------------------------------------------------


def test_percentile_rank_ties_and_singleton():
    assert percentile_rank(5, [5]) == 0.5
    assert percentile_rank(2, [1, 2, 2, 3]) == 0.5
    assert percentile_rank(1, [1, 2, 2, 3]) == 0.125
    assert percentile_rank(3, [1, 2, 2, 3]) == 0.875


# ---------------------------------------------------------------------------
# 인터랙터 — 3형태 (업종 전 region / region×industry 단건 / region 전 업종)
# ---------------------------------------------------------------------------


class FakeRepository(RegionIndustryMetricRepositoryPort):
    def __init__(self, metrics: list[RegionIndustryMetric]) -> None:
        self._metrics = metrics

    def upsert(self, metrics: list[RegionIndustryMetric]) -> int:
        raise NotImplementedError

    def list_by_industry_year(
        self, industry_id: str, year: int
    ) -> list[RegionIndustryMetric]:
        return [
            m for m in self._metrics if m.industry_id == industry_id and m.year == year
        ]

    def find(
        self, region_code: str, industry_id: str, year: int
    ) -> RegionIndustryMetric | None:
        raise NotImplementedError

    def latest_year(
        self, industry_id: str | None = None, until_year: int | None = None
    ) -> int | None:
        years = [
            m.year
            for m in self._metrics
            if (industry_id is None or m.industry_id == industry_id)
            and (until_year is None or m.year <= until_year)
        ]
        return max(years) if years else None

    def list_by_region_year(
        self, region_code: str, year: int
    ) -> list[RegionIndustryMetric]:
        return [
            m for m in self._metrics if m.region_code == region_code and m.year == year
        ]

    def list_latest_by_region(
        self, region_code: str, until_year: int | None = None
    ) -> list[RegionIndustryMetric]:
        region_rows = [
            m
            for m in self._metrics
            if m.region_code == region_code and (until_year is None or m.year <= until_year)
        ]
        latest_year_by_industry: dict[str, int] = {}
        for m in region_rows:
            latest_year_by_industry[m.industry_id] = max(
                m.year, latest_year_by_industry.get(m.industry_id, m.year)
            )
        return [
            m
            for m in region_rows
            if m.year == latest_year_by_industry[m.industry_id]
        ]


class FakeStoreStats(StoreStatsPort):
    """store 원천 최신 기록일만 흉내 — None이면 데이터 없음(완결 연도 상한 없음)."""

    def __init__(self, latest: date | None = None) -> None:
        self._latest = latest

    def yearly_stats(self, years: list[int]) -> list[YearlyStoreStat]:
        raise NotImplementedError

    def latest_record_date(self) -> date | None:
        return self._latest


def _m(
    region_code: str,
    industry_id: str,
    closure: float | None,
    store: int,
    growth: float | None,
    year: int = 2025,
) -> RegionIndustryMetric:
    return RegionIndustryMetric(
        region_code=region_code,
        industry_id=industry_id,
        year=year,
        store_count=store,
        open_count=0,
        close_count=0,
        closure_rate=closure,
        growth_rate=growth,
    )


# cafe 업종 3-region 풀 — closure/store/growth가 모두 동일 순서로 커지도록 설계해
# 수작업 검산이 쉽게 만든다. (A: 최저위험, C: 최고위험)
_CAFE_POOL = [
    _m("R1", "cafe", 0.0, 10, 0.0),
    _m("R2", "cafe", 0.5, 20, 0.5),
    _m("R3", "cafe", 1.0, 30, 1.0),
]
_BAKERY_POOL = [
    _m("R1", "bakery", 1.0, 5, 1.0),
    _m("R2", "bakery", 0.0, 1, 0.0),
]


def test_rank_by_region_returns_desc_sorted_scores():
    interactor = RiskInteractor(repository=FakeRepository(_CAFE_POOL), store_stats=FakeStoreStats())
    ranking = interactor.rank_by_region("cafe", year=None)
    assert [d.region_code for d in ranking] == ["R3", "R2", "R1"]
    assert ranking[0].score == 83.3
    assert ranking[0].grade == "red"
    assert ranking[1].score == 50.0
    assert ranking[1].grade == "yellow"
    assert ranking[2].score == 16.7
    assert ranking[2].grade == "green"


def test_rank_by_region_uses_latest_year_when_not_given():
    old = _m("R1", "cafe", 0.0, 1, 0.0, year=2020)
    new = _m("R1", "cafe", 1.0, 1, 1.0, year=2025)
    interactor = RiskInteractor(repository=FakeRepository([old, new]), store_stats=FakeStoreStats())
    ranking = interactor.rank_by_region("cafe", year=None)
    assert len(ranking) == 1
    assert ranking[0].score == risk_score(0.5, 0.5, 0.5).score  # N=1 -> percentile 0.5


def test_rank_by_region_empty_when_no_data():
    interactor = RiskInteractor(repository=FakeRepository([]), store_stats=FakeStoreStats())
    assert interactor.rank_by_region("general_restaurants", year=None) == []


def test_score_for_returns_single_region_result():
    interactor = RiskInteractor(repository=FakeRepository(_CAFE_POOL), store_stats=FakeStoreStats())
    dto = interactor.score_for("R2", "cafe", year=None)
    assert isinstance(dto, RiskScoreDto)
    assert dto.region_code == "R2"
    assert dto.score == 50.0
    assert dto.grade == "yellow"


def test_score_for_none_when_region_missing():
    interactor = RiskInteractor(repository=FakeRepository(_CAFE_POOL), store_stats=FakeStoreStats())
    assert interactor.score_for("R9", "cafe", year=None) is None


def test_score_for_none_when_no_data():
    interactor = RiskInteractor(repository=FakeRepository([]), store_stats=FakeStoreStats())
    assert interactor.score_for("R1", "cafe", year=None) is None


def test_rank_by_industry_returns_desc_sorted_scores_across_industries():
    interactor = RiskInteractor(repository=FakeRepository(_CAFE_POOL + _BAKERY_POOL), store_stats=FakeStoreStats())
    ranking = interactor.rank_by_industry("R1", year=None)
    assert [d.industry_id for d in ranking] == ["bakery", "cafe"]
    assert ranking[0].score == 75.0
    assert ranking[0].grade == "red"
    assert ranking[1].score == 16.7
    assert ranking[1].grade == "green"


def test_rank_by_industry_empty_when_no_data():
    interactor = RiskInteractor(repository=FakeRepository([]), store_stats=FakeStoreStats())
    assert interactor.rank_by_industry("R1", year=None) == []


def test_rankable_excludes_rows_with_none_rates():
    metrics = [
        _m("R1", "cafe", 0.5, 10, 0.5),
        _m("R2", "cafe", None, 20, None),  # 전년 표본 부재 -> 랭킹 제외
    ]
    interactor = RiskInteractor(repository=FakeRepository(metrics), store_stats=FakeStoreStats())
    ranking = interactor.rank_by_region("cafe", year=None)
    assert [d.region_code for d in ranking] == ["R1"]


# ---------------------------------------------------------------------------
# API — GET /metrics/risk (3형태 + 데이터 없음 200 빈 응답 + 에러 바디)
# ---------------------------------------------------------------------------


def _client(metrics: list[RegionIndustryMetric]) -> TestClient:
    fake = RiskInteractor(repository=FakeRepository(metrics), store_stats=FakeStoreStats())
    app.dependency_overrides[get_risk_use_case] = lambda: fake
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_risk_endpoint_industry_only_returns_region_ranking():
    client = _client(_CAFE_POOL)
    response = client.get("/metrics/risk?industry=cafe")
    assert response.status_code == 200
    body = response.json()
    assert [row["region_code"] for row in body] == ["R3", "R2", "R1"]
    assert body[0]["components"] == {"closure": 33.3, "density": 33.3, "growth": 16.7}


def test_risk_endpoint_region_and_industry_returns_single_object():
    client = _client(_CAFE_POOL)
    response = client.get("/metrics/risk?industry=cafe&region_code=R2")
    assert response.status_code == 200
    body = response.json()
    assert body["region_code"] == "R2"
    assert body["score"] == 50.0


def test_risk_endpoint_region_only_returns_industry_ranking():
    client = _client(_CAFE_POOL + _BAKERY_POOL)
    response = client.get("/metrics/risk?region_code=R1")
    assert response.status_code == 200
    body = response.json()
    assert [row["industry_id"] for row in body] == ["bakery", "cafe"]


def test_risk_endpoint_no_seed_data_returns_200_empty_array():
    """인허가 수집 전(Task 4 대기) region_industry_metric이 비어 있어도 500이 아닌 200+빈 배열."""
    client = _client([])
    response = client.get("/metrics/risk?industry=general_restaurants")
    assert response.status_code == 200
    assert response.json() == []


def test_risk_endpoint_404_when_region_industry_combo_missing():
    client = _client(_CAFE_POOL)
    response = client.get("/metrics/risk?industry=cafe&region_code=R9")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "RISK_NOT_FOUND"


def test_risk_endpoint_400_when_no_query_params():
    client = _client(_CAFE_POOL)
    response = client.get("/metrics/risk")
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "RISK_QUERY_INVALID"


def test_risk_endpoint_year_param_overrides_latest():
    old = _m("R1", "cafe", 0.0, 1, 0.0, year=2020)
    new = _m("R1", "cafe", 1.0, 1, 1.0, year=2025)
    client = _client([old, new])
    response = client.get("/metrics/risk?industry=cafe&region_code=R1&year=2020")
    assert response.status_code == 200
    body = response.json()
    assert body["components"] == {"closure": 20.0, "density": 20.0, "growth": 10.0}


# ---------------------------------------------------------------------------
# Fix — rank_by_industry의 업종별 연도 해석 (전역 latest_year 하나로 필터링하면
# 업종마다 최신 연도가 다를 때 행이 조용히 누락된다: bakery만 2023, cafe는 2025)
# ---------------------------------------------------------------------------

_BAKERY_POOL_2023_ONLY = [
    _m("R1", "bakery", 1.0, 5, 1.0, year=2023),
    _m("R2", "bakery", 0.0, 1, 0.0, year=2023),
]


def test_rank_by_industry_keeps_industries_with_different_latest_years():
    # cafe는 2025년까지 데이터가 있고, bakery는 2023년에만 데이터가 있다(2024·2025 없음).
    # 전역 latest_year()(=2025) 하나로 region_code 행을 필터링하면 bakery 행이 사라진다.
    interactor = RiskInteractor(
        repository=FakeRepository(_CAFE_POOL + _BAKERY_POOL_2023_ONLY),
        store_stats=FakeStoreStats(),
    )
    ranking = interactor.rank_by_industry("R1", year=None)

    assert [d.industry_id for d in ranking] == ["bakery", "cafe"]  # 둘 다 등장, desc 정렬
    assert ranking[0].score == 75.0  # bakery: 2023년 자기 풀(R1,R2) 기준 백분위
    assert ranking[0].grade == "red"
    assert ranking[1].score == 16.7  # cafe: 2025년 자기 풀(R1,R2,R3) 기준 백분위
    assert ranking[1].grade == "green"


def test_risk_endpoint_region_only_keeps_industries_with_different_latest_years():
    client = _client(_CAFE_POOL + _BAKERY_POOL_2023_ONLY)
    response = client.get("/metrics/risk?region_code=R1")
    assert response.status_code == 200
    body = response.json()
    assert [row["industry_id"] for row in body] == ["bakery", "cafe"]
    assert body[0]["score"] == 75.0
    assert body[1]["score"] == 16.7


# ---------------------------------------------------------------------------
# 기본 연도 = 마지막 완결 연도 — store 원천 최신 기록일(2026-09-14)의 연도는 부분 연도라 제외
# ---------------------------------------------------------------------------

_PARTIAL_2026 = [
    _m("R1", "cafe", 1.0, 99, 1.0, year=2026),  # 부분 연도 — 단독 풀이면 0.5 백분위
    _m("R2", "bakery", 1.0, 99, 1.0, year=2026),
]


def _with_partial_year() -> RiskInteractor:
    return RiskInteractor(
        repository=FakeRepository(_CAFE_POOL + _BAKERY_POOL + _PARTIAL_2026),
        store_stats=FakeStoreStats(latest=date(2026, 9, 14)),
    )


def test_default_year_skips_partial_current_year():
    interactor = _with_partial_year()
    assert [d.region_code for d in interactor.rank_by_region("cafe", year=None)] == ["R3", "R2", "R1"]
    assert interactor.score_for("R2", "cafe", year=None).score == 50.0  # 2025 풀 기준


def test_explicit_year_still_returns_partial_year():
    ranking = _with_partial_year().rank_by_region("cafe", year=2026)
    assert [d.region_code for d in ranking] == ["R1"]


def test_rank_by_industry_default_skips_partial_current_year():
    ranking = _with_partial_year().rank_by_industry("R2", year=None)
    assert [(d.industry_id, d.score) for d in ranking] == [("cafe", 50.0), ("bakery", 25.0)]
