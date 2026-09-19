"""행정동 인구 요약 — 도메인 연령대 합산·Interactor(Fake 포트)·Router 계약·Repository(실 DB)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete

from apps.master.adapter.inbound.api.v1.population_stat_router import router
from apps.master.adapter.outbound.orms.population_stat_orm import PopulationStatOrm
from apps.master.adapter.outbound.repositories.population_stat_repository import (
    SqlAlchemyPopulationStatRepository,
)
from apps.master.app.dtos.population_stat_dto import PopulationAgeBandDto, PopulationSummaryDto
from apps.master.app.ports.input.population_stat_use_case import PopulationStatUseCase
from apps.master.app.ports.output.population_stat_port import PopulationStatRepositoryPort
from apps.master.app.use_cases.population_stat_interactor import PopulationStatInteractor
from apps.master.dependencies.population_stat_dependencies import get_population_stat_use_case
from apps.master.domain.entities.population_stat_entity import (
    PopulationStat,
    select_base_period,
    sum_by_band,
)
from core.matrix.grid_oracle_database_manager import session_scope

_REGION = "2711059500"  # seed_master가 넣는 실제 행정동 (FK 충족)
_TEST_PERIODS = ["999901", "999902", "999903"]  # 실적재 연월(2019~2026)과 겹치지 않는 테스트 전용 연월

# main.py 배선은 별도 — 이 슬라이스 라우터만 얹은 로컬 앱
app = FastAPI()
app.include_router(router)


def _stat(period: str, gender: str, age_from: int, population: int, region_code: str = _REGION) -> PopulationStat:
    return PopulationStat(
        region_code=region_code,
        period=period,
        gender=gender,
        age_from=age_from,
        age_to=None if age_from == 100 else age_from + 4,
        population=population,
    )


# --- 도메인 ---


def test_sum_by_band_adds_both_genders_and_assigns_by_age_from():
    stats = [
        _stat("202606", "M", 0, 1),
        _stat("202606", "F", 15, 2),  # 15~19 → 0~19세 상한 경계
        _stat("202606", "M", 20, 4),  # 20~39세 하한 경계
        _stat("202606", "F", 35, 8),
        _stat("202606", "M", 40, 16),
        _stat("202606", "F", 55, 32),
        _stat("202606", "M", 60, 64),
        _stat("202606", "F", 100, 128),  # 100세 이상 (age_to=None) → 60세 이상
        _stat("202012", "M", 0, 999),  # 다른 연월은 제외
    ]

    assert sum_by_band(stats, "202606") == [3, 12, 48, 192]


def test_select_base_period_prefers_202012_over_earlier_period():
    assert select_base_period(["201912", "202012", "202606"]) == "202012"


def test_select_base_period_falls_back_to_earliest_when_202012_missing():
    assert select_base_period(["202606", "202112", "202312"]) == "202112"


# --- Interactor (Fake 포트) ---


class FakePopulationStatRepository(PopulationStatRepositoryPort):
    def __init__(self, stats: list[PopulationStat]) -> None:
        self._stats = stats

    def find_periods(self, region_code: str) -> list[str]:
        return sorted({s.period for s in self._stats if s.region_code == region_code})

    def find_by_periods(self, region_code: str, periods: list[str]) -> list[PopulationStat]:
        return [s for s in self._stats if s.region_code == region_code and s.period in periods]


def test_summary_compares_latest_with_202012_baseline():
    interactor = PopulationStatInteractor(
        repository=FakePopulationStatRepository(
            [
                _stat("201912", "M", 0, 7777),  # 기준점이 아닌 더 이른 시점 — 무시
                _stat("202012", "M", 0, 10),
                _stat("202012", "F", 0, 11),
                _stat("202012", "F", 100, 5),
                _stat("202512", "M", 0, 8888),  # 최신도 기준도 아닌 중간 시점 — 무시
                _stat("202606", "M", 0, 8),
                _stat("202606", "F", 25, 9),
                _stat("202606", "M", 100, 6),
                _stat("202606", "M", 0, 5555, region_code="2711051700"),  # 다른 행정동 — 무시
            ]
        )
    )

    dto = interactor.summary(_REGION)

    assert dto == PopulationSummaryDto(
        region_code=_REGION,
        latest_period="202606",
        base_period="202012",
        latest_total=23,
        base_total=26,
        age_bands=[
            PopulationAgeBandDto(label="0~19세", latest=8, base=21),
            PopulationAgeBandDto(label="20~39세", latest=9, base=0),
            PopulationAgeBandDto(label="40~59세", latest=0, base=0),
            PopulationAgeBandDto(label="60세 이상", latest=6, base=5),
        ],
    )


def test_summary_falls_back_to_earliest_period_when_202012_missing():
    interactor = PopulationStatInteractor(
        repository=FakePopulationStatRepository(
            [_stat("202112", "M", 40, 3), _stat("202312", "M", 40, 4), _stat("202606", "F", 40, 5)]
        )
    )

    dto = interactor.summary(_REGION)

    assert dto is not None
    assert (dto.latest_period, dto.base_period) == ("202606", "202112")
    assert (dto.latest_total, dto.base_total) == (5, 3)


def test_summary_returns_none_when_region_has_no_rows():
    interactor = PopulationStatInteractor(repository=FakePopulationStatRepository([]))
    assert interactor.summary(_REGION) is None


# --- Router 계약 ---

_SUMMARY = PopulationSummaryDto(
    region_code=_REGION,
    latest_period="202606",
    base_period="202012",
    latest_total=30,
    base_total=40,
    age_bands=[
        PopulationAgeBandDto(label="0~19세", latest=3, base=10),
        PopulationAgeBandDto(label="20~39세", latest=6, base=10),
        PopulationAgeBandDto(label="40~59세", latest=9, base=10),
        PopulationAgeBandDto(label="60세 이상", latest=12, base=10),
    ],
)


class FakePopulationStatUseCase(PopulationStatUseCase):
    def myself(self) -> PopulationSummaryDto:
        return _SUMMARY

    def summary(self, region_code: str) -> PopulationSummaryDto | None:
        return _SUMMARY if region_code == _REGION else None


def _client() -> TestClient:
    app.dependency_overrides[get_population_stat_use_case] = FakePopulationStatUseCase
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_populations_myself_wiring_returns_200():
    response = TestClient(app).get("/populations/myself")  # 오버라이드 없이 실제 배선
    assert response.status_code == 200
    assert response.json()["region_code"] == "myself"


def test_summary_endpoint_contract():
    response = _client().get(f"/populations/{_REGION}/summary")
    assert response.status_code == 200
    assert response.json() == {
        "region_code": _REGION,
        "latest_period": "202606",
        "base_period": "202012",
        "latest_total": 30,
        "base_total": 40,
        "age_bands": [
            {"label": "0~19세", "latest": 3, "base": 10},
            {"label": "20~39세", "latest": 6, "base": 10},
            {"label": "40~59세", "latest": 9, "base": 10},
            {"label": "60세 이상", "latest": 12, "base": 10},
        ],
    }


def test_summary_endpoint_404_with_error_body():
    response = _client().get("/populations/0000000000/summary")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "POPULATION_NOT_FOUND"


def test_summary_endpoint_404_through_real_repository():
    response = TestClient(app).get("/populations/0000000000/summary")  # region에 없는 코드 — 행 0건
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "POPULATION_NOT_FOUND"


# --- Repository (실 DB) ---


def _cleanup() -> None:
    with session_scope() as session:
        session.execute(
            delete(PopulationStatOrm).where(
                PopulationStatOrm.region_code == _REGION,
                PopulationStatOrm.period.in_(_TEST_PERIODS),
            )
        )


def test_repository_returns_periods_and_rows_for_requested_periods_only():
    _cleanup()
    try:
        with session_scope() as session:
            session.add_all(
                [
                    PopulationStatOrm(
                        region_code=_REGION, period="999901", gender="M", age_from=0, age_to=4, population=11
                    ),
                    PopulationStatOrm(
                        region_code=_REGION, period="999902", gender="F", age_from=0, age_to=4, population=22
                    ),
                    PopulationStatOrm(
                        region_code=_REGION, period="999903", gender="F", age_from=100, age_to=None, population=33
                    ),
                ]
            )
        repository = SqlAlchemyPopulationStatRepository()

        periods = repository.find_periods(_REGION)
        stats = repository.find_by_periods(_REGION, ["999901", "999903"])

        assert set(_TEST_PERIODS) <= set(periods)  # 다른 테스트가 실적재한 연월(202606)이 섞여 있을 수 있다
        assert len(periods) == len(set(periods))
        assert sorted((s.period, s.gender, s.age_from, s.age_to, s.population) for s in stats) == [
            ("999901", "M", 0, 4, 11),
            ("999903", "F", 100, None, 33),
        ]
        assert repository.find_periods("0000000000") == []
    finally:
        _cleanup()
