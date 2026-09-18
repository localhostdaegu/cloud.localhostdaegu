# 창업자금 사전상담 전환 — DB·ERD 스키마 설계

> 작성: 2026-09-18
> 근거: [데이터 확보 계획](../../2026-09-18-data-acquisition-plan.md) · [iM뱅크 전환 계획](../../2026-09-18-imbank-consultation-plan.md) · [문제 정의](../../problem.md)
> 대상: `backend/` 스키마 계층 (ORM·마이그레이션·리포지토리·ERD 문서)
> 상태: **설계 확정안.** 이 문서는 스키마를 정의하며, 실제 데이터 적재·반출 승인·은행 제휴를 완료했다는 뜻이 아니다.

## 0. 목적과 범위

**목적:** 세 계획 문서가 요구하는 데이터(금융상품 상담 메타데이터, DIP 센터 반출 결과표, 사용자 상담 세션)를 받을 자리를 DB에 미리 만들어, **데이터가 도착하면 적재만으로 동작**하게 한다.

**이번 범위:**

| 포함 | 제외 |
|---|---|
| 신규 ORM 10테이블 + alembic 단일 리비전 | 실제 데이터 적재 (센터 미반출) |
| 상품 JSON → DB 시드 CLI, 매칭 게이트웨이 DB 우선·JSON 폴백 | 프론트엔드 `sessionStorage` → API 전환 |
| consultation BC 11-file set (POST/GET 왕복) | 전환 계획 T1·T2·T4·T5 기능 구현 |
| `docs/erd.md` 신규 작성 | 기존 19테이블 컬럼 변경 (전부 additive) |

**기존 계획과의 충돌 정정:** 전환 계획 §0은 *"새 DB 테이블·로그인·은행 API·채팅 전용 서버를 이번 전환에 추가하지 않는다"*고 기록했다. 이 설계는 그중 **DB 테이블 항목만** 사용자 결정(2026-09-18)으로 덮는다. 로그인·은행 API·채팅 전용 서버는 여전히 추가하지 않는다. 전환 계획 §0에 정정 주석을 남긴다.

**설계 기준:** `backend/CLAUDE.md` §12 Fractal 11-File Set, §13 ERD 규칙(1NF→2NF→3NF, 근거 있는 역정규화, 고립 테이블 금지)을 따른다. 기존 `apps/funding/`을 11-file set 참조 구현으로 삼는다.

## 1. 현재 상태

**기존 19테이블** — 마스터 허브 `region`·`district`·`industry`(+`industry_subcategory`·`industry_source_code`), 점포 계층 `store`·`academy_course`·`tobacco_retailer`·`convenience_store`, 집계 `region_industry_metric`, 통계 `population_stat`·`rent_price`·`interest_rate`, 충격 `shock_event`(+`_industry`·`_region`), 문서 `funding_program`·`news_article`·`rag_chunk`.

**자리가 없는 데이터 5종:**

| 필요 데이터 | 근거 | 현재 |
|---|---|---|
| 금융상품 12건 + `consultation_metadata` | 전환계획 §5-2 | `data/manual/*.json` 3파일 + `lru_cache` 로더. DB 없음 |
| DIP D1 삼성카드 동·업종 소비 결과표 | 확보계획 §3 D1 | 없음 |
| DIP D2 SKT 생활인구 결과표 | 확보계획 §3 D2 | 없음 |
| 결과표의 출처·기간·산식·제한사항 | 확보계획 §6 | 어느 테이블에도 provenance 컬럼 없음 |
| 상담 프로필·최초안/현재안/선택안·상담자료 | 전환계획 §5-1·§5-3 | `sessionStorage` 전용, analysis 요청도 in-memory |

**alembic head:** `66a23fb0c6e9` (rag_chunk). 신규 리비전은 이 head 위에 단일 리비전으로 올린다.

**PostgreSQL 17** (`pgvector/pgvector:pg17`) — `UNIQUE NULLS NOT DISTINCT` 사용 가능.

