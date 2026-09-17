"""POST /finance/simulate 입력 검증 — 0 나눗셈(500)·음수 BEP 대신 422."""

import pytest
from fastapi.testclient import TestClient

from main import app

_VALID = {
    "deposit": 20_000_000, "key_money": 0, "interior_cost": 30_000_000, "equipment_cost": 10_000_000,
    "monthly_rent": 2_000_000, "monthly_payroll": 6_000_000, "monthly_insurance": 500_000,
    "cost_ratio": 0.40, "fee_ratio": 0.03,
    "equity": 50_000_000, "desired_loan": 20_000_000, "loan_rate": 0.045,
    "expected_monthly_revenue": 20_000_000,
}


def _post(**overrides):
    return TestClient(app).post("/finance/simulate", json={**_VALID, **overrides})


def test_valid_input_returns_200():
    assert _post().status_code == 200


@pytest.mark.parametrize(
    "overrides",
    [
        {"cost_ratio": 0.97, "fee_ratio": 0.03},  # 변동비율 = 1 → BEP 0 나눗셈
        {"cost_ratio": 0.9, "fee_ratio": 0.2},  # 변동비율 > 1 → 음수 BEP
        {"cost_ratio": 1.0, "fee_ratio": 0.0},
        {"fee_ratio": -0.01},
        {"loan_rate": -0.01},
        {"deposit": -1},
        {"expected_monthly_revenue": -1},
    ],
)
def test_invalid_input_returns_422(overrides):
    assert _post(**overrides).status_code == 422
