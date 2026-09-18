"""상담 후보 구성 — 전환계획 §5-2 (프레임워크 의존 없는 순수 함수).

`GET /matching/consultation` 과 리포트 게이트웨이가 함께 호출한다.
자격 확정이나 승인 결과가 아니다. 확인하지 못한 조건은 남은 확인 사항으로 보존한다.
"""

from dataclasses import dataclass, field

from apps.matching.domain.matcher import _PRIORITY

# iM뱅크 주 상담 후보가 될 수 있는 연결 분류. unverified·none 은 후보로 안내하지 않는다.
_BANK_CANDIDATE_CONNECTIONS = frozenset({"direct", "linked"})

_EMPTY_METADATA: dict = {
    "bank_connection": "unverified",
    "bank_connection_source_url": None,
    "business_registration_required": None,
    "prerequisites": [],
    "application_steps": [],
    "documents": [],
    "verified_at": None,
}


@dataclass(frozen=True)
class ConsultationCandidate:
    product: dict
    metadata: dict
    status: str  # reviewable | prerequisites_needed | needs_check
    reason: str
    unresolved_conditions: list[str] = field(default_factory=list)


def build_consultation_candidates(
    products: list[dict],
    *,
    external_funding_need: int,
    category: str,
    business_registered: bool | None,
    business_age_months: int | None,
    owner_age: int | None,
) -> list[ConsultationCandidate]:
    candidates = [
        _to_candidate(product, external_funding_need, business_registered, owner_age)
        for product in products
        if _is_bank_candidate(product) and _passes_conditions(product, category, business_age_months, owner_age)
    ]
    return sorted(candidates, key=lambda c: _PRIORITY[c.product["provider_type"]])


def _metadata_of(product: dict) -> dict:
    """메타데이터가 없으면 미확인이다 — 기존 자료도 계속 읽을 수 있게 한다(§5-2)."""
    return {**_EMPTY_METADATA, **(product.get("consultation_metadata") or {})}


def _is_bank_candidate(product: dict) -> bool:
    return _metadata_of(product)["bank_connection"] in _BANK_CANDIDATE_CONNECTIONS


def _passes_conditions(
    product: dict, category: str, business_age_months: int | None, owner_age: int | None
) -> bool:
    """기존 업종·업력·연령 조건을 그대로 쓴다. 한도는 거르지 않고 설명에 반영한다."""
    if product["category"] is not None and category not in product["category"]:
        return False
    if business_age_months is not None:
        if product["business_age_min"] is not None and business_age_months < product["business_age_min"]:
            return False
        if product["business_age_max"] is not None and business_age_months > product["business_age_max"]:
            return False
    # 연령 미확인은 자격 미달이 아니다 — 확인 사항으로 남긴다.
    if product["owner_age_max"] is not None and owner_age is not None and owner_age > product["owner_age_max"]:
        return False
    return True


def _to_candidate(
    product: dict, external_funding_need: int, business_registered: bool | None, owner_age: int | None
) -> ConsultationCandidate:
    metadata = _metadata_of(product)
    unresolved = _unresolved(product, metadata, business_registered, owner_age)
    status = _status(metadata, business_registered, unresolved)
    return ConsultationCandidate(
        product=product,
        metadata=metadata,
        status=status,
        reason=_reason(product, metadata, external_funding_need, business_registered),
        unresolved_conditions=unresolved,
    )


def _unresolved(
    product: dict, metadata: dict, business_registered: bool | None, owner_age: int | None
) -> list[str]:
    items: list[str] = []
    if metadata["business_registration_required"] is None:
        items.append("사업자등록 필요 여부가 공식 안내에서 확인되지 않음")
    elif metadata["business_registration_required"] and business_registered is None:
        items.append("사업자등록 여부 미입력")
    if not metadata["documents"]:
        items.append("준비서류는 공식 안내에서 확인 필요")
    if not metadata["application_steps"]:
        items.append("신청 경로는 공식 안내에서 확인 필요")
    if product["owner_age_max"] is not None and owner_age is None:
        items.append("연령 조건이 있으나 연령 미입력")
    if product["interest_rate"] is None:
        items.append("적용 금리는 은행·기관 상담에서 확인")
    if metadata["verified_at"] is None:
        items.append("원문 확인일 미기록 — 현재 접수 가능 여부 확인 필요")
    return items


def _status(metadata: dict, business_registered: bool | None, unresolved: list[str]) -> str:
    if metadata["business_registration_required"] is True and business_registered is False:
        return "prerequisites_needed"
    if metadata["prerequisites"]:
        return "prerequisites_needed"
    return "needs_check" if unresolved else "reviewable"


def _reason(product: dict, metadata: dict, external_funding_need: int, business_registered: bool | None) -> str:
    parts = [
        "iM뱅크 직접 취급으로 확인됨"
        if metadata["bank_connection"] == "direct"
        else "iM뱅크 연계 근거가 확인됨"
    ]
    limit = product["loan_limit"]
    if limit is not None and limit < external_funding_need:
        parts.append(
            f"공시 한도 {limit:,}원은 조달 필요 {external_funding_need:,}원보다 적어 일부만 충당 가능"
        )
    if metadata["business_registration_required"] is True and business_registered is False:
        parts.append("사업자등록 후 신청 가능")
    return " · ".join(parts)