## 2. `apps/product` — 금융상품 DB 정본 (4테이블)

**정본 정책 (하이브리드):** DB가 정본, `data/manual/*.json`은 시드 입력. 로더는 **DB 우선 → 행이 없으면 JSON 폴백**. 시드 CLI가 JSON → DB 멱등 upsert를 수행한다. 기존 `GET /matching` 응답 형태는 변경하지 않는다.

### 2-1. `finance_product`

```python
class FinanceProductOrm(OrmBase):
    __tablename__ = "finance_product"
    __table_args__ = (
        Index("ix_finance_product_provider_type", "provider_type"),
    )

    product_id: Mapped[str] = mapped_column(primary_key=True)   # "imbank-1" 등 수기 슬러그
    provider: Mapped[str]                                        # "iM뱅크" / "대구신용보증재단"
    provider_type: Mapped[str]                                   # bank / guarantee / policy (matcher._PRIORITY 키)
    product_name: Mapped[str]
    target: Mapped[str]                                          # 지원대상 원문 (LLM 구조화 추출 원천)
    region: Mapped[str]                                          # "전국 (iM뱅크 영업점 취급)" 등 원문
    business_age_min: Mapped[int | None]
    business_age_max: Mapped[int | None]
    owner_age_max: Mapped[int | None]
    loan_limit: Mapped[int | None]                               # 원 단위
    interest_rate: Mapped[float | None]                          # 연 % (JSON 실측: 2.5)
    guarantee_fee: Mapped[float | None]                          # 연 % (JSON 실측: 0.9)
    url: Mapped[str]
    source_url: Mapped[str]
    # JSON category의 None(업종 무관) ↔ [](해당 업종 없음) 구분 보존 — §2-2 참조
    category_restricted: Mapped[bool] = mapped_column(default=False)
    source_file: Mapped[str]                                     # 시드 출처 파일명 — 재시드·대조 추적
```

### 2-2. `finance_product_category` (M:N → `industry`)

```python
class FinanceProductCategoryOrm(OrmBase):
    __tablename__ = "finance_product_category"

    product_id: Mapped[str] = mapped_column(ForeignKey("finance_product.product_id"), primary_key=True)
    industry_id: Mapped[str] = mapped_column(ForeignKey("industry.industry_id"), primary_key=True)
```

**`category` 3상태 보존 규칙 (중요):** 현재 `matcher.match_products`는 `if p["category"] is not None and category not in p["category"]: return False`로 판정한다. 즉 `None`=업종 무관 통과, `[]`=전부 탈락이다. 이 의미를 그대로 옮긴다.

| JSON `category` | `category_restricted` | `finance_product_category` 행 | 매칭 결과 |
|---|---|---|---|
| `None` | `False` | 0건 | 모든 업종 통과 |
| `[]` | `True` | 0건 | 모든 업종 탈락 (지역한정 제외 유지) |
| `["cafe", ...]` | `True` | N건 | 해당 업종만 통과 |

로더가 DB에서 상품을 읽어 dict로 되돌릴 때 `category`를 `None` / `[]` / `[industry_id, ...]`로 복원해야 하며, **기존 `match_products` 함수는 수정하지 않는다.**

`industry_id`는 `industry` 테이블에 존재해야 한다(FK). 현재 JSON에 실제 업종 값이 없으므로 이번 시드에서는 행이 생기지 않는다. 향후 상품 원문 대조(전환계획 T3)에서 채운다. **`industry`에 없는 업종 문자열을 만나면 시드를 실패시키고 로그에 남긴다** — 조용히 버리지 않는다.

### 2-3. `product_consultation_metadata` (1:1)

전환 계획 §5-2 `ConsultationProductMetadata`의 스칼라 필드.

