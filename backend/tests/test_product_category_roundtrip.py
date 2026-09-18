"""금융상품 category 3상태 보존 — 인코딩/디코딩·ORM 왕복 (DB 불필요).

matcher.match_products 는 `category is None` = 업종 무관 통과, `[]` = 전부 탈락으로 판정한다.
DB 왕복이 이 구분을 무너뜨리면 GET /matching 이 회귀한다 (설계 스펙 §2-2).
"""

from datetime import date

import pytest

from apps.product.adapter.outbound.orm_mappers import finance_product_orm_mapper as orm_mapper
from apps.product.domain.entities.finance_product_entity import (
    ConsultationMetadata,
    FinanceProduct,
    ProcedureStep,
)
from apps.product.domain.finance_product_rules import decode_category, encode_category


def _product(category: list[str] | None, **overrides) -> FinanceProduct:
    base = dict(
        product_id="imbank-1",
        provider="iM뱅크",
        provider_type="bank",
        product_name="테스트 상품",
        target="소상공인",
        region="전국 (iM뱅크 영업점 취급)",
        business_age_min=0,
        business_age_max=None,
        owner_age_max=None,
        loan_limit=100_000_000,
        interest_rate=2.5,
        guarantee_fee=0.9,
        url="https://example.test/product",
        source_url="https://example.test/product",
        category=category,
        source_file="imbank_products.json",
    )
    return FinanceProduct(**{**base, **overrides})


@pytest.mark.parametrize(
    ("category", "restricted", "industry_ids"),
    [
        (None, False, []),          # 업종 무관 — 모든 업종 통과
        ([], True, []),             # 해당 업종 없음 — 전부 탈락 (구·군 한정 상품)
        (["cafe", "restaurant"], True, ["cafe", "restaurant"]),
    ],
)
def test_category_encode_decode_roundtrip(category, restricted, industry_ids):
    assert encode_category(category) == (restricted, industry_ids)
    assert decode_category(restricted, industry_ids) == category


def test_category_decode_normalizes_order():
    """M:N 테이블에는 순서 컬럼이 없다 — 복원값은 정렬로 결정적이다(매칭은 멤버십만 본다)."""
    assert decode_category(True, ["restaurant", "cafe"]) == ["cafe", "restaurant"]


@pytest.mark.parametrize("category", [None, [], ["cafe", "restaurant"]])
def test_orm_roundtrip_preserves_category_three_states(category):
    entity = _product(category)

    restored = orm_mapper.to_entity(
        orm_mapper.to_orm(entity),
        orm_mapper.to_category_orms(entity),
        orm_mapper.to_metadata_orm(entity),
        orm_mapper.to_step_orms(entity),
    )

    assert restored.category == category
    assert restored == entity


def test_orm_roundtrip_preserves_metadata_and_steps():
    entity = _product(
        ["cafe"],
        consultation=ConsultationMetadata(
            bank_connection="linked",
            bank_connection_source_url="https://example.test/source",
            business_registration_required=None,  # 미확인 — False 로 바뀌면 안 된다
            verified_at=date(2026, 9, 18),
        ),
        # to_entity 는 (step_type, step_order) 로 정렬해 복원한다 — DB 행 순서는 보장되지 않는다
        procedure_steps=[
            ProcedureStep(step_type="application_step", step_order=1, description="영업점 방문"),
            ProcedureStep(step_type="application_step", step_order=2, description="서류 제출"),
            ProcedureStep(step_type="prerequisite", step_order=1, description="사업자등록"),
        ],
    )

    restored = orm_mapper.to_entity(
        orm_mapper.to_orm(entity),
        orm_mapper.to_category_orms(entity),
        orm_mapper.to_metadata_orm(entity),
        orm_mapper.to_step_orms(entity),
    )

    assert restored == entity
    assert restored.consultation.business_registration_required is None


def test_orm_roundtrip_without_metadata_row_means_unverified():
    """메타데이터 행이 없으면 '미확인'이다 — 기존 12건은 행 없이 적재된다 (스펙 §2-3)."""
    entity = _product(None)

    restored = orm_mapper.to_entity(orm_mapper.to_orm(entity), [], None, [])

    assert restored.consultation is None
    assert restored.procedure_steps == []
