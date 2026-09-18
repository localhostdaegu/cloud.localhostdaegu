"""매칭 로더 DB 우선 / JSON 폴백 — 가짜 리포지토리 주입 (DB 불필요, 스펙 §2-5).

GET /matching 응답 dict 는 기존 15필드 그대로여야 한다. 폴백 경로에서도 동일해야 회귀가 아니다.
"""

import json
from unittest import mock

from apps.matching.adapter.outbound.gateways import manual_product_gateway
from apps.matching.adapter.outbound.gateways.manual_product_gateway import (
    load_all_products_from,
)
from apps.matching.domain.matcher import match_products
from apps.product.app.ports.output.finance_product_port import FinanceProductRepositoryPort
from apps.product.domain.entities.finance_product_entity import FinanceProduct

_DICT_FIELDS = [
    "product_id", "provider", "provider_type", "product_name", "target", "region",
    "business_age_min", "business_age_max", "category", "owner_age_max",
    "loan_limit", "interest_rate", "guarantee_fee", "url", "source_url",
    "district_code",  # 자치구 한정 상품만 값이 있다 — 두 경로가 같은 형태여야 한다
]


class FakeRepository(FinanceProductRepositoryPort):
    def __init__(self, products: list[FinanceProduct] | None = None, error: Exception | None = None):
        self._products = products or []
        self._error = error

    def upsert(self, products: list[FinanceProduct]) -> tuple[int, int]:
        raise NotImplementedError

    def list_all(self) -> list[FinanceProduct]:
        if self._error is not None:
            raise self._error
        return self._products


def _entity(product_id: str, provider_type: str, category: list[str] | None) -> FinanceProduct:
    return FinanceProduct(
        product_id=product_id,
        provider="iM뱅크",
        provider_type=provider_type,
        product_name="테스트 상품",
        target="소상공인",
        region="대구광역시",
        business_age_min=0,
        business_age_max=None,
        owner_age_max=None,
        loan_limit=50_000_000,
        interest_rate=2.5,
        guarantee_fee=0.9,
        url="https://example.test/p",
        source_url="https://example.test/p",
        category=category,
        source_file="imbank_products.json",
    )


def _write_manual_json(tmp_path, products: list[dict]):
    manual_dir = tmp_path / "data" / "manual"
    manual_dir.mkdir(parents=True)
    (manual_dir / "imbank_products.json").write_text(json.dumps(products))
    (manual_dir / "dgsinbo_products.json").write_text(json.dumps([]))
    (manual_dir / "daegu_youth_startup.json").write_text(json.dumps([]))
    return mock.patch.object(manual_product_gateway, "Path", _path_stub(tmp_path))


def _path_stub(tmp_path):
    stub = mock.MagicMock()
    stub.return_value.resolve.return_value.parents.__getitem__.return_value = tmp_path
    return stub


_JSON_PRODUCT = {
    "product_id": "json-1", "provider": "p", "provider_type": "bank", "product_name": "n",
    "target": "t", "region": "대구", "business_age_min": 0, "business_age_max": None,
    "category": None, "owner_age_max": None, "loan_limit": None, "interest_rate": None,
    "guarantee_fee": None, "url": "http://t", "source_url": "http://t",
}


def test_db_rows_return_the_existing_fifteen_field_dict():
    products = load_all_products_from(FakeRepository([_entity("imbank-1", "bank", ["cafe"])]))

    assert [list(p.keys()) for p in products] == [_DICT_FIELDS]  # source_file 은 응답에 없다
    assert products[0]["category"] == ["cafe"]
    match_products(products, funding_gap=0, category="cafe", business_age_months=0, owner_age=None)


def test_db_rows_preserve_category_three_states():
    products = load_all_products_from(
        FakeRepository([
            _entity("a", "bank", None),
            _entity("b", "guarantee", []),
            _entity("c", "policy", ["cafe"]),
        ])
    )
    by_id = {p["product_id"]: p for p in products}

    assert by_id["a"]["category"] is None
    assert by_id["b"]["category"] == []
    assert by_id["c"]["category"] == ["cafe"]
    # None 통과 / [] 탈락 — matcher 의미가 DB 경로에서도 같다
    matched = match_products(products, funding_gap=0, category="restaurant",
                             business_age_months=0, owner_age=None)
    assert [p["product_id"] for p in matched] == ["a"]


def test_empty_db_falls_back_to_json_with_warning(tmp_path):
    with _write_manual_json(tmp_path, [_JSON_PRODUCT]):
        with mock.patch.object(manual_product_gateway, "_logger") as logger:
            products = load_all_products_from(FakeRepository([]))

    assert [p["product_id"] for p in products] == ["json-1"]
    assert logger.warning.call_count == 1


def test_db_failure_falls_back_to_json_with_warning(tmp_path):
    with _write_manual_json(tmp_path, [_JSON_PRODUCT]):
        with mock.patch.object(manual_product_gateway, "_logger") as logger:
            products = load_all_products_from(FakeRepository(error=RuntimeError("DB 연결 실패")))

    assert [p["product_id"] for p in products] == ["json-1"]
    assert logger.warning.call_count == 1


def test_db_rows_skip_unknown_provider_type():
    """matcher 우선순위 표에 없는 provider_type 은 정렬 시 KeyError(500) — JSON 경로와 같은 가드."""
    with mock.patch.object(manual_product_gateway, "_logger") as logger:
        products = load_all_products_from(
            FakeRepository([_entity("ok-1", "bank", None), _entity("odd-1", "fintech", None)])
        )

    assert [p["product_id"] for p in products] == ["ok-1"]
    assert logger.warning.call_count == 1
