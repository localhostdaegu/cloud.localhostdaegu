"""POST /intent — 실제 composition(get_dongs_gus → 테스트 DB 시드 마스터) 통과 E2E (DI override 없음)."""

import pytest
from fastapi.testclient import TestClient

from apps.intent.adapter.inbound.api.v1.intent_router import _load_dongs_gus
from main import app


@pytest.fixture()
def client() -> TestClient:
    _load_dongs_gus.cache_clear()  # 다른 테스트가 채운 캐시 대신 이 세션의 테스트 DB 사전
    yield TestClient(app)
    _load_dongs_gus.cache_clear()


def test_dalseo_gu_is_not_seo_gu_and_compound_budget(client: TestClient):
    response = client.post("/intent", json={"text": "달서구에서 카페 1억 5천만원"})

    assert response.status_code == 200
    body = response.json()
    assert body["intent_type"] == "A"
    assert body["district_code"] == "27290"  # 서구(27170) 아님
    assert body["industry_id"] == "cafe"
    assert body["budget_krw"] == 150_000_000
    assert body["missing"] == []


def test_landmark_resolves_to_seeded_numbered_dong(client: TestClient):
    response = client.post("/intent", json={"text": "동대구역 근처 2층 카페 5천만원"})

    body = response.json()
    assert body["district_code"] == "27140"
    assert body["region_name"] == "신암4동"
    assert body["budget_krw"] == 50_000_000  # '2층' 무시


def test_seeded_dong_name_matches_without_landmark(client: TestClient):
    body = client.post("/intent", json={"text": "산격3동에서 미용실"}).json()

    assert body["district_code"] == "27230"
    assert body["region_name"] == "산격3동"
    assert body["industry_id"] == "hair_salon"
    assert body["missing"] == ["budget"]


def test_spoken_place_comes_back_as_a_dong_code_so_the_map_can_select_it(client: TestClient):
    """2026-09-19 페르소나 테스트 — '서문시장 근처'라 말한 고객이 구 중심의 다른 동을 골랐다."""
    body = client.post("/intent", json={"text": "서문시장 근처 카페, 예산 5천"}).json()
    assert (body["region_name"], body["region_code"]) == ("대신동", "2711059500")


def test_district_only_has_no_dong_code(client: TestClient):
    assert client.post("/intent", json={"text": "수성구에 음식점"}).json()["region_code"] is None