```python
class ProductConsultationMetadataOrm(OrmBase):
    __tablename__ = "product_consultation_metadata"

    product_id: Mapped[str] = mapped_column(ForeignKey("finance_product.product_id"), primary_key=True)
    bank_connection: Mapped[str]                       # direct / linked / unverified / none
    bank_connection_source_url: Mapped[str | None]
    business_registration_required: Mapped[bool | None]  # None = 미확인 (추정 금지)
    verified_at: Mapped[date | None]                   # 원문 확인일 — 접수 가능 보장이 아님
```

**분리 근거:** 상품 식별정보와 원문 대조 기록(확인일·연결 근거)은 수명주기가 다르다. 전환계획 §10-3은 원문 확인을 별도 산출물(`docs/research/finance-products/2026-09-18-consultation-sources.md`)로 규정한다. 행이 없으면 **미확인**으로 처리하며, 기존 12건은 이번에 메타데이터 행 없이 적재된다.

`bank_connection` 허용값은 도메인 상수 `BANK_CONNECTIONS = frozenset({"direct", "linked", "unverified", "none"})`로 두고 리포지토리 쓰기 경로에서 검증한다. DB CHECK 제약은 두지 않는다(값 추가 시 마이그레이션 유발 회피).

### 2-4. `product_procedure_step` (1:N)

§5-2의 리스트 3종(`prerequisites` / `application_steps` / `documents`)을 1NF로 저장한다.

```python
class ProductProcedureStepOrm(OrmBase):
    __tablename__ = "product_procedure_step"
    __table_args__ = (
        UniqueConstraint("product_id", "step_type", "step_order"),
    )

    step_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("finance_product.product_id"), index=True)
    step_type: Mapped[str]     # prerequisite / application_step / document
    step_order: Mapped[int]    # 1부터 — 상품별 실제 순서 보존 (전환계획 §4-2)
    description: Mapped[str]
```

**배열 컬럼 대신 판별자 1테이블을 쓰는 근거:** 세 리스트 모두 `(순서, 문자열)` 구조가 같고 접근 패턴이 동일하다. 테이블 3개로 쪼개면 §12 fractal set 3벌을 요구하게 되어 과설계다. 빈 `documents`는 행 0건이며, 화면에서는 *"공식 안내에서 준비서류 확인 필요"*로 표시한다(§5-2).

### 2-5. 로더 변경

`apps/matching/adapter/outbound/gateways/manual_product_gateway.py`의 `load_all_products()`:

- DB에서 상품을 읽어 **기존 dict 15필드와 동일한 형태**로 반환한다(`category`는 §2-2 규칙으로 복원).
- DB 행이 0건이거나 DB 연결에 실패하면 기존 JSON 경로로 폴백하고 `WARNING`을 남긴다.
- `lru_cache(maxsize=1)`는 유지한다. 테스트는 기존 관행대로 `load_all_products.cache_clear()`로 초기화한다.
- **`match_products`·`matching_router`는 수정하지 않는다.** 기존 `GET /matching` 응답이 바뀌면 회귀다.

## 3. `apps/dataset` + `apps/indicator` — 센터 반출 결과 수용 (2테이블)

확보계획 §6 *"목록·수치·출처가 함께 이동해야 한다"* / *"새 지표의 출처를 보존한다 — 카드 소비 변화율을 기존 인허가 `growth_rate`에 덮어쓰지 않고 별도 지표로 표시한다"*를 스키마로 강제한다.

### 3-1. `external_dataset`

```python
class ExternalDatasetOrm(OrmBase):
    __tablename__ = "external_dataset"

    dataset_id: Mapped[str] = mapped_column(primary_key=True)  # "dip-samsung-card-2024" 등 결정적 슬러그
    name: Mapped[str]
    provider: Mapped[str]                      # 원 제공기관: 삼성카드 / SK텔레콤 / 행정안전부
    source_channel: Mapped[str]                # dip_center / open_api / manual
    period_start: Mapped[str]                  # YYYYMM
    period_end: Mapped[str]
    aggregation_note: Mapped[str]              # 산식·집계 정의 (센터 승인 문구 그대로)
    restriction_note: Mapped[str]              # 제한사항 — 확보계획 §3의 "하지 않을 것"을 보존
    export_approved_on: Mapped[date | None]    # 반출 승인일. None = 미승인 (승인 전 적재 금지 신호)
    approval_ref: Mapped[str | None]           # 반출요청서·심사 식별자
    source_url: Mapped[str | None]
    catalog_page: Mapped[str | None]           # 설명서 쪽수 (예: "18", "54-58")
```

