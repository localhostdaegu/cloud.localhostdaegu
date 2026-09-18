"""매칭 라우터 — GET /matching 엔드포인트."""

from dataclasses import asdict

from fastapi import APIRouter, Query

from apps.matching.adapter.outbound.gateways.manual_product_gateway import (
    load_all_products,
    load_consultation_products,
)
from apps.matching.domain.consultation import build_consultation_candidates
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


@router.get("/consultation")
def get_consultation_candidates(
    external_funding_need: int = Query(ge=0),
    category: str = "",
    business_registered: bool | None = None,
    business_age_months: int | None = Query(default=None, ge=0),
    owner_age: int | None = Query(default=None, ge=0, le=120),
    district_code: str | None = Query(default=None, min_length=5, max_length=5),
    include_unverified: bool = False,
) -> list[dict]:
    """iM뱅크 상담 후보와 남은 확인 사항 (§5-2). 자격 확정이나 승인 결과가 아니다.

    미상 값은 쿼리에서 생략한다 — 생략을 충족·미달로 바꾸지 않는다.
    include_unverified=True 면 취급 근거가 확인되지 않은 상품도 참고자료로 함께 준다(§5-2).
    district_code(자치구 5자리)를 주면 자치구 한정 상품을 해당 지역에서만 보여준다.
    """
    candidates = build_consultation_candidates(
        load_consultation_products(),
        external_funding_need=external_funding_need,
        category=category,
        business_registered=business_registered,
        business_age_months=business_age_months,
        owner_age=owner_age,
        district_code=district_code,
        include_unverified=include_unverified,
    )
    return [asdict(c) for c in candidates]
