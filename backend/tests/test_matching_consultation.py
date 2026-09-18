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


def _reference(products, **kwargs):
    return _build(products, include_unverified=True, **kwargs)


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
    # iM뱅크 자사 취급이 최우선 — 보증→은행 정렬보다 은행 연결 등급이 먼저다.
    assert [c.product["product_id"] for c in candidates] == ["a", "b"]


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


# --- §5-2: unverified 는 은행 후보가 아니라 '관련 기관 참고자료'로만 ------------


def test_unverified_products_are_excluded_by_default():
    """기본 동작은 그대로 — iM뱅크 주 상담 후보에는 들어가지 않는다."""
    assert _build([_product(consultation_metadata={"bank_connection": "unverified"})]) == []


def test_unverified_products_can_be_requested_as_reference():
    (candidate,) = _build(
        [_product(consultation_metadata={"bank_connection": "unverified"})], include_unverified=True
    )

    assert candidate.metadata["bank_connection"] == "unverified"
    # 취급이 확인된 것처럼 쓰지 않고, 직접 확인이 필요하다고 말한다.
    assert "직접 확인 필요" in candidate.reason
    assert "취급으로 확인" not in candidate.reason


def test_reference_listing_still_excludes_products_with_no_bank_route():
    """'none'은 은행 취급 자체가 없다고 확인된 것 — 참고자료에도 넣지 않는다."""
    assert _build(
        [_product(consultation_metadata={"bank_connection": "none"})], include_unverified=True
    ) == []


def test_reference_listing_keeps_bank_candidates_first():
    candidates = _build(
        [
            _product(product_id="ref", consultation_metadata={"bank_connection": "unverified"}),
            _product(product_id="bank", consultation_metadata={"bank_connection": "direct"}),
        ],
        include_unverified=True,
    )

    assert [c.product["product_id"] for c in candidates] == ["bank", "ref"]


def test_reference_listing_applies_the_same_eligibility_conditions():
    """참고자료라고 자격 조건을 느슨하게 보지 않는다."""
    too_old = _product(owner_age_max=39, consultation_metadata={"bank_connection": "unverified"})

    assert _build([too_old], owner_age=45, include_unverified=True) == []


def test_unchecked_product_says_it_was_never_checked():
    """원문을 아직 안 본 것과, 보았는데 은행 명시가 없던 것은 다르다."""
    (candidate,) = _reference([{**_BASE}])  # consultation_metadata 자체가 없다

    assert "아직 확인하지 못" in candidate.reason


def test_checked_but_unnamed_bank_says_so():
    (candidate,) = _reference(
        [_product(consultation_metadata={"bank_connection": "unverified", "verified_at": "2026-09-18"})]
    )

    assert "취급 은행이 명시되지 않" in candidate.reason


# --- 은행 우선순위: iM뱅크 직접 취급 → 연계 → 취급 미확인 --------------------


def test_direct_handling_outranks_linked():
    """같은 iM뱅크 후보라도 자사 취급 고시가 연계 근거보다 앞선다."""
    candidates = _build([
        _product(product_id="linked", consultation_metadata={"bank_connection": "linked"}),
        _product(product_id="direct", consultation_metadata={"bank_connection": "direct"}),
    ])

    assert [c.product["product_id"] for c in candidates] == ["direct", "linked"]


def test_bank_priority_beats_provider_priority():
    """보증→은행→정책 정렬보다 은행 연결 등급이 먼저다 — iM뱅크가 최우선이다."""
    candidates = _reference([
        _product(product_id="guarantee-ref", provider_type="guarantee",
                 consultation_metadata={"bank_connection": "unverified"}),
        _product(product_id="policy-direct", provider_type="policy",
                 consultation_metadata={"bank_connection": "direct"}),
    ])

    assert [c.product["product_id"] for c in candidates] == ["policy-direct", "guarantee-ref"]


def test_provider_priority_still_orders_within_the_same_bank_grade():
    candidates = _build([
        _product(product_id="bank", provider_type="bank", consultation_metadata={"bank_connection": "direct"}),
        _product(product_id="guarantee", provider_type="guarantee", consultation_metadata={"bank_connection": "direct"}),
    ])

    assert [c.product["product_id"] for c in candidates] == ["guarantee", "bank"]
