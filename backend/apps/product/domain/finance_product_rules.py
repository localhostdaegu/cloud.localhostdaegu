"""금융상품 도메인 규칙 — 허용값 상수와 category 3상태 인코딩 (프레임워크 의존 없음).

category 3상태는 matcher.match_products 의 판정 의미를 DB 왕복 뒤에도 그대로 유지하기 위한 것이다.
`None` = 업종 무관(모두 통과) / `[]` = 해당 업종 없음(모두 탈락) / `[...]` = 해당 업종만 통과.
M:N 테이블(finance_product_category)만으로는 앞의 두 상태를 구분할 수 없어
`finance_product.category_restricted` 플래그와 짝을 이룬다.
"""

from collections.abc import Iterable

# product_consultation_metadata.bank_connection 허용값 — DB CHECK 대신 쓰기 경로에서 검증한다
# (값 추가가 마이그레이션을 유발하지 않게 한다).
BANK_CONNECTIONS = frozenset({"direct", "linked", "unverified", "none"})

# product_procedure_step.step_type 허용값 — 전환계획 §5-2 리스트 3종의 판별자
STEP_TYPES = frozenset({"prerequisite", "application_step", "document"})


def encode_category(category: list[str] | None) -> tuple[bool, list[str]]:
    """3상태 → (category_restricted, industry_id 목록). `None` 만 제한 없음이다."""
    if category is None:
        return False, []
    return True, list(category)


def decode_category(category_restricted: bool, industry_ids: Iterable[str]) -> list[str] | None:
    """(category_restricted, industry_id 목록) → 3상태.

    M:N 테이블에 순서 컬럼이 없으므로 정렬해 결정적으로 복원한다.
    매칭은 멤버십(`category not in p["category"]`)만 보므로 순서는 의미를 갖지 않는다.
    """
    if not category_restricted:
        return None
    return sorted(industry_ids)
