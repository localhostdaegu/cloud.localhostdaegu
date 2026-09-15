"""매칭 도메인 함수 테스트 — verbatim from task brief."""

import json
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from apps.matching.domain.matcher import match_products
from apps.matching.adapter.outbound.gateways.manual_product_gateway import load_all_products

PRODUCTS = [
    {"product_id": "dgsinbo-1", "provider_type": "guarantee", "loan_limit": 30_000_000,
     "category": None, "business_age_min": 0, "business_age_max": None, "owner_age_max": None},
    {"product_id": "imbank-1", "provider_type": "bank", "loan_limit": 50_000_000,
     "category": ["general_restaurants"], "business_age_min": 0, "business_age_max": None, "owner_age_max": None},
    {"product_id": "youth-1", "provider_type": "policy", "loan_limit": 20_000_000,
     "category": None, "business_age_min": 0, "business_age_max": 12, "owner_age_max": 39},
]

def test_priority_order_guarantee_bank_policy():
    out = match_products(PRODUCTS, funding_gap=10_000_000, category="general_restaurants",
                         business_age_months=0, owner_age=30)
    assert [p["product_id"] for p in out] == ["dgsinbo-1", "imbank-1", "youth-1"]

def test_filters_apply():
    out = match_products(PRODUCTS, funding_gap=10_000_000, category="rest_cafes",
                         business_age_months=24, owner_age=45)
    # imbank-1은 업종 불일치, youth-1은 업력·연령 초과 → 보증만 남음
    assert [p["product_id"] for p in out] == ["dgsinbo-1"]

def test_limit_filter():
    out = match_products(PRODUCTS, funding_gap=40_000_000, category="general_restaurants",
                         business_age_months=0, owner_age=30)
    assert "dgsinbo-1" not in [p["product_id"] for p in out]   # 한도 3천 < 부족 4천


def test_gateway_loads_products_from_json_files(tmp_path):
    """게이트웨이: 실제 JSON 파일들을 로드하고 상품 데이터 검증."""
    # 게이트웨이가 읽는 정확한 경로 구조 생성
    manual_dir = tmp_path / "data" / "manual"
    manual_dir.mkdir(parents=True)

    # 3개의 제품 파일 생성 (각 파일에 1개의 유효한 상품)
    imbank_product = {
        "product_id": "imbank-test", "provider": "test-bank", "provider_type": "bank",
        "product_name": "테스트 은행상품", "target": "소상공인", "region": "대구",
        "business_age_min": 0, "business_age_max": None, "category": ["general_restaurants"],
        "owner_age_max": None, "loan_limit": 50000000, "interest_rate": 5.5,
        "guarantee_fee": 0.8, "url": "http://test.com", "source_url": "http://test.com"
    }
    (manual_dir / "imbank_products.json").write_text(json.dumps([imbank_product]))

    dgsinbo_product = {
        "product_id": "dgsinbo-test", "provider": "test-guarantee", "provider_type": "guarantee",
        "product_name": "테스트 보증", "target": "소상공인", "region": "대구",
        "business_age_min": 0, "business_age_max": None, "category": None,
        "owner_age_max": None, "loan_limit": 30000000, "interest_rate": 0.0,
        "guarantee_fee": 0.5, "url": "http://test.com", "source_url": "http://test.com"
    }
    (manual_dir / "dgsinbo_products.json").write_text(json.dumps([dgsinbo_product]))

    youth_product = {
        "product_id": "youth-test", "provider": "test-policy", "provider_type": "policy",
        "product_name": "테스트 정책자금", "target": "청년", "region": "대구",
        "business_age_min": 0, "business_age_max": 12, "category": None,
        "owner_age_max": 39, "loan_limit": 20000000, "interest_rate": 2.5,
        "guarantee_fee": 0.0, "url": "http://test.com", "source_url": "http://test.com"
    }
    (manual_dir / "daegu_youth_startup.json").write_text(json.dumps([youth_product]))

    # 게이트웨이의 Path 반환값을 tmp_path 루트로 패치
    with mock.patch('apps.matching.adapter.outbound.gateways.manual_product_gateway.Path') as mock_path_class:
        # __file__은 gateway 모듈의 위치가 아닌, tmp_path를 기준으로 돌려줌
        mock_instance = mock.MagicMock()
        mock_instance.resolve.return_value.parents.__getitem__.return_value = tmp_path
        mock_path_class.return_value = mock_instance

        # 캐시 클리어하고 로드
        load_all_products.cache_clear()
        products = load_all_products()

        # 검증: 3개 파일이 모두 로드되었는지 확인
        assert len(products) == 3, f"Expected 3 products, got {len(products)}"
        product_ids = [p["product_id"] for p in products]
        assert "imbank-test" in product_ids
        assert "dgsinbo-test" in product_ids
        assert "youth-test" in product_ids


def test_gateway_raises_on_missing_required_field(tmp_path):
    """게이트웨이: 필수 필드 누락 시 ValueError 발생."""
    manual_dir = tmp_path / "data" / "manual"
    manual_dir.mkdir(parents=True)

    # 필수 필드 하나(provider)를 뺀 불완전한 상품
    invalid_product = {
        "product_id": "invalid-1", "provider_type": "bank",
        # ⚠ "provider" 필드 누락 (필수)
        "product_name": "테스트", "target": "테스트", "region": "대구",
        "business_age_min": 0, "business_age_max": None, "category": None,
        "owner_age_max": None, "loan_limit": 10000000, "interest_rate": 5.0,
        "guarantee_fee": 0.5, "url": "http://test.com", "source_url": "http://test.com"
    }
    (manual_dir / "imbank_products.json").write_text(json.dumps([invalid_product]))

    # 다른 두 파일은 유효한 상품으로 생성
    (manual_dir / "dgsinbo_products.json").write_text(json.dumps([]))
    (manual_dir / "daegu_youth_startup.json").write_text(json.dumps([]))

    with mock.patch('apps.matching.adapter.outbound.gateways.manual_product_gateway.Path') as mock_path_class:
        mock_instance = mock.MagicMock()
        mock_instance.resolve.return_value.parents.__getitem__.return_value = tmp_path
        mock_path_class.return_value = mock_instance

        load_all_products.cache_clear()

        # ValueError 발생 확인, 에러 메시지에 누락 필드명 포함 확인
        with pytest.raises(ValueError, match="provider"):
            load_all_products()
