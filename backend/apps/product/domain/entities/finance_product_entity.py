from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class ConsultationMetadata:
    """상품 원문 대조 기록 — 상품 식별정보와 수명주기가 다르다(전환계획 §10-3).

    엔티티에 이 값이 없으면(=행 없음) '미확인'이다. 추정으로 채우지 않는다.
    """

    bank_connection: str  # direct / linked / unverified / none — BANK_CONNECTIONS
    bank_connection_source_url: str | None = None
    business_registration_required: bool | None = None  # None = 미확인 (False 로 바꾸지 않는다)
    verified_at: date | None = None  # 원문 확인일 — 접수 가능 보장이 아니다


@dataclass(frozen=True)
class ProcedureStep:
    """사전조건·신청절차·준비서류 — 상품별 실제 순서를 보존한다(전환계획 §4-2)."""

    step_type: str  # prerequisite / application_step / document — STEP_TYPES
    step_order: int  # 1부터
    description: str


@dataclass
class FinanceProduct:
    """금융상품 — DB 정본. data/manual/*.json 은 시드 입력일 뿐이다(스펙 §2).

    category 3상태(None/[]/[...])를 도메인에서 그대로 표현한다. 이 구분이 무너지면
    GET /matching 의 업종 필터가 회귀한다 — 인코딩 규칙은 finance_product_rules 참조.
    """

    product_id: str  # "imbank-1" 등 수기 슬러그
    provider: str  # "iM뱅크" / "대구신용보증재단"
    provider_type: str  # bank / guarantee / policy — matcher._PRIORITY 키
    product_name: str
    target: str  # 지원대상 원문 (LLM 구조화 추출 원천)
    region: str  # "전국 (iM뱅크 영업점 취급)" 등 원문
    business_age_min: int | None
    business_age_max: int | None
    owner_age_max: int | None
    loan_limit: int | None  # 원 단위
    interest_rate: float | None  # 연 %
    guarantee_fee: float | None  # 연 %
    url: str
    source_url: str
    category: list[str] | None  # None=업종 무관 / []=해당 업종 없음 / [...]=해당 업종만
    source_file: str  # 시드 출처 파일명 — 재시드·대조 추적
    consultation: ConsultationMetadata | None = None  # None = 미확인
    procedure_steps: list[ProcedureStep] = field(default_factory=list)
