"""metric 조회 검증 — GET /metrics 값 추출·None 제외·404 에러 바디 (프론트엔드 계약)."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from apps.metric.app.dtos.region_industry_metric_dto import (
    MetricValueDto,
    RegionIndustryMetricDto,
    YearlyStoreStat,
)
from apps.metric.app.ports.input.region_industry_metric_use_case import (
    RegionIndustryMetricUseCase,
)
from apps.metric.app.ports.output.region_industry_metric_port import (
    IndustryCatalogPort,
    RegionIndustryMetricRepositoryPort,
    StoreStatsPort,
)
from apps.metric.app.use_cases.region_industry_metric_interactor import (
    RegionIndustryMetricInteractor,
)
from apps.metric.dependencies.region_industry_metric_dependencies import (
    get_region_industry_metric_use_case,
)
from apps.metric.domain.entities.region_industry_metric_entity import (
    RegionIndustryMetric,
)
from apps.metric.domain.errors import IndustryNotFoundError, MetricNotFoundError
from apps.metric.domain.reporting_year import last_complete_year
from main import app


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
        return next(
            (
                m
                for m in self._metrics
                if (m.region_code, m.industry_id, m.year)
                == (region_code, industry_id, year)
            ),
            None,
        )

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
        raise NotImplementedError

    def list_latest_by_region(
        self, region_code: str, until_year: int | None = None
    ) -> list[RegionIndustryMetric]:
        raise NotImplementedError


class FakeStoreStats(StoreStatsPort):
    def __init__(self, latest: date | None = None) -> None:
        self._latest = latest

    def yearly_stats(self, years: list[int]) -> list[YearlyStoreStat]:
        return []

    def latest_record_date(self) -> date | None:
        return self._latest


class FakeIndustryCatalog(IndustryCatalogPort):
    def exists(self, industry_id: str) -> bool:
        return industry_id == "cafe"


def _metric(
    region_code: str, closure_rate: float | None, year: int = 2025
) -> RegionIndustryMetric:
    return RegionIndustryMetric(
        region_code=region_code,
        industry_id="cafe",
        year=year,
        store_count=10,
        open_count=1,
        close_count=1,
        closure_rate=closure_rate,
        growth_rate=None,
    )


def _interactor(
    metrics: list[RegionIndustryMetric], latest: date | None = None
) -> RegionIndustryMetricInteractor:
    return RegionIndustryMetricInteractor(
        repository=FakeRepository(metrics),
        store_stats=FakeStoreStats(latest),
        industry_catalog=FakeIndustryCatalog(),
    )


def test_list_metric_values_excludes_none_rows():
    interactor = _interactor([_metric("1168064000", 0.1), _metric("1111051500", None)])
    values = interactor.list_metric_values("cafe", "closure_rate", 2025)
    assert values == [MetricValueDto(region_code="1168064000", value=0.1)]


def test_list_metric_values_rejects_unknown_metric():
    with pytest.raises(MetricNotFoundError):
        _interactor([]).list_metric_values("cafe", "sales_rate", 2025)


def test_list_metric_values_rejects_unknown_industry():
    with pytest.raises(IndustryNotFoundError):
        _interactor([]).list_metric_values("bakery", "closure_rate", 2025)


def test_find_returns_dto_or_none():
    interactor = _interactor([_metric("1168064000", 0.1)])
    dto = interactor.find("1168064000", "cafe", 2025)
    assert isinstance(dto, RegionIndustryMetricDto)
    assert dto.closure_rate == 0.1
    assert interactor.find("1111051500", "cafe", 2025) is None


def test_last_complete_year_excludes_year_of_latest_record():
    assert last_complete_year(date(2026, 9, 14)) == 2025
    assert last_complete_year(date(2026, 1, 1)) == 2025


def test_find_without_year_uses_last_complete_year():
    """사이드패널 카드 — 부분 연도(2026) 대신 원천 최신 기록일 기준 마지막 완결 연도(2025)."""
    interactor = _interactor(
        [_metric("2711059500", 0.1, year=2025), _metric("2711059500", 0.9, year=2026)],
        latest=date(2026, 9, 14),
    )
    assert interactor.find("2711059500", "cafe", None).year == 2025
    assert interactor.find("2711059500", "cafe", 2026).year == 2026  # 명시 연도는 그대로


def test_find_without_year_none_when_no_metrics():
    assert _interactor([], latest=date(2026, 9, 14)).find("2711059500", "cafe", None) is None


def test_data_years_runs_through_latest_record_year():
    assert _interactor([], latest=date(2026, 9, 14)).data_years(2019) == list(range(2019, 2027))
    assert _interactor([], latest=None).data_years(2019) == []


def _client(metrics: list[RegionIndustryMetric]) -> TestClient:
    fake: RegionIndustryMetricUseCase = _interactor(metrics)
    app.dependency_overrides[get_region_industry_metric_use_case] = lambda: fake
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_metrics_endpoint_returns_region_value_rows():
    client = _client([_metric("1168064000", 0.1), _metric("1111051500", None)])
    response = client.get("/metrics?industry=cafe&metric=closure_rate&year=2025")
    assert response.status_code == 200
    assert response.json() == [{"region_code": "1168064000", "value": 0.1}]


def test_metrics_endpoint_404_on_unknown_metric():
    client = _client([])
    response = client.get("/metrics?industry=cafe&metric=sales_rate&year=2025")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "METRIC_NOT_FOUND"
    assert body["error"]["message"]


def test_metrics_endpoint_404_on_unknown_industry():
    client = _client([])
    response = client.get("/metrics?industry=bakery&metric=closure_rate&year=2025")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "INDUSTRY_NOT_FOUND"
    assert body["error"]["message"]
