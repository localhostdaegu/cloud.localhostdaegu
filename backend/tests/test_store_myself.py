"""store BC 배선 검증 — GET /stores/myself (CLAUDE.md §12)."""

from fastapi.testclient import TestClient

from main import app


def test_store_myself_wiring_returns_200():
    client = TestClient(app)
    response = client.get("/stores/myself")
    assert response.status_code == 200
    body = response.json()
    assert body["store_id"] == "myself"
    assert body["name"]


def test_store_myself_uses_daegu_sample():
    # 서울 포팅 잔재(11110, 37.5/127.0) 제거 — 대구 구·군 코드와 좌표 범위 안의 표본
    from core.matrix.grid_region_config import DISTRICTS, LAT_RANGE, LNG_RANGE

    body = TestClient(app).get("/stores/myself").json()
    assert body["district_code"] in DISTRICTS
    assert LAT_RANGE[0] < body["lat"] < LAT_RANGE[1]
    assert LNG_RANGE[0] < body["lng"] < LNG_RANGE[1]