`restriction_note`·`aggregation_note`는 **NOT NULL**이다. 출처·산식 없이 지표를 넣을 수 없게 만드는 것이 이 테이블의 존재 이유다.

### 3-2. `regional_indicator`

```python
class RegionalIndicatorOrm(OrmBase):
    __tablename__ = "regional_indicator"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id", "region_code", "industry_id", "period", "indicator_key", "breakdown",
            postgresql_nulls_not_distinct=True,   # PG15+ — 업종/슬라이스 NULL도 중복 차단
        ),
        Index("ix_regional_indicator_key_period", "indicator_key", "period"),
        Index("ix_regional_indicator_region_industry", "region_code", "industry_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("external_dataset.dataset_id"))
    region_code: Mapped[str] = mapped_column(ForeignKey("region.region_code"))
    industry_id: Mapped[str | None] = mapped_column(ForeignKey("industry.industry_id"))  # 생활인구 등 업종 무관 지표
    period: Mapped[str]          # YYYYMM / YYYYQn / YYYY — dataset이 단위를 규정
    indicator_key: Mapped[str]   # 측정값 이름: card_amt_index / living_pop_worker 등
    breakdown: Mapped[str | None]  # 슬라이스: weekend / time_09_13 / male_20s / visitor …
    value: Mapped[float]
    unit: Mapped[str]            # 원 / 건 / % / 명 / 지수
```

**long format을 택한 근거:** 확보계획 §3은 D1·D2의 반출 형태를 *"센터가 승인하는 동등한 형식"*으로만 규정하며, 승인 결과가 컬럼 단위로 확정되지 않았다. 지표별 전용 테이블을 지금 만들면 승인 형태가 다를 때 마이그레이션을 다시 짜야 한다. long format은 D1·D2는 물론 D3~D5·후속 반출까지 **마이그레이션 없이** 수용한다.

**`region_industry_metric`과 분리하는 근거:** 확보계획 §6이 명시적으로 덮어쓰기를 금지한다. 테이블을 나누면 구조적으로 보장된다.

**적재 규칙:** `external_dataset.export_approved_on`이 `NULL`인 데이터셋에는 지표를 적재하지 않는다. 로더 CLI가 이를 검사한다.

### 3-3. CSV 로더 CLI

`apps/indicator/adapter/inbound/cli/load_regional_indicator.py` — 승인된 결과표 CSV를 읽어 `regional_indicator`에 멱등 upsert한다. **이번에 데이터는 넣지 않는다**(센터 미반출). CLI와 단위 테스트(합성 CSV 픽스처)만 만든다.

## 4. `apps/consultation` — 상담 세션 (4테이블)

**범위 구분:** 백엔드는 POST/GET 왕복이 실제로 동작하는 데까지 만든다. **프론트엔드의 `sessionStorage` → API 전환은 이번 범위가 아니다** — 전환계획 §5-3은 여전히 `sessionStorage`를 규정하며, 코드 프리즈(09-19 18:00) 전에 T2·T5 계약을 흔들지 않는다. 서버 저장 경로가 준비된 상태로 남긴다.

### 4-1. `consultation_session`

전환 계획 §5-1 `ConsultationProfile` + `ConsultationContext`의 스칼라 부분. 프로필은 세션과 1:1 필수 동반이며 모든 필드가 `session_id`에 완전 함수 종속이므로 인라인한다(3NF 위반 아님).

