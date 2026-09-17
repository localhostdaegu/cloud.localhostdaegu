"""금융상품 매칭 도메인 함수 — 우선순위 정렬 + 필터링."""

_PRIORITY = {"guarantee": 0, "bank": 1, "policy": 2}   # 보증 연계 → 은행 → 정책자금

def match_products(products: list[dict], funding_gap: int, category: str,
                   business_age_months: int, owner_age: int | None) -> list[dict]:
    def ok(p: dict) -> bool:
        if p["loan_limit"] is not None and p["loan_limit"] < funding_gap: return False
        if p["category"] is not None and category not in p["category"]: return False
        if p["business_age_min"] is not None and business_age_months < p["business_age_min"]: return False
        if p["business_age_max"] is not None and business_age_months > p["business_age_max"]: return False
        # 연령 미수집(None)은 자격 미달이 아니므로 제외하지 않는다
        if p["owner_age_max"] is not None and owner_age is not None and owner_age > p["owner_age_max"]: return False
        return True
    return sorted((p for p in products if ok(p)), key=lambda p: _PRIORITY[p["provider_type"]])
