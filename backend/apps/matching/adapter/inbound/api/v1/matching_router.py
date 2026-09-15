"""매칭 라우터 — GET /matching 엔드포인트."""

from fastapi import APIRouter
from apps.matching.adapter.outbound.gateways.manual_product_gateway import load_all_products
from apps.matching.domain.matcher import match_products

router = APIRouter(prefix="/matching", tags=["matching"])

@router.get("/myself")
def myself() -> dict:
    return {"app": "matching", "status": "wired"}

@router.get("")
def get_matching(
    funding_gap: int,
    category: str,
    business_age_months: int,
    owner_age: int | None = None
) -> list[dict]:
    """부족금액·업종·업력·연령으로 상품 매칭. 우선순위: 보증→은행→정책자금."""
    products = load_all_products()
    return match_products(products, funding_gap, category, business_age_months, owner_age)