```python
class ConsultationSessionOrm(OrmBase):
    __tablename__ = "consultation_session"
    __table_args__ = (Index("ix_consultation_session_updated", "updated_at"),)

    session_id: Mapped[str] = mapped_column(primary_key=True)  # uuid4 hex — 로그인 없는 익명 세션키
    region_code: Mapped[str | None] = mapped_column(ForeignKey("region.region_code"))
    industry_id: Mapped[str | None] = mapped_column(ForeignKey("industry.industry_id"))
    # ConsultationProfile — 모름은 None으로 보존한다 (0·False로 변환 금지, §4-2)
    business_registered: Mapped[bool | None]
    business_age_months: Mapped[int | None]
    planned_opening_date: Mapped[date | None]
    funds_needed_by: Mapped[date | None]
    owner_age: Mapped[int | None]
    guarantee_status: Mapped[str]            # not_started / in_progress / issued / unknown
    policy_confirmation_status: Mapped[str]
    selected_plan_kind: Mapped[str | None]   # baseline / current / None
    change_reason: Mapped[str]               # 조건 변경 이유 (기본 "")
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

`region_code`·`industry_id`가 nullable인 근거: 전환계획 §1은 지역·업종 미정 사용자가 지도에서 선택한 뒤 합류하는 동선을 규정한다. 세션은 그 전에 시작될 수 있다.

**`region_code`는 행정동 10자리다.** intent 해석 결과의 `district`(구·군 5자리)를 그대로 넣지 않는다(전환계획 §1).

### 4-2. `consultation_plan`

```python
class ConsultationPlanOrm(OrmBase):
    __tablename__ = "consultation_plan"
    __table_args__ = (UniqueConstraint("session_id", "plan_kind"),)

    plan_id: Mapped[str] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("consultation_session.session_id"), index=True)
    plan_kind: Mapped[str]   # baseline(최초안) / current(현재안)

    # FinanceInput 13필드 — 원 단위 정수, 비율은 기존 FinanceInput 단위 유지
    deposit: Mapped[int]; key_money: Mapped[int]
    interior_cost: Mapped[int]; equipment_cost: Mapped[int]
    monthly_rent: Mapped[int]; monthly_payroll: Mapped[int]; monthly_insurance: Mapped[int]
    cost_ratio: Mapped[float]; fee_ratio: Mapped[float]
    equity: Mapped[int]; desired_loan: Mapped[int]; loan_rate: Mapped[float]
    expected_monthly_revenue: Mapped[int]

    # 계산 결과 — 감사·재현용 스냅샷. 리포트는 항상 서버에서 재계산한다 (§5-3)
    capex: Mapped[int]; monthly_fixed: Mapped[int]; bep_revenue: Mapped[int]
    funding_gap: Mapped[int]                 # 희망대출 반영 후 남는 부족액 (기존 산식 보존)
    reserve_months: Mapped[int]              # 현재 엔진 상수 6
    operating_reserve: Mapped[int]           # monthly_fixed × reserve_months
    total_required_funds: Mapped[int]        # capex + operating_reserve
    external_funding_need: Mapped[int]       # max(0, total_required_funds − equity)
    computed_at: Mapped[datetime]
```

**결과를 저장하는 근거와 한계:** §5-3은 *"클라이언트가 보낸 계산 결과를 리포트의 기준으로 삼지 않는다"*고 규정한다. 저장된 8필드는 **감사·재현용 스냅샷**이며 리포트 생성 경로가 이 값을 읽어서는 안 된다. 리포지토리 docstring에 이 제약을 명시한다.

`scenarios`·`stress`는 13필드에서 파생되므로 저장하지 않는다(3NF).

**`reserve_months`·`operating_reserve`·`total_required_funds`·`external_funding_need`는 전환계획 §4-1이 정의한 신규 값이다.** 이번 범위에서 재무 엔진(`engine.py`)은 수정하지 않으므로, 이 컬럼들은 T1 구현 전까지 쓰기 경로에서 호출자가 계산해 넣거나 0으로 남는다. **T1이 엔진에 값을 추가하면 그대로 연결된다.**

### 4-3. `consultation_note`

§5-1 `assumptions` / `open_questions`의 1NF 형태.

```python
class ConsultationNoteOrm(OrmBase):
    __tablename__ = "consultation_note"
    __table_args__ = (UniqueConstraint("session_id", "note_type", "note_order"),)

    note_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("consultation_session.session_id"), index=True)
    note_type: Mapped[str]    # assumption(가정·출처) / open_question(미확인 항목)
    note_order: Mapped[int]
    content: Mapped[str]
