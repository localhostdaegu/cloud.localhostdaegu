"""consultation BC 배선 검증 — GET /consultation/myself (CLAUDE.md §12 라우터 최초 검증 규칙)."""

from fastapi.testclient import TestClient

from main import app


def test_consultation_myself_wiring_returns_200():
    client = TestClient(app)
    response = client.get("/consultation/myself")
    assert response.status_code == 200
    body = response.json()
    assert body["session"]["session_id"] == "myself"
    assert body["plans"] == []
    assert body["notes"] == []


def test_consultation_myself_keeps_unknown_profile_as_null():
    """배선 응답에서도 미입력 프로필은 null이다 — 0·false로 채우지 않는다 (전환계획 §4-2)."""
    response = TestClient(app).get("/consultation/myself")
    session = response.json()["session"]
    assert session["business_registered"] is None
    assert session["owner_age"] is None
    assert session["business_age_months"] is None
