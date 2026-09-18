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


# 전환계획 §4-1 — 응답이 자금 구성 4수치를 함께 실어야 한다.
_PLAN_REVISED = {
    "deposit": 20_000_000, "key_money": 0, "interior_cost": 20_000_000, "equipment_cost": 10_000_000,
    "monthly_rent": 1_000_000, "monthly_payroll": 900_000, "monthly_insurance": 100_000,
    "cost_ratio": 0.57, "fee_ratio": 0.03,
    "equity": 40_000_000, "desired_loan": 25_000_000, "loan_rate": 0.048,
    "expected_monthly_revenue": 8_000_000,
}


def test_response_carries_funding_breakdown():
    """§7-2 — 부족액 0원이어도 조달 필요 2,260만이 응답에 남는다."""
    body = TestClient(app).post("/finance/simulate", json=_PLAN_REVISED).json()
    assert body["reserve_months"] == 6
    assert body["operating_reserve"] == 12_600_000
    assert body["total_required_funds"] == 62_600_000
    assert body["external_funding_need"] == 22_600_000
    assert body["funding_gap"] == 0
