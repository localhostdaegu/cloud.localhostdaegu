"""상담 후보 구성 — 전환계획 §5-2 (합성 데이터, DB·네트워크 없음)."""

from apps.matching.domain.consultation import build_consultation_candidates

_BASE = {
    "product_id": "test-only", "provider": "테스트 기관", "provider_type": "bank",
    "product_name": "합성 테스트 상품", "target": "테스트", "region": "대구", "category": None,
    "business_age_min": 0, "business_age_max": None, "owner_age_max": None,
    "loan_limit": 10_000_000, "interest_rate": None, "guarantee_fee": None,
    "url": "https://example.org", "source_url": "https://example.org",
}
_METADATA = {
    "bank_connection": "direct", "bank_connection_source_url": "https://example.org/notice",
    "business_registration_required": None, "prerequisites": [], "application_steps": [],
    "documents": [], "verified_at": "2026-09-18",
}


def _product(**overrides):
    metadata = {**_METADATA, **overrides.pop("consultation_metadata", {})}
    return {**_BASE, **overrides, "consultation_metadata": metadata}


def _build(products, **kwargs):
    defaults = dict(
        external_funding_need=2_000_000, category="cafe",
        business_registered=True, business_age_months=0, owner_age=None,
    )
    return build_consultation_candidates(products, **{**defaults, **kwargs})


def test_unverified_bank_connection_is_not_a_bank_candidate():
    """취급·연계 근거가 없으면 iM뱅크 후보로 안내하지 않는다."""
    assert _build([_product(consultation_metadata={"bank_connection": "unverified"})]) == []


def test_missing_metadata_is_treated_as_unverified():
    """consultation_metadata 자체가 없는 기존 12건은 미확인이다."""
    product = {**_BASE}
    assert build_consultation_candidates(
        [product], external_funding_need=2_000_000, category="cafe",
        business_registered=True, business_age_months=0, owner_age=None,
    ) == []


def test_direct_and_linked_are_candidates():
    candidates = _build([
        _product(product_id="a", consultation_metadata={"bank_connection": "direct"}),
        _product(product_id="b", provider_type="guarantee", consultation_metadata={"bank_connection": "linked"}),
    ])
    assert [c.product["product_id"] for c in candidates] == ["b", "a"]  # 보증 → 은행 순


def test_registration_required_before_registering_needs_prerequisites():
    (candidate,) = _build(
        [_product(consultation_metadata={"business_registration_required": True})],
        business_registered=False,
    )
    assert candidate.status == "prerequisites_needed"
    assert "사업자등록" in candidate.reason


def test_unknown_registration_requirement_stays_a_check_item():
    """미확인을 충족으로도 미달로도 바꾸지 않는다(§4-2)."""
    (candidate,) = _build([_product()], business_registered=False)

    assert candidate.status == "needs_check"
    assert any("사업자등록" in c for c in candidate.unresolved_conditions)


def test_limit_below_need_is_explained_not_filtered_out():
    """한도가 조달 필요보다 작아도 검토 대상에서 빼지 않는다(§4-2)."""
    (candidate,) = _build([_product(loan_limit=1_000_000)], external_funding_need=2_000_000)

    assert "한도" in candidate.reason


def test_region_limited_product_stays_excluded():
    """category=[] 는 해당 업종 없음 — 기존 매처와 같은 판정을 유지한다."""
    assert _build([_product(category=[])]) == []


def test_business_age_and_owner_age_conditions_are_kept():
    too_new = _product(business_age_min=12)
    assert _build([too_new], business_age_months=0) == []

    too_old = _product(owner_age_max=39)
    assert _build([too_old], owner_age=45) == []


def test_unknown_owner_age_is_not_a_disqualification():
    (candidate,) = _build([_product(owner_age_max=39)], owner_age=None)

    assert any("연령" in c for c in candidate.unresolved_conditions)


def test_empty_documents_become_a_check_item_not_a_fabricated_list():
    (candidate,) = _build([_product(consultation_metadata={"documents": []})])

    assert any("준비서류" in c for c in candidate.unresolved_conditions)


def test_prerequisites_are_preserved_in_order():
    (candidate,) = _build([
        _product(consultation_metadata={
            "business_registration_required": False,
            "prerequisites": ["소진공 확인서 발급", "보증기관 상담"],
        })
    ])
    assert candidate.metadata["prerequisites"] == ["소진공 확인서 발급", "보증기관 상담"]
    assert candidate.status == "prerequisites_needed"
