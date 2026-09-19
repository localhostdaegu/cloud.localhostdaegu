"""최신 분기 임대 시세 조회 — Interactor(Fake 포트)·Router 계약·전체 배선(실 DB).

main.py 배선 전이라 라우터를 로컬 FastAPI 앱에 붙여 검증한다.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete, insert

from apps.rent.adapter.inbound.api.v1.rent_price_router import router
from apps.rent.adapter.outbound.orms.rent_price_orm import RentPriceOrm
from apps.rent.app.dtos.rent_price_dto import RentPriceDto
from apps.rent.app.ports.input.rent_price_use_case import RentPriceUseCase
from apps.rent.app.ports.output.rent_price_port import RentPriceRepositoryPort
from apps.rent.app.use_cases.rent_price_interactor import RentPriceInteractor
from apps.rent.dependencies.rent_price_dependencies import get_rent_price_use_case
from apps.rent.domain.entities.rent_price_entity import RentPrice
from core.matrix.grid_oracle_database_manager import session_scope

_TEST_CLS_PREFIX = "99100"  # 실데이터·test_rent_price_ingest(990001)와 충돌하지 않는 시험용 CLS_ID


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def _price(
    region_name: str,
    region_level: int,
    building_type: str,
    period: str,
    rent: float | None = 20.0,
    vacancy: float | None = 10.0,
) -> RentPrice:
    return RentPrice(
        id=f"{building_type}:{region_name}:{period}",
        building_type=building_type,
        region_name=region_name,
        region_level=region_level,
        period=period,
        rent_per_m2=rent,
        vacancy_rate=vacancy,
    )


# --- Interactor (Fake 포트) ---


class FakeRentPriceRepository(RentPriceRepositoryPort):
    def __init__(self, prices: list[RentPrice]) -> None:
        self._prices = prices

    def find_latest(self) -> list[RentPrice]:
        return self._prices


def test_latest_sorts_by_level_then_region_then_building_type():
    interactor = RentPriceInteractor(
        repository=FakeRentPriceRepository(
            [
                _price("칠곡", 2, "small", "2026Q2"),
                _price("계명대", 2, "small", "2026Q2"),
                _price("계명대", 2, "medium_large", "2026Q2"),
                _price("대구", 1, "small", "2026Q2"),
            ]
        )
    )

    keys = [(d.region_level, d.region_name, d.building_type) for d in interactor.latest()]

    assert keys == [
        (1, "대구", "small"),
        (2, "계명대", "medium_large"),
        (2, "계명대", "small"),
        (2, "칠곡", "small"),
    ]


def test_latest_keeps_missing_metric_as_none():
    interactor = RentPriceInteractor(
        repository=FakeRentPriceRepository([_price("대구", 1, "small", "2026Q2", rent=None, vacancy=None)])
    )
    assert interactor.latest() == [
        RentPriceDto(
            region_name="대구",
            region_level=1,
            building_type="small",
            period="2026Q2",
            rent_per_m2=None,
            vacancy_rate=None,
        )
    ]


def test_latest_returns_empty_list_when_no_rows():
    assert RentPriceInteractor(repository=FakeRentPriceRepository([])).latest() == []


# --- Router 계약 ---


class FakeRentPriceUseCase(RentPriceUseCase):
    def __init__(self, dtos: list[RentPriceDto]) -> None:
        self._dtos = dtos

    def myself(self) -> RentPriceDto:
        return self._dtos[0]

    def latest(self) -> list[RentPriceDto]:
        return self._dtos


def _client(dtos: list[RentPriceDto]) -> TestClient:
    app = _app()
    app.dependency_overrides[get_rent_price_use_case] = lambda: FakeRentPriceUseCase(dtos)
    return TestClient(app)


def test_rents_myself_wiring_returns_200():
    response = TestClient(_app()).get("/rents/myself")
    assert response.status_code == 200
    assert response.json()["region_name"] == "myself"


def test_latest_endpoint_contract_with_null_metric():
    dto = RentPriceDto(
        region_name="동성로",
        region_level=2,
        building_type="medium_large",
        period="2026Q2",
        rent_per_m2=21.7,
        vacancy_rate=None,
    )
    response = _client([dto]).get("/rents/latest")
    assert response.status_code == 200
    assert response.json() == [
        {
            "region_name": "동성로",
            "region_level": 2,
            "building_type": "medium_large",
            "period": "2026Q2",
            "rent_per_m2": 21.7,
            "vacancy_rate": None,
        }
    ]


def test_latest_endpoint_returns_empty_list():
    response = _client([]).get("/rents/latest")
    assert response.status_code == 200
    assert response.json() == []


# --- 전체 배선 (실 DB — conftest의 테스트 DB) ---


def _row(cls_no: int, region_name: str, level: int, building_type: str, period: str, rent, vacancy) -> dict:
    cls_id = f"{_TEST_CLS_PREFIX}{cls_no}"
    return {
        "id": f"{building_type}:{cls_id}:{period}",
        "building_type": building_type,
        "cls_id": cls_id,
        "region_name": region_name,
        "region_path": "대구" if level == 1 else f"대구>{region_name}",
        "region_level": level,
        "district_code": None,
        "period": period,
        "rent_per_m2": rent,
        "vacancy_rate": vacancy,
        "rent_statbl_id": None,
        "vacancy_statbl_id": None,
    }


def _cleanup() -> None:
    with session_scope() as session:
        session.execute(delete(RentPriceOrm).where(RentPriceOrm.cls_id.like(f"{_TEST_CLS_PREFIX}%")))


def test_latest_endpoint_returns_only_most_recent_period_from_db():
    _cleanup()
    try:
        # 9999년 — 테스트 DB에 다른 행이 있어도 항상 최신 분기
        with session_scope() as session:
            session.execute(
                insert(RentPriceOrm),
                [
                    _row(2, "시험상권", 2, "small", "9999Q2", 22.5, None),
                    _row(1, "시험대구", 1, "medium_large", "9999Q2", 21.7, 18.9),
                    _row(2, "시험상권", 2, "medium_large", "9999Q2", None, 14.2),
                    _row(1, "시험대구", 1, "medium_large", "9999Q1", 11.1, 11.1),
                    _row(2, "시험상권", 2, "small", "9999Q1", 12.2, 12.2),
                ],
            )

        response = TestClient(_app()).get("/rents/latest")

        assert response.status_code == 200
        assert response.json() == [
            {
                "region_name": "시험대구",
                "region_level": 1,
                "building_type": "medium_large",
                "period": "9999Q2",
                "rent_per_m2": 21.7,
                "vacancy_rate": 18.9,
            },
            {
                "region_name": "시험상권",
                "region_level": 2,
                "building_type": "medium_large",
                "period": "9999Q2",
                "rent_per_m2": None,
                "vacancy_rate": 14.2,
            },
            {
                "region_name": "시험상권",
                "region_level": 2,
                "building_type": "small",
                "period": "9999Q2",
                "rent_per_m2": 22.5,
                "vacancy_rate": None,
            },
        ]
    finally:
        _cleanup()


def test_latest_endpoint_returns_empty_list_from_empty_table():
    _cleanup()
    with session_scope() as session:
        # 테스트 DB는 rent_price를 적재하지 않는다(conftest) — 전제가 깨지면 여기서 드러난다
        assert session.query(RentPriceOrm).count() == 0

    response = TestClient(_app()).get("/rents/latest")

    assert response.status_code == 200
    assert response.json() == []