```

§5-1: *"단계폼에서 '모름'을 선택한 사실이 숫자 가정으로 바뀌면서 사라지지 않게 한다."* 이 테이블이 그 기록의 저장소다.

### 4-4. `consultation_document`

```python
class ConsultationDocumentOrm(OrmBase):
    __tablename__ = "consultation_document"
    __table_args__ = (Index("ix_consultation_document_session_generated", "session_id", "generated_at"),)

    document_id: Mapped[str] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("consultation_session.session_id"))
    plan_id: Mapped[str] = mapped_column(ForeignKey("consultation_plan.plan_id"))  # 어느 선택안으로 만든 자료인가
    purpose: Mapped[str]              # review(AI 계획 점검) / handoff(최종 상담자료)
    generated_at: Mapped[datetime]
    content_markdown: Mapped[str]
    content_hash: Mapped[str]         # sha256(content_markdown) — 변경 여부 확인용
```

`content_hash`는 problem.md §8-1의 *"블록체인 리포트 해시 앵커링 — 선택·후속 항목"*에 대비한 1컬럼이다. **이번에 앵커링을 구현하지 않으며**, 해시 존재를 블록체인 연동으로 설명하지 않는다.

### 4-5. API

`apps/consultation/adapter/inbound/api/v1/consultation_router.py`, prefix `/consultation`:

| 메서드 | 경로 | 역할 |
|---|---|---|
| GET | `/consultation/myself` | 배선 검증 (§12 규칙 — 비즈니스 엔드포인트보다 먼저) |
| POST | `/consultation` | 세션 생성 → `session_id` 반환 |
| GET | `/consultation/{session_id}` | 세션 + 계획 + 노트 조회 |
| PUT | `/consultation/{session_id}/plans/{plan_kind}` | 계획안 저장 (baseline/current 멱등 upsert) |

`main.py`에는 `include_router` **추가만** 한다(전환계획 §0, handoff §0-6 공동 파일 규칙).

## 5. `docs/erd.md` 신규 작성

**현재 `docs/erd.md`는 존재하지 않는다.** `convenience_store_orm.py`·`tobacco_retailer_orm.py`·`rent_price_orm.py`·`population_stat_orm.py`·`interest_rate_orm.py`·`region_industry_metric_orm.py` 등 6곳 이상의 docstring이 이 파일을 참조하지만 원천 프로젝트(Metabole/beyondfacade) 유산이다.

신규 `docs/erd.md`에 담을 것:

1. **전체 29테이블 mermaid `erDiagram`** — 마스터 허브 / 점포·집계 / 통계 / 충격 / 문서·RAG / **금융상품(신규)** / **외부 데이터셋·지표(신규)** / **상담(신규)** 그룹으로 구획.
2. **연결(엣지) 표** — 테이블별 FK 대상과 근거. §13 "고립 테이블 금지" 충족 증명.
3. **역정규화 근거 표** — `region_industry_metric`(집계 계층), `convenience_store.brand`, `consultation_plan`의 결과 8필드(감사 스냅샷), `finance_product.category_restricted`.
4. **신규 테이블의 설계 판단** — long format 선택 이유, `category` 3상태 보존, 상품 메타데이터 분리, `NULLS NOT DISTINCT`.
5. **미연결 테이블 표기** — `shock_event`·`shock_event_region`·`tobacco_retailer`·`convenience_store`·`academy_course`·`rent_price`는 적재/스키마는 있으나 새 창업자금 동선에 연결되지 않았음을 명시(problem.md §8-1의 "자료 적재 / 계산 경로 연결 / 화면 표시" 구분을 ERD에도 반영).

## 6. 작업 분할과 검증

의존: **A · B · C 병렬 → D → E**

| # | 작업 | 산출물 | 검증 |
|---|---|---|---|
| A | `apps/product` BC | ORM 4, entity, orm_mapper, repository, port, dto, 시드 CLI, `manual_product_gateway` DB 폴백 | `pytest tests/test_matching.py tests/test_product_*.py -q` |
| B | `apps/dataset` + `apps/indicator` BC | ORM 2, entity, orm_mapper, repository, port, CSV 로더 CLI | `pytest tests/test_indicator_*.py -q` |
| C | `apps/consultation` BC | ORM 4, 11-file set, 라우터 4엔드포인트, `main.py` 라우터 추가 | `pytest tests/test_consultation_*.py -q` |
| D | alembic 단일 리비전 | `migrations/env.py`에 신규 ORM 10개 등록 + `66a23fb0c6e9` 위 리비전 1개 | `alembic upgrade head` 후 `alembic check`가 빈 diff |
| E | `docs/erd.md` + 문서 정합 | ERD 문서, 전환계획 §0 정정, `docs/handoff.md`·`docs/jekyll.md` 기록 | 문서 링크·표 검토 |

**전체 검증 (E 이후):**

```bash
# backend/
.venv/bin/python -m pytest tests/ -q
```

테스트는 `tests/conftest.py`가 `<db>_test` DB를 만들고 `alembic upgrade head` + 마스터 시드까지 수행한다. 개발 DB(포트 5437)를 건드리지 않는다.

## 7. 인수 기준

- [ ] 기존 19테이블의 컬럼·인덱스가 하나도 변경되지 않는다 (마이그레이션 diff가 전부 `create_table`/`create_index`).
- [ ] `alembic upgrade head` 후 `alembic check`가 빈 diff를 반환한다 (ORM ↔ 마이그레이션 일치).
- [ ] `GET /matching` 응답이 시드 전후·DB 폴백 경로에서 동일하다. `match_products`는 수정되지 않았다.
- [ ] `category`의 `None`·`[]`·`["x"]` 3상태가 DB 왕복 후에도 구분된다 (회귀 테스트 필수).
- [ ] `industry`에 없는 업종 문자열은 시드를 실패시킨다 (조용히 버리지 않음).
- [ ] `export_approved_on`이 `NULL`인 데이터셋에는 지표를 적재할 수 없다.
- [ ] `regional_indicator`에 `industry_id`·`breakdown`이 NULL인 행을 두 번 넣으면 UNIQUE 위반이 발생한다.
- [ ] `consultation_session`의 `business_registered`·`owner_age` 미입력이 `False`·`0`이 아니라 `None`으로 왕복한다.
- [ ] `POST /consultation` → `PUT .../plans/current` → `GET /consultation/{id}`가 실제 DB에 대해 동작한다.
- [ ] `docs/erd.md`가 29테이블 전부를 포함하고, 고립 테이블이 0건이다.
- [ ] `backend/.venv/bin/python -m pytest tests/ -q` 전체 통과. 실패 시 원인을 환경·기존 결함과 구분해 기록한다.

## 8. 하지 않는 것

- 기존 19테이블 컬럼 변경·삭제. `shock_*`·`tobacco_retailer`·`convenience_store`·`academy_course`·`rent_price`는 새 동선과 무관하지만 삭제 대상이 아니다.
- 재무 엔진(`engine.py`) 수정 — 전환계획 T1의 범위다.
- 프론트엔드 변경 — `frontend/src/shared/api/types.ts`를 포함해 이번 범위에 없다.
- 실제 데이터 적재 — DIP 센터 D1·D2는 **미신청·미확보**다. 스키마 존재를 데이터 확보로 표현하지 않는다.
- 로그인·계정·은행 API·블록체인 앵커링.
