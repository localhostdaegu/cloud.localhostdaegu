"""상품 로더 — DB(정본) 우선, 실패·0건이면 수기 JSON(data/manual/*.json) 폴백.

반환 dict 15필드는 GET /matching 응답 형태 그대로다(스펙 §2-5). category 는
None(업종 무관) / [](해당 업종 없음) / [...] 3상태로 복원되며 match_products 는 수정하지 않는다.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path

from apps.matching.domain.matcher import PROVIDER_TYPES
# cross-BC 접근은 이 어댑터에서만 하고, product BC 의 **유스케이스**만 본다(§7·§11).
# 리포지토리(Adapter)를 직접 import 하지 않는다 — analysis 의 market_data_gateway 와 같은 형태.
from apps.product.app.ports.input.finance_product_use_case import FinanceProductUseCase
from apps.product.dependencies.finance_product_dependencies import (
    get_finance_product_use_case,
)
from apps.product.domain.entities.finance_product_entity import FinanceProduct

_logger = logging.getLogger(__name__)

_REQUIRED_FIELDS = {
    "product_id", "provider", "provider_type", "product_name", "target", "region",
    "business_age_min", "business_age_max", "category", "owner_age_max",
    "loan_limit", "interest_rate", "guarantee_fee", "url", "source_url"
}

# JSON 에 없을 수 있는 선택 필드 — 없으면 None 으로 채운다(지역 제한 없음).
_OPTIONAL_FIELDS = ("district_code",)

@lru_cache(maxsize=1)
def load_consultation_products() -> list[dict]:
    """상담 경로용 — 15필드에 consultation_metadata 를 더해 읽는다.

    GET /matching 의 15필드 응답 계약을 흔들지 않으려고 로더를 분리했다.
    메타데이터가 없는 상품은 키 자체를 넣지 않아 '미확인'으로 남는다(§5-2).
    """
    return load_consultation_products_from(get_finance_product_use_case())


def load_consultation_products_from(catalog: FinanceProductUseCase) -> list[dict]:
    try:
        products = catalog.list_all()
    except Exception:
        _logger.warning("finance_product 조회 실패 — 상담 후보를 구성하지 않는다", exc_info=True)
        return []
    return [
        {**_to_dict(p), "consultation_metadata": _consultation_metadata(p)}
        for p in products
        if _is_matchable(p.product_id, p.provider_type)
    ]


def _consultation_metadata(product: FinanceProduct) -> dict | None:
    """엔티티의 상담 메타데이터 → §5-2 dict. 미확인(None)이면 None 그대로."""
    if product.consultation is None:
        return None
    steps = {"prerequisite": [], "application_step": [], "document": []}
    for step in sorted(product.procedure_steps, key=lambda s: (s.step_type, s.step_order)):
        steps.setdefault(step.step_type, []).append(step.description)
    return {
        "bank_connection": product.consultation.bank_connection,
        "bank_connection_source_url": product.consultation.bank_connection_source_url,
        "business_registration_required": product.consultation.business_registration_required,
        "prerequisites": steps["prerequisite"],
        "application_steps": steps["application_step"],
        "documents": steps["document"],
        "verified_at": (
            product.consultation.verified_at.isoformat() if product.consultation.verified_at else None
        ),
    }


@lru_cache(maxsize=1)
def load_all_products() -> list[dict]:
    """DB 정본에서 상품을 읽고, 비어 있거나 실패하면 수기 JSON 으로 폴백한다."""
    return load_all_products_from(get_finance_product_use_case())


def load_all_products_from(catalog: FinanceProductUseCase) -> list[dict]:
    """주입된 유스케이스로 상품을 읽는다 — 테스트가 DB 없이 두 경로를 모두 검증할 수 있게 분리."""
    try:
        products = catalog.list_all()
    except Exception:  # DB 미구성·연결 실패 — 데모가 멈추지 않게 JSON 으로 계속한다
        _logger.warning("finance_product 조회 실패 — data/manual JSON 폴백", exc_info=True)
        return _load_from_json()
    if not products:
        _logger.warning("finance_product 행 0건 — data/manual JSON 폴백 (시드 CLI 미실행)")
        return _load_from_json()
    return [_to_dict(p) for p in products if _is_matchable(p.product_id, p.provider_type)]


def _to_dict(product: FinanceProduct) -> dict:
    """엔티티 → 기존 15필드 dict. source_file 등 시드 추적 필드는 응답에 넣지 않는다."""
    return {
        "product_id": product.product_id,
        "provider": product.provider,
        "provider_type": product.provider_type,
        "product_name": product.product_name,
        "target": product.target,
        "region": product.region,
        "business_age_min": product.business_age_min,
        "business_age_max": product.business_age_max,
        "category": product.category,
        "owner_age_max": product.owner_age_max,
        "loan_limit": product.loan_limit,
        "interest_rate": product.interest_rate,
        "guarantee_fee": product.guarantee_fee,
        "url": product.url,
        "source_url": product.source_url,
        "district_code": product.district_code,
    }


def _is_matchable(product_id: str, provider_type: str) -> bool:
    """매칭 정렬 KeyError(500) 방지 — JSON·DB 두 경로에 같은 가드를 둔다."""
    if provider_type in PROVIDER_TYPES:
        return True
    _logger.warning("상품 %s 건너뜀 — 알 수 없는 provider_type: %s", product_id, provider_type)
    return False


def _load_from_json() -> list[dict]:
    """data/manual/*.json의 3파일을 읽어 합침. 스키마 검증 후 반환."""
    data_dir = Path(__file__).resolve().parents[6] / "data" / "manual"

    all_products = []
    for json_file in ["imbank_products.json", "dgsinbo_products.json", "daegu_youth_startup.json"]:
        file_path = data_dir / json_file
        if not file_path.exists():
            continue

        with open(file_path) as f:
            products = json.load(f)

        for p in products:
            # 필수 필드 검증
            missing = _REQUIRED_FIELDS - set(p.keys())
            if missing:
                raise ValueError(f"Product {p.get('product_id', '?')} 누락 필드: {missing}")
            if not _is_matchable(p["product_id"], p["provider_type"]):
                continue
            # 15필드만 남긴다 — consultation_metadata 등 추가 키가 GET /matching 응답에
            # 섞이면 DB 경로와 형태가 달라진다(스펙 §2-5).
            all_products.append(
                {name: p[name] for name in _REQUIRED_FIELDS}
                | {name: p.get(name) for name in _OPTIONAL_FIELDS}
            )

    return all_products
