"""consultation DB 왕복 — POST /consultation → PUT .../plans/current → GET /consultation/{id}.

**이 파일은 alembic 리비전(작업 D)이 올라오기 전까지 실패한다** — consultation_* 4테이블이
아직 테스트 DB에 없다. 순수 로직 테스트(test_consultation_interactor·_mappers)는 D와 무관하게 통과한다.
"""

from fastapi.testclient import TestClient

from main import app

_PLAN_INPUT = {
    "deposit": 30_000_000,
    "key_money": 10_000_000,
    "interior_cost": 40_000_000,
    "equipment_cost": 20_000_000,
    "monthly_rent": 1_800_000,
    "monthly_payroll": 3_000_000,
    "monthly_insurance": 200_000,
    "cost_ratio": 0.35,
    "fee_ratio": 0.05,
    "equity": 60_000_000,
    "desired_loan": 50_000_000,
    "loan_rate": 0.045,
    "expected_monthly_revenue": 18_000_000,
}


def _create_session(client: TestClient, **profile) -> str:
    response = client.post("/consultation", json=profile)
    assert response.status_code == 201, response.text
    return response.json()["session_id"]


def test_create_save_plan_and_get_round_trip():
    client = TestClient(app)
    session_id = _create_session(client, region_code="2711059500", industry_id="cafe")

    saved = client.put(f"/consultation/{session_id}/plans/current", json=_PLAN_INPUT)
    assert saved.status_code == 200, saved.text

    detail = client.get(f"/consultation/{session_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["session"]["region_code"] == "2711059500"
    assert len(body["plans"]) == 1
    assert body["plans"][0]["plan_kind"] == "current"
    assert body["plans"][0]["monthly_rent"] == 1_800_000


def test_saving_same_plan_kind_twice_updates_without_unique_violation():
    client = TestClient(app)
    session_id = _create_session(client)

    first = client.put(f"/consultation/{session_id}/plans/current", json=_PLAN_INPUT)
    second = client.put(
        f"/consultation/{session_id}/plans/current",
        json={**_PLAN_INPUT, "monthly_rent": 2_500_000},
    )

    assert second.status_code == 200, second.text
    assert second.json()["plan_id"] == first.json()["plan_id"]
    plans = client.get(f"/consultation/{session_id}").json()["plans"]
    assert len(plans) == 1
    assert plans[0]["monthly_rent"] == 2_500_000


def test_baseline_and_current_coexist():
    client = TestClient(app)
    session_id = _create_session(client)

    client.put(f"/consultation/{session_id}/plans/baseline", json=_PLAN_INPUT)
    client.put(f"/consultation/{session_id}/plans/current", json=_PLAN_INPUT)

    kinds = [p["plan_kind"] for p in client.get(f"/consultation/{session_id}").json()["plans"]]
    assert kinds == ["baseline", "current"]


def test_unknown_profile_survives_db_round_trip_as_null():
    """인수 기준 — business_registered·owner_age 미입력이 False·0이 아니라 None으로 왕복한다."""
    client = TestClient(app)
    session_id = _create_session(client)

    session = client.get(f"/consultation/{session_id}").json()["session"]

    assert session["business_registered"] is None
    assert session["owner_age"] is None
    assert session["business_age_months"] is None


def test_invalid_plan_kind_returns_400():
    client = TestClient(app)
    session_id = _create_session(client)

    response = client.put(f"/consultation/{session_id}/plans/selected", json=_PLAN_INPUT)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_PLAN_KIND"


def test_unknown_session_returns_404():
    client = TestClient(app)

    assert client.get("/consultation/0123456789abcdef").status_code == 404
    put = client.put("/consultation/0123456789abcdef/plans/current", json=_PLAN_INPUT)
    assert put.status_code == 404
    assert put.json()["error"]["code"] == "SESSION_NOT_FOUND"
