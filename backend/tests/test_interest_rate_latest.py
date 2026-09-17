"""최신 금리 조회 — 도메인 비율 환산·Interactor(Fake 포트)·Router 계약·Repository(실 DB)."""

from fastapi.testclient import TestClient
from sqlalchemy import delete

from apps.shock.adapter.inbound.cli.load_interest_rate import upsert_rates
from apps.shock.adapter.outbound.orms.interest_rate_orm import InterestRateOrm
from apps.shock.adapter.outbound.repositories.interest_rate_repository import (
    SqlAlchemyInterestRateRepository,
)
from apps.shock.app.dtos.interest_rate_dto import InterestRateDto
from apps.shock.app.ports.input.interest_rate_use_case import InterestRateUseCase
from apps.shock.app.ports.output.interest_rate_port import InterestRateRepositoryPort
from apps.shock.app.use_cases.interest_rate_interactor import InterestRateInteractor
from apps.shock.dependencies.interest_rate_dependencies import get_interest_rate_use_case
from apps.shock.domain.entities.interest_rate_entity import InterestRate
from core.matrix.grid_oracle_database_manager import session_scope
from main import app

_TEST_PREFIX = "test-latest:"


def _rate(rate_type: str, period: str, rate: float) -> InterestRate:
    return InterestRate(
        id=f"{_TEST_PREFIX}{rate_type}:{period}",
        rate_type=rate_type,
        period=period,
        rate=rate,
        unit="연리%",
        stat_code="121Y006",
        item_code="BECBLA0202",
    )


# --- 도메인 ---


def test_ratio_converts_percent_without_float_noise():
    assert _rate("loan_sme", "202607", 4.22).ratio == 0.0422  # 4.22/100 = 0.042199999… 방지


# --- Interactor (Fake 포트) ---


class FakeInterestRateRepository(InterestRateRepositoryPort):
    def __init__(self, rates: list[InterestRate]) -> None:
        self._rates = rates

    def find_latest(self, rate_type: str) -> InterestRate | None:
        matching = [r for r in self._rates if r.rate_type == rate_type]
        return max(matching, key=lambda r: r.period, default=None)


def test_latest_returns_percent_and_ratio_for_most_recent_period():
    interactor = InterestRateInteractor(
        repository=FakeInterestRateRepository(
            [_rate("loan_sme", "202606", 4.38), _rate("loan_sme", "202607", 4.22), _rate("base", "202608", 2.5)]
        )
    )

    dto = interactor.latest("loan_sme")

    assert dto == InterestRateDto(rate_type="loan_sme", period="202607", value_percent=4.22, value_ratio=0.0422)


def test_latest_returns_none_when_rate_type_has_no_rows():
    interactor = InterestRateInteractor(repository=FakeInterestRateRepository([]))
    assert interactor.latest("loan_sme") is None


# --- Router 계약 ---


class FakeInterestRateUseCase(InterestRateUseCase):
    def myself(self) -> InterestRateDto:
        return InterestRateDto(rate_type="myself", period="202609", value_percent=1.0, value_ratio=0.01)

    def latest(self, rate_type: str) -> InterestRateDto | None:
        if rate_type != "loan_sme":
            return None
        return InterestRateDto(rate_type="loan_sme", period="202607", value_percent=4.22, value_ratio=0.0422)


def _client() -> TestClient:
    app.dependency_overrides[get_interest_rate_use_case] = FakeInterestRateUseCase
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_rates_myself_wiring_returns_200():
    response = TestClient(app).get("/shocks/rates/myself")
    assert response.status_code == 200
    assert response.json()["rate_type"] == "myself"


def test_latest_rate_endpoint_contract():
    response = _client().get("/shocks/rates/latest", params={"rate_type": "loan_sme"})
    assert response.status_code == 200
    assert response.json() == {
        "rate_type": "loan_sme",
        "period": "202607",
        "value_percent": 4.22,
        "value_ratio": 0.0422,
    }


def test_latest_rate_endpoint_404_with_error_body():
    response = _client().get("/shocks/rates/latest", params={"rate_type": "unknown"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RATE_NOT_FOUND"


# --- Repository (실 DB) ---


def _cleanup() -> None:
    with session_scope() as session:
        session.execute(delete(InterestRateOrm).where(InterestRateOrm.id.like(f"{_TEST_PREFIX}%")))


def test_repository_find_latest_picks_max_period_within_rate_type():
    _cleanup()
    try:
        upsert_rates(
            [
                _rate("test_loan", "202512", 4.9),
                _rate("test_loan", "202601", 4.7),
                _rate("test_other", "202609", 9.9),
            ]
        )
        repository = SqlAlchemyInterestRateRepository()

        latest = repository.find_latest("test_loan")

        assert latest is not None
        assert (latest.rate_type, latest.period, latest.rate) == ("test_loan", "202601", 4.7)
        assert repository.find_latest("test_missing") is None
    finally:
        _cleanup()
