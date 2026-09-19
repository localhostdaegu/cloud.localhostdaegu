"""지역 지표 조회 — 최신 기간 선별(순수 함수)·Interactor(Fake 포트)·Router 계약·Repository(테스트 DB)."""

from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete

from apps.dataset.adapter.outbound.orms.external_dataset_orm import ExternalDatasetOrm
from apps.dataset.adapter.outbound.repositories.external_dataset_repository import (
    SqlAlchemyExternalDatasetRepository,
)
from apps.dataset.domain.entities.external_dataset_entity import ExternalDataset
from apps.indicator.adapter.inbound.api.v1.regional_indicator_router import router
from apps.indicator.adapter.outbound.orms.regional_indicator_orm import RegionalIndicatorOrm
from apps.indicator.adapter.outbound.repositories.regional_indicator_repository import (
    SqlAlchemyRegionalIndicatorRepository,
)
from apps.indicator.app.dtos.regional_indicator_dto import RegionalIndicatorDto
from apps.indicator.app.ports.output.regional_indicator_port import (
    RegionalIndicatorRepositoryPort,
)
from apps.indicator.app.use_cases.regional_indicator_interactor import (
    RegionalIndicatorInteractor,
    latest_per_key,
)
from apps.indicator.domain.entities.regional_indicator_entity import RegionalIndicator
from core.matrix.grid_oracle_database_manager import session_scope

_REGION = "2711051700"  # 중구 동인동 (시드 마스터)
_OTHER_REGION = "2711059500"  # 중구 대신동 (시드 마스터)
_EMPTY_REGION = "0000000000"  # 어떤 행도 없는 코드
_DATASET_ID = "test-indicator-read"


def _indicator(
    key: str, period: str, value: float, breakdown: str | None = None, region: str = _REGION, unit: str = "명"
) -> RegionalIndicator:
    return RegionalIndicator(
        dataset_id=_DATASET_ID,
        region_code=region,
        period=period,
        indicator_key=key,
        breakdown=breakdown,
        value=value,
        unit=unit,
    )


# 키마다 최신 기간이 다르다 — 시장 수는 202512 한 번, 승차는 월별(슬라이스 포함)
_ROWS = [
    _indicator("test_subway_daily_avg", "202606", 10.0, "time_10_14"),
    _indicator("test_subway_daily_avg", "202606", 20.0, "time_05_10"),
    _indicator("test_subway_daily_avg", "202605", 99.0, "time_05_10"),
    _indicator("test_subway_monthly", "202607", 300.0),
    _indicator("test_subway_monthly", "202606", 200.0),
    _indicator("test_market_count", "202512", 3.0, "", unit="곳"),  # 빈 문자열 슬라이스 → null
]

_EXPECTED = [
    RegionalIndicatorDto("test_market_count", None, "202512", 3.0, "곳"),
    RegionalIndicatorDto("test_subway_daily_avg", "time_05_10", "202606", 20.0, "명"),
    RegionalIndicatorDto("test_subway_daily_avg", "time_10_14", "202606", 10.0, "명"),
    RegionalIndicatorDto("test_subway_monthly", None, "202607", 300.0, "명"),
]


# --- 최신 기간 선별 (순수 함수) ---


def test_latest_per_key_keeps_each_keys_own_latest_period_with_all_breakdowns():
    assert latest_per_key(_ROWS) == _EXPECTED


def test_latest_per_key_sorts_null_breakdown_before_named_ones():
    rows = [_indicator("test_key", "202606", 2.0, "time_05_10"), _indicator("test_key", "202606", 1.0)]
    assert [dto.breakdown for dto in latest_per_key(rows)] == [None, "time_05_10"]


def test_latest_per_key_of_nothing_is_empty():
    assert latest_per_key([]) == []


# --- Interactor (Fake 포트) ---


class FakeRegionalIndicatorRepository(RegionalIndicatorRepositoryPort):
    def __init__(self, rows: list[RegionalIndicator]) -> None:
        self._rows = rows

    def upsert(self, indicators: list[RegionalIndicator]) -> int:
        raise NotImplementedError

    def myself(self) -> RegionalIndicator:
        return _indicator("myself", "202609", 1.0)

    def find_by_region(self, region_code: str) -> list[RegionalIndicator]:
        return [row for row in self._rows if row.region_code == region_code]


def test_list_latest_only_sees_requested_region():
    rows = [*_ROWS, _indicator("test_subway_monthly", "202612", 1.0, region=_OTHER_REGION)]
    interactor = RegionalIndicatorInteractor(repository=FakeRegionalIndicatorRepository(rows))

    assert interactor.list_latest(_REGION) == _EXPECTED
    assert interactor.list_latest(_EMPTY_REGION) == []


# --- Router 계약 (테스트 DB) ---


@pytest.fixture
def loaded_rows():
    SqlAlchemyExternalDatasetRepository().upsert(
        [
            ExternalDataset(
                dataset_id=_DATASET_ID,
                name="지역 지표 조회 테스트",
                provider="대구교통공사",
                source_channel="open_api",
                period_start="202512",
                period_end="202612",
                aggregation_note="테스트",
                restriction_note="테스트",
                export_approved_on=date(2026, 9, 19),
                approval_ref=None,
                source_url=None,
                catalog_page=None,
            )
        ]
    )
    SqlAlchemyRegionalIndicatorRepository().upsert(
        [*_ROWS, _indicator("test_subway_monthly", "202612", 1.0, region=_OTHER_REGION)]
    )
    yield
    with session_scope() as session:
        session.execute(delete(RegionalIndicatorOrm).where(RegionalIndicatorOrm.dataset_id == _DATASET_ID))
        session.execute(delete(ExternalDatasetOrm).where(ExternalDatasetOrm.dataset_id == _DATASET_ID))


def _client() -> TestClient:
    app = FastAPI()  # main.py 배선과 무관하게 라우터만 검증한다
    app.include_router(router)
    return TestClient(app)


def test_indicators_myself_wiring_returns_200():
    response = _client().get("/indicators/myself")
    assert response.status_code == 200
    assert response.json()["indicator_key"] == "myself"


def test_indicators_endpoint_contract(loaded_rows):
    response = _client().get("/indicators", params={"region_code": _REGION})
    assert response.status_code == 200
    assert response.json() == [
        {"indicator_key": "test_market_count", "breakdown": None, "period": "202512", "value": 3.0, "unit": "곳"},
        {
            "indicator_key": "test_subway_daily_avg",
            "breakdown": "time_05_10",
            "period": "202606",
            "value": 20.0,
            "unit": "명",
        },
        {
            "indicator_key": "test_subway_daily_avg",
            "breakdown": "time_10_14",
            "period": "202606",
            "value": 10.0,
            "unit": "명",
        },
        {"indicator_key": "test_subway_monthly", "breakdown": None, "period": "202607", "value": 300.0, "unit": "명"},
    ]


def test_indicators_endpoint_returns_empty_list_for_region_without_rows(loaded_rows):
    response = _client().get("/indicators", params={"region_code": _EMPTY_REGION})
    assert response.status_code == 200
    assert response.json() == []


def test_indicators_endpoint_requires_region_code():
    assert _client().get("/indicators").status_code == 422
