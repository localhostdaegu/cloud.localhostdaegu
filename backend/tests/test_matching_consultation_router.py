"""GET /matching/consultation — §5-2 계약. 상품 로더를 합성 데이터로 대체한다."""

from fastapi.testclient import TestClient

from apps.matching.adapter.inbound.api.v1 import matching_router
from main import app

_PRODUCT = {
    "product_id": "test-only", "provider": "테스트 은행", "provider_type": "bank",
    "product_name": "합성 테스트 상품", "target": "테스트", "region": "대구", "category": None,
    "business_age_min": 0, "business_age_max": None, "owner_age_max": None,
    "loan_limit": 10_000_000, "interest_rate": None, "guarantee_fee": None,
    "url": "https://example.org", "source_url": "https://example.org",
    "consultation_metadata": {
        "bank_connection": "direct", "bank_connection_source_url": "https://example.org/notice",
        "business_registration_required": True,
        "prerequisites": ["소진공 확인서 발급"], "application_steps": ["영업점 방문"],
        "documents": ["사업자등록증"], "verified_at": "2026-09-18",
    },
}


def _get(monkeypatch, products, query: str):
    monkeypatch.setattr(matching_router, "load_consultation_products", lambda: products)
    return TestClient(app).get(f"/matching/consultation?{query}")


def test_returns_candidate_with_metadata_and_reason(monkeypatch):
    response = _get(monkeypatch, [_PRODUCT], "external_funding_need=2000000&category=cafe&business_registered=true")

    assert response.status_code == 200
    (candidate,) = response.json()
    assert candidate["product"]["product_id"] == "test-only"
    assert candidate["metadata"]["bank_connection"] == "direct"
    assert candidate["metadata"]["prerequisites"] == ["소진공 확인서 발급"]
    assert candidate["status"] == "prerequisites_needed"
    assert candidate["reason"]


def test_unverified_products_return_empty_list(monkeypatch):
    product = {**_PRODUCT, "consultation_metadata": {**_PRODUCT["consultation_metadata"], "bank_connection": "unverified"}}

    response = _get(monkeypatch, [product], "external_funding_need=2000000&category=cafe")

    assert response.status_code == 200
    assert response.json() == []


def test_optional_inputs_can_be_omitted(monkeypatch):
    response = _get(monkeypatch, [_PRODUCT], "external_funding_need=0&category=")

    assert response.status_code == 200


def test_negative_amount_is_rejected(monkeypatch):
    assert _get(monkeypatch, [_PRODUCT], "external_funding_need=-1&category=cafe").status_code == 422


def test_reference_products_are_opt_in(monkeypatch):
    """§5-2 — 참고자료는 명시적으로 요청할 때만 함께 준다."""
    product = {
        **_PRODUCT,
        "consultation_metadata": {**_PRODUCT["consultation_metadata"], "bank_connection": "unverified"},
    }

    without = _get(monkeypatch, [product], "external_funding_need=2000000&category=cafe")
    assert without.json() == []

    with_reference = _get(
        monkeypatch, [product], "external_funding_need=2000000&category=cafe&include_unverified=true"
    )
    (candidate,) = with_reference.json()
    assert candidate["metadata"]["bank_connection"] == "unverified"
