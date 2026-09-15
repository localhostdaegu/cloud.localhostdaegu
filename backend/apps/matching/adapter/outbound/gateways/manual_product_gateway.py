"""수기 JSON 상품 파일 로더 — data/manual/*.json 합치기 + 스키마 검증."""

import json
from functools import lru_cache
from pathlib import Path

_REQUIRED_FIELDS = {
    "product_id", "provider", "provider_type", "product_name", "target", "region",
    "business_age_min", "business_age_max", "category", "owner_age_max",
    "loan_limit", "interest_rate", "guarantee_fee", "url", "source_url"
}

@lru_cache(maxsize=1)
def load_all_products() -> list[dict]:
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
            all_products.append(p)

    return all_products
