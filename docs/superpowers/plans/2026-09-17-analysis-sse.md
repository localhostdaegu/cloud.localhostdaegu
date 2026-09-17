# AI 리포트 `/analysis` SSE Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 백엔드에 `POST /analysis` + `GET /analysis/{id}/events`(SSE)를 추가해, 상권 지표·위험도(Feature) + 재무 시뮬레이션·상품 매칭(Finance) + RAG 문서를 Gemini로 해석한 리포트를 프론트 `AgentEvent` 계약 그대로 스트리밍하고, 프론트 AI 분석 탭을 mock에서 실백엔드로 전환한다.

**Architecture:** 신규 Bounded Context `backend/apps/analysis/`(ERD 테이블 없음 — metric의 risk처럼 파생 계산이라 ORM·repository 없이 헥사고널 레이어만 둔다). 인터랙터가 오케스트레이터 역할: 에이전트 3종(market·shock·funding, **Strategy**)이 포트로 데이터를 모아 컨텍스트를 채우고, 리포트 섹션 5종(**Strategy + Template Method**)이 "코드가 쓰는 첫머리(수치) → LLM 해석 스트림" 순으로 `report_delta`를 낸다. 수치는 전부 코드가 포맷하고 LLM은 해석만 한다. 타 BC(master·metric·rag·finance·matching) 접근은 outbound 어댑터에서만 한다.

**Tech Stack:** FastAPI 0.141 `StreamingResponse`(text/event-stream), google-genai 1.29 `generate_content_stream`, 기존 RAG 검색 유스케이스(pgvector, gemini-embedding-001), pytest(Fake 포트), Next.js 16 + vitest, Playwright headless.

**Spec:** 별도 스펙 없음 — 근거 문서: `docs/handoff.md` §4-1, `docs/daegunavi.md` §4④·§5.4·§7, 프론트 계약 `frontend/src/shared/api/types.ts`(`AgentEvent`), mock 구현 `frontend/src/app/api/mock/analysis/route.ts`·`frontend/src/app/api/mock/analysis/[id]/events/route.ts`·`frontend/src/app/api/mock/fixtures.ts`(`agentEventScript`), 소비자 `frontend/src/features/agent-report/`.

## Global Constraints

- 문서·주석·커밋 메시지는 한국어. 커밋 메시지 끝에 `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`.
- `backend/` 작업은 `backend/CLAUDE.md`(헥사고널·TDD·ISP 포트), 모든 작업은 루트 `CLAUDE.md`(GoF: 타입/상태 분기는 Strategy·State, `isinstance` 금지) 준수.
- `domain/`·`app/use_cases/`에서 FastAPI·SQLAlchemy·google-genai import 금지. 타 BC import는 `adapter/outbound/`와 `dependencies/`에서만.
- **LLM 수치 계산 금지**(daegunavi §7): 점수·금액·비율은 코드가 포맷해 리포트에 직접 쓰고, 프롬프트에는 이미 계산된 값만 넣는다.
- 시스템 프롬프트 지역명은 `core.matrix.grid_region_config.REGION_NAME`("대구")에서 주입 — 서울 문구 금지.
- **RAG 질의 임베더는 `provider="gemini"` 필수.** `rag_chunk` 3,560건 전부 `embedded_by=gemini-embedding-001`(2026-09-17 실측). `get_rag_search_use_case()` 기본값 `ollama`로 질의하면 벡터 공간이 달라 검색이 무의미해진다.
- 테스트에서 LLM·RAG·DB는 Fake 포트로 대체. **실 Gemini 생성 호출은 Task 10에서만.**
- 백엔드 테스트: `cd backend && .venv/bin/python -m pytest ...` (conftest가 `localhostdaegu_test` DB를 자동 준비 — docker db 기동 필요). 기준선 210 passed / 1 skipped.
- 프론트 테스트: `cd frontend && npx vitest run` (기준선 84 passed), `npx tsc --noEmit`.
- 실행 중인 서버(백엔드 :8300 uvicorn — `--reload` 아님, 프론트 :3300 next dev)는 Task 10의 **사용자 승인 단계 전까지** 재시작·종료 금지. 브라우저는 headless Playwright만, 시각 브라우저 열기 금지.
- 건드리지 말 것: `data/manual/`, `docs/research/`(다른 에이전트 작업 중), `docs/application_form.md`, `frontend/docs/`(미추적 사용자 파일). `git add`는 태스크에 적힌 파일만 — `git add -A`/`git add .` 금지.
- 범위 밖(YAGNI): 리포트 해시 앵커링, PDF, 리포트 영속 저장, Redis 저장소, mock fixture 문구 수정, 시뮬레이터 → AI 리포트 CTA.

## SSE 계약 (프론트 기준 — 변경 금지)

```
POST {API_BASE}/analysis        body {region: string, industry: string, question?: string}
                                → 200 {analysis_id: string}
GET  {API_BASE}/analysis/{analysis_id}/events   (EventSource)
                                → text/event-stream, 각 이벤트:
                                  event: <type>\ndata: <JSON(AgentEvent)>\n\n
```

```ts
type AgentName = "orchestrator" | "market" | "shock" | "funding";
type AgentEvent =
  | { type: "agent_status"; agent: AgentName; status: "running" | "done" | "error" }
  | { type: "tool_call"; agent: AgentName; tool: string; summary: string }
  | { type: "report_delta"; section: string; markdown: string }   // 같은 section이면 이어붙임
  | { type: "report_done"; report_id: string; citations: unknown[] };
```

- 프론트는 `agent_status`·`tool_call`·`report_delta`·`report_done` 4개 이름만 `addEventListener`로 듣는다(이름 없는 `message` 이벤트는 무시됨). `report_done` 수신 시 스트림을 닫는다. `onerror`(연결 종료 포함) 시 에러 표시 후 닫는다 → **서버는 반드시 `report_done`으로 끝내야 한다.**
- `ReportView`는 section `verdict → market → shock → funding → calculator` 순서로, 값이 있는 것만 렌더한다.
- `citations` 원소는 `{title: string, url: string, grade: "fact" | "signal"}`이어야 화면에 나온다(그 외 모양은 필터링됨).
- 이벤트 순서(mock과 동일): `orchestrator running` → 에이전트마다 `running → tool_call* → done` → `report_delta*` → `orchestrator done` → `report_done`.
- 백엔드 확장(프론트 미사용, 하위 호환): POST body에 선택 `finance`(`/finance/simulate` 요청과 같은 13필드). 있으면 시뮬레이션·`calculator` 섹션이 추가되고 매칭에 funding_gap을 쓴다. 없으면 funding_gap=0.
- 알 수 없는/이미 소비된 `analysis_id` → 404 `{"error":{"code":"ANALYSIS_NOT_FOUND","message":...}}`. 요청은 GET 1회에 소비된다(EventSource 재연결로 LLM이 중복 호출되지 않게).

## File Structure

```
backend/apps/analysis/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── agent_event.py          # AgentEvent 4종 + Citation — to_payload()가 프론트 JSON과 1:1
│   ├── analysis_context.py     # AnalysisRequest, MarketSnapshot, EvidenceDoc, SimulationSummary, MatchedProduct, AnalysisContext
│   ├── errors.py               # AnalysisNotFoundError
│   └── report_text.py          # 순수 텍스트 빌더: 첫머리(수치)·프롬프트·계산표·인용
├── app/
│   ├── __init__.py
│   ├── ports/__init__.py
│   ├── ports/input/__init__.py
│   ├── ports/input/analysis_use_case.py      # AnalysisUseCase(start, stream)
│   ├── ports/output/__init__.py
│   ├── ports/output/analysis_port.py         # MarketDataPort, EvidenceSearchPort, SimulationPort, ProductMatchingPort, ReportWriterPort, AnalysisRequestStorePort
│   ├── use_cases/__init__.py
│   ├── use_cases/analysis_agents.py          # AnalysisAgent(Strategy) + Market/Shock/FundingAgent
│   ├── use_cases/report_sections.py          # ReportSection(Strategy) + InterpretedSection(Template Method) + 5 섹션
│   └── use_cases/analysis_interactor.py      # 오케스트레이터
├── adapter/
│   ├── __init__.py
│   ├── inbound/__init__.py
│   ├── inbound/api/__init__.py
│   ├── inbound/api/schemas/__init__.py
│   ├── inbound/api/schemas/analysis_schema.py
│   ├── inbound/api/v1/__init__.py
│   ├── inbound/api/v1/analysis_router.py
│   ├── inbound/mappers/__init__.py
│   ├── inbound/mappers/analysis_mapper.py    # schema→AnalysisRequest, AgentEvent→SSE 문자열
│   ├── outbound/__init__.py
│   ├── outbound/gateways/__init__.py
│   ├── outbound/gateways/market_data_gateway.py      # master region summary + metric risk (ACL)
│   ├── outbound/gateways/evidence_search_gateway.py  # rag 검색 → EvidenceDoc
│   ├── outbound/gateways/finance_gateways.py         # finance engine + matching domain
│   ├── outbound/llm/__init__.py
│   ├── outbound/llm/gemini_report_writer.py
│   ├── outbound/stores/__init__.py
│   └── outbound/stores/in_memory_analysis_request_store.py
└── dependencies/
    ├── __init__.py
    └── analysis_dependencies.py              # Composition Root (lru_cache 싱글턴)

backend/core/matrix/grid_keymaker_secret_manager.py   # gemini_report_model 설정 추가
backend/main.py                                       # analysis_router 등록
backend/tests/analysis_fakes.py                       # 테스트 공용 샘플·Fake 포트
backend/tests/test_analysis_domain.py
backend/tests/test_analysis_report_text.py
backend/tests/test_analysis_agents.py
backend/tests/test_analysis_sections.py
backend/tests/test_analysis_interactor.py
backend/tests/test_analysis_gateways.py
backend/tests/test_analysis_gemini_writer.py
backend/tests/test_analysis_router.py
backend/tests/test_settings_env_files.py              # 설정 필드 테스트 1건 추가

frontend/src/features/agent-report/hooks/use-agent-report.ts       # mock 고정 베이스 제거 → config.apiBase
frontend/src/features/agent-report/hooks/use-agent-report.test.ts
frontend/tests/analysis.cjs                                        # headless E2E (Task 10)
```

모든 `__init__.py`는 빈 파일(기존 BC와 동일).

---

### Task 1: 도메인 — 이벤트 계약·분석 컨텍스트

**Files:**
- Create: `backend/apps/analysis/__init__.py`, `backend/apps/analysis/domain/__init__.py` (빈 파일)
- Create: `backend/apps/analysis/domain/agent_event.py`
- Create: `backend/apps/analysis/domain/analysis_context.py`
- Create: `backend/apps/analysis/domain/errors.py`
- Create: `backend/tests/analysis_fakes.py`
- Test: `backend/tests/test_analysis_domain.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `Citation(title: str, url: str, grade: str)`
  - `AgentEvent.to_payload() -> dict`, 하위 `AgentStatusEvent(agent, status)`, `ToolCallEvent(agent, tool, summary)`, `ReportDeltaEvent(section, markdown)`, `ReportDoneEvent(report_id, citations: list[Citation])`; 클래스 상수 `TYPE`
  - `AnalysisRequest(region, industry, question=None, finance: dict | None = None)`
  - `MetricCard(label, value)`, `RiskView(score, grade, components)`, `MarketSnapshot(region_name, industry_name, cards, risk)`
  - `EvidenceDoc(source_type, title, snippet, url, org, published_at: str | None)`
  - `ScenarioLine(name, monthly_revenue, operating_profit, payback_months)`, `SimulationSummary(capex, monthly_fixed, bep_revenue, funding_gap, scenarios)`
  - `MatchedProduct(provider, product_name, loan_limit, interest_rate)`
  - `AnalysisContext(analysis_id, request, market=None, news=[], funding_docs=[], products=[], simulation=None)` + 프로퍼티 `region_label`, `industry_label`, `risk`, `cards`, `funding_gap`
  - `AnalysisNotFoundError(Exception)`
  - `tests/analysis_fakes.py`: `MARKET`, `NEWS_DOC`, `FUNDING_DOC`, `PRODUCT`, `SIMULATION`, `FINANCE`, `full_context()`

- [ ] **Step 1: 공용 샘플 모듈 작성** — `backend/tests/analysis_fakes.py`

```python
"""analysis BC 테스트 공용 샘플·Fake 포트 — DB·네트워크·LLM 없음.

SIMULATION 수치는 FINANCE 입력을 apps.finance.domain.engine.simulate로 계산한 실측값(2026-09-17).
"""

from apps.analysis.domain.analysis_context import (
    AnalysisContext,
    AnalysisRequest,
    EvidenceDoc,
    MarketSnapshot,
    MatchedProduct,
    MetricCard,
    RiskView,
    ScenarioLine,
    SimulationSummary,
)

MARKET = MarketSnapshot(
    region_name="대신동",
    industry_name="카페",
    cards=[MetricCard("점포수", "120개"), MetricCard("폐업률", "6.4%"), MetricCard("성장률", "+2.1%")],
    risk=RiskView(score=72.5, grade="red", components={"closure": 30.0, "density": 28.5, "growth": 14.0}),
)
NEWS_DOC = EvidenceDoc(
    source_type="news",
    title="원두값 급등에 카페 원가 압박",
    snippet="원두 선물 가격이 전년 대비 8% 상승했다.",
    url="https://news.example/1",
    org="매일신문",
    published_at="2026-09-10",
)
FUNDING_DOC = EvidenceDoc(
    source_type="funding",
    title="대구 청년창업 지원사업",
    snippet="만 39세 이하 예비창업자 대상 최대 5천만원",
    url="https://funding.example/1",
    org="대구광역시",
    published_at="2026-09-01",
)
PRODUCT = MatchedProduct(
    provider="대구신용보증재단", product_name="소상공인 창업 보증", loan_limit=50_000_000, interest_rate=3.2
)
FINANCE = {
    "deposit": 10_000_000,
    "key_money": 0,
    "interior_cost": 20_000_000,
    "equipment_cost": 10_000_000,
    "monthly_rent": 1_000_000,
    "monthly_payroll": 2_000_000,
    "monthly_insurance": 100_000,
    "cost_ratio": 0.35,
    "fee_ratio": 0.05,
    "equity": 30_000_000,
    "desired_loan": 10_000_000,
    "loan_rate": 0.05,
    "expected_monthly_revenue": 8_000_000,
}
SIMULATION = SimulationSummary(
    capex=40_000_000,
    monthly_fixed=3_141_666,
    bep_revenue=5_236_109,
    funding_gap=18_849_996,
    scenarios=[
        ScenarioLine("비관", 4_800_000, -261_665, None),
        ScenarioLine("기준", 8_000_000, 1_658_335, 24.1),
        ScenarioLine("낙관", 12_800_000, 4_538_334, 8.8),
    ],
)


def full_context() -> AnalysisContext:
    """에이전트 수집이 모두 끝난 상태의 컨텍스트."""
    return AnalysisContext(
        analysis_id="abc",
        request=AnalysisRequest(region="2711059500", industry="cafe", question="원두값 오르면?", finance=FINANCE),
        market=MARKET,
        news=[NEWS_DOC],
        funding_docs=[FUNDING_DOC],
        products=[PRODUCT],
        simulation=SIMULATION,
    )
```

- [ ] **Step 2: 실패 테스트 작성** — `backend/tests/test_analysis_domain.py`

```python
"""analysis 도메인 — SSE 페이로드가 프론트 AgentEvent(types.ts)와 1:1인지, 컨텍스트 라벨 폴백."""

from apps.analysis.domain.agent_event import (
    AgentStatusEvent,
    Citation,
    ReportDeltaEvent,
    ReportDoneEvent,
    ToolCallEvent,
)
from apps.analysis.domain.analysis_context import AnalysisContext, AnalysisRequest
from tests.analysis_fakes import MARKET, SIMULATION


def test_agent_status_payload_matches_frontend_contract():
    assert AgentStatusEvent(agent="market", status="running").to_payload() == {
        "type": "agent_status",
        "agent": "market",
        "status": "running",
    }


def test_tool_call_payload_matches_frontend_contract():
    assert ToolCallEvent(agent="shock", tool="news_search", summary="뉴스 RAG 검색 — 3건").to_payload() == {
        "type": "tool_call",
        "agent": "shock",
        "tool": "news_search",
        "summary": "뉴스 RAG 검색 — 3건",
    }


def test_report_delta_payload_matches_frontend_contract():
    assert ReportDeltaEvent(section="verdict", markdown="### 종합 진단").to_payload() == {
        "type": "report_delta",
        "section": "verdict",
        "markdown": "### 종합 진단",
    }


def test_report_done_payload_serializes_citations_as_objects():
    event = ReportDoneEvent(report_id="abc", citations=[Citation(title="공고", url="https://x", grade="fact")])
    assert event.to_payload() == {
        "type": "report_done",
        "report_id": "abc",
        "citations": [{"title": "공고", "url": "https://x", "grade": "fact"}],
    }


def _bare_context() -> AnalysisContext:
    return AnalysisContext(analysis_id="abc", request=AnalysisRequest(region="2711059500", industry="cafe"))


def test_context_labels_fall_back_to_codes_without_market():
    ctx = _bare_context()
    assert (ctx.region_label, ctx.industry_label) == ("2711059500", "cafe")
    assert ctx.risk is None
    assert ctx.cards == []


def test_context_labels_use_market_names():
    ctx = _bare_context()
    ctx.market = MARKET
    assert (ctx.region_label, ctx.industry_label) == ("대신동", "카페")
    assert ctx.risk == MARKET.risk
    assert ctx.cards == MARKET.cards


def test_context_funding_gap_is_zero_without_simulation_and_uses_simulation_when_present():
    ctx = _bare_context()
    assert ctx.funding_gap == 0
    ctx.simulation = SIMULATION
    assert ctx.funding_gap == 18_849_996
```

- [ ] **Step 3: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analysis_domain.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.analysis'`

- [ ] **Step 4: 구현** — 빈 `__init__.py` 2개 생성 후 아래 3파일

`backend/apps/analysis/domain/agent_event.py`
```python
"""SSE 이벤트 계약 — frontend/src/shared/api/types.ts 의 AgentEvent 와 필드명·값이 1:1.

각 이벤트가 자기 type 을 안다(분기 없이 to_payload 한 곳에서 직렬화).
"""

from dataclasses import asdict, dataclass, field
from typing import ClassVar


@dataclass(frozen=True)
class Citation:
    title: str
    url: str
    grade: str  # fact | signal — 프론트 GradeBadge 계약


@dataclass(frozen=True)
class AgentEvent:
    TYPE: ClassVar[str] = ""

    def to_payload(self) -> dict:
        return {"type": self.TYPE, **asdict(self)}


@dataclass(frozen=True)
class AgentStatusEvent(AgentEvent):
    TYPE: ClassVar[str] = "agent_status"
    agent: str
    status: str  # running | done | error


@dataclass(frozen=True)
class ToolCallEvent(AgentEvent):
    TYPE: ClassVar[str] = "tool_call"
    agent: str
    tool: str
    summary: str


@dataclass(frozen=True)
class ReportDeltaEvent(AgentEvent):
    TYPE: ClassVar[str] = "report_delta"
    section: str
    markdown: str


@dataclass(frozen=True)
class ReportDoneEvent(AgentEvent):
    TYPE: ClassVar[str] = "report_done"
    report_id: str
    citations: list[Citation] = field(default_factory=list)
```

`backend/apps/analysis/domain/analysis_context.py`
```python
"""분석 요청·수집 결과 값 객체와 오케스트레이션 컨텍스트 (프레임워크·타 BC import 금지)."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AnalysisRequest:
    region: str  # 행정동 region_code
    industry: str  # industry_id
    question: str | None = None
    finance: dict | None = None  # /finance/simulate 요청 13필드(원 단위) — 있으면 시뮬레이션·계산표 포함


@dataclass(frozen=True)
class MetricCard:
    label: str
    value: str


@dataclass(frozen=True)
class RiskView:
    score: float
    grade: str  # red | yellow | green
    components: dict[str, float]  # closure·density·growth


@dataclass(frozen=True)
class MarketSnapshot:
    region_name: str
    industry_name: str
    cards: list[MetricCard]
    risk: RiskView | None


@dataclass(frozen=True)
class EvidenceDoc:
    source_type: str  # funding | news
    title: str
    snippet: str
    url: str | None
    org: str | None
    published_at: str | None  # YYYY-MM-DD


@dataclass(frozen=True)
class ScenarioLine:
    name: str
    monthly_revenue: int
    operating_profit: int
    payback_months: float | None


@dataclass(frozen=True)
class SimulationSummary:
    capex: int
    monthly_fixed: int
    bep_revenue: int
    funding_gap: int
    scenarios: list[ScenarioLine]


@dataclass(frozen=True)
class MatchedProduct:
    provider: str
    product_name: str
    loan_limit: int
    interest_rate: float


@dataclass
class AnalysisContext:
    """오케스트레이션 1회분 작업 공간 — 에이전트가 채우고 리포트 섹션이 읽는다."""

    analysis_id: str
    request: AnalysisRequest
    market: MarketSnapshot | None = None
    news: list[EvidenceDoc] = field(default_factory=list)
    funding_docs: list[EvidenceDoc] = field(default_factory=list)
    products: list[MatchedProduct] = field(default_factory=list)
    simulation: SimulationSummary | None = None

    @property
    def region_label(self) -> str:
        return self.market.region_name if self.market else self.request.region

    @property
    def industry_label(self) -> str:
        return self.market.industry_name if self.market else self.request.industry

    @property
    def risk(self) -> RiskView | None:
        return self.market.risk if self.market else None

    @property
    def cards(self) -> list[MetricCard]:
        return self.market.cards if self.market else []

    @property
    def funding_gap(self) -> int:
        return self.simulation.funding_gap if self.simulation else 0
```

`backend/apps/analysis/domain/errors.py`
```python
"""analysis BC 도메인 예외 — 라우터가 잡아 404 에러 바디로 변환한다."""


class AnalysisNotFoundError(Exception):
    """존재하지 않거나 이미 스트림으로 소비된 analysis_id."""
```

- [ ] **Step 5: 통과 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analysis_domain.py -q`
Expected: `7 passed`

- [ ] **Step 6: 커밋**

```bash
git add backend/apps/analysis/__init__.py backend/apps/analysis/domain/ backend/tests/analysis_fakes.py backend/tests/test_analysis_domain.py
git commit -m "feat(analysis): SSE 이벤트 계약·분석 컨텍스트 도메인

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: 도메인 — 리포트 텍스트 빌더 (수치는 코드가 쓴다)

**Files:**
- Create: `backend/apps/analysis/domain/report_text.py`
- Test: `backend/tests/test_analysis_report_text.py`

**Interfaces:**
- Consumes: Task 1의 `AnalysisContext`, `EvidenceDoc`, `SimulationSummary`, `Citation`, `tests/analysis_fakes`
- Produces (모두 순수 함수, 반환 `str` — 마지막만 예외):
  - `FALLBACK_MARKDOWN: str`
  - `system_instruction(region_name: str) -> str`
  - `verdict_lead(ctx)`, `market_lead(ctx)`, `shock_lead(ctx)`, `funding_lead(ctx)`
  - `verdict_prompt(ctx)`, `market_prompt(ctx)`, `shock_prompt(ctx)`, `funding_prompt(ctx)`
  - `market_facts(ctx)`, `finance_facts(ctx)`, `products_text(ctx)`, `format_docs(docs: list[EvidenceDoc])`
  - `calculator_markdown(sim: SimulationSummary) -> str`
  - `citations_from(ctx) -> list[Citation]`

- [ ] **Step 1: 실패 테스트 작성** — `backend/tests/test_analysis_report_text.py`

```python
"""리포트 텍스트 빌더 — 수치 포맷·프롬프트 구성·인용 목록 (LLM 없음)."""

from dataclasses import replace

from apps.analysis.domain.agent_event import Citation
from apps.analysis.domain.analysis_context import AnalysisContext, AnalysisRequest, EvidenceDoc
from apps.analysis.domain.report_text import (
    calculator_markdown,
    citations_from,
    finance_facts,
    format_docs,
    funding_lead,
    funding_prompt,
    market_lead,
    shock_prompt,
    system_instruction,
    verdict_lead,
)
from tests.analysis_fakes import FUNDING_DOC, NEWS_DOC, SIMULATION, full_context


def _bare_context() -> AnalysisContext:
    return AnalysisContext(analysis_id="abc", request=AnalysisRequest(region="2711059500", industry="cafe"))


def test_system_instruction_injects_region_and_forbids_calculation():
    text = system_instruction("대구")
    assert "대구" in text
    assert "계산하거나 추정하지 않는다" in text
    assert "서울" not in text


def test_verdict_lead_is_written_by_code_with_score_and_grade_label():
    assert verdict_lead(full_context()) == "### 종합 진단\n\n**대신동 카페 · 위험도 72.5점 — 진입 주의**\n\n"


def test_verdict_lead_without_market_data_says_no_risk_data():
    assert verdict_lead(_bare_context()) == "### 종합 진단\n\n**2711059500 cafe · 위험도 데이터 없음**\n\n"


def test_market_lead_renders_cards_and_risk_components_table():
    text = market_lead(full_context())
    assert text.startswith("### 상권 진단\n\n| 지표 | 값 |\n|---|---|\n")
    assert "| 폐업률 | 6.4% |" in text
    assert "| 위험도 구성(폐업·밀집·성장) | 30.0 · 28.5 · 14.0 |" in text


def test_market_lead_without_data_says_no_metrics():
    assert market_lead(_bare_context()) == "### 상권 진단\n\n_상권 지표 데이터가 없습니다._\n\n"


def test_funding_lead_lists_matched_products_or_none():
    assert "- 대구신용보증재단 소상공인 창업 보증: 한도 50,000,000원, 금리 3.2%" in funding_lead(full_context())
    assert "- 조건에 맞는 상품 없음" in funding_lead(_bare_context())


def test_calculator_markdown_formats_scenarios_and_unrecoverable_payback():
    text = calculator_markdown(SIMULATION)
    assert text.startswith("### 재무 시뮬레이션\n\n")
    assert "부족 자금 18,849,996원" in text
    assert "| 비관 | 4,800,000원 | -261,665원 | 회수 불가 |" in text
    assert "| 기준 | 8,000,000원 | 1,658,335원 | 24.1개월 |" in text


def test_finance_facts_without_simulation():
    assert finance_facts(_bare_context()) == "재무 시뮬레이션: 입력 없음"


def test_format_docs_numbers_documents_and_handles_empty():
    assert format_docs([]) == "(관련 문서 없음)"
    assert format_docs([NEWS_DOC]) == "[1] 원두값 급등에 카페 원가 압박 (매일신문, 2026-09-10)\n원두 선물 가격이 전년 대비 8% 상승했다."


def test_shock_prompt_contains_numbered_news_and_user_question():
    prompt = shock_prompt(full_context())
    assert "[1] 원두값 급등에 카페 원가 압박 (매일신문, 2026-09-10)" in prompt
    assert "사용자 추가 질문(답변에 반영): 원두값 오르면?" in prompt


def test_funding_prompt_contains_precomputed_gap_and_products():
    prompt = funding_prompt(full_context())
    assert "부족 자금 18,849,996원" in prompt
    assert "- 대구신용보증재단 소상공인 창업 보증: 한도 50,000,000원, 금리 3.2%" in prompt
    assert "[1] 대구 청년창업 지원사업 (대구광역시, 2026-09-01)" in prompt


def test_citations_dedupe_by_url_skip_missing_url_and_grade_by_source():
    ctx = full_context()
    ctx.news = [NEWS_DOC, replace(NEWS_DOC, title="중복"), replace(NEWS_DOC, url=None, title="URL 없음")]
    assert citations_from(ctx) == [
        Citation(title=FUNDING_DOC.title, url="https://funding.example/1", grade="fact"),
        Citation(title=NEWS_DOC.title, url="https://news.example/1", grade="signal"),
    ]
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analysis_report_text.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.analysis.domain.report_text'`

- [ ] **Step 3: 구현** — `backend/apps/analysis/domain/report_text.py`

```python
"""리포트 텍스트 빌더 (순수 함수) — "결론 첫 줄은 LLM이 아니라 코드가 쓴다".

수치는 전부 여기서 포맷해 리포트에 직접 쓰고, LLM 프롬프트에는 이미 계산된 값만 넣는다
(LLM 수치 계산 금지 — docs/daegunavi.md §7).
"""

from apps.analysis.domain.agent_event import Citation
from apps.analysis.domain.analysis_context import AnalysisContext, EvidenceDoc, SimulationSummary

_GRADE_LABEL = {"red": "진입 주의", "yellow": "보통", "green": "양호"}
_CITATION_GRADE = {"funding": "fact", "news": "signal"}  # 공고=확인된 사실, 뉴스=참고 신호

FALLBACK_MARKDOWN = "\n\n_AI 해석을 생성하지 못했습니다. 위 수치와 참고 자료를 확인해 주세요._\n\n"


def system_instruction(region_name: str) -> str:
    return (
        f"너는 {region_name} 소상공인 창업 금융 컨설턴트다. "
        "사용자 메시지에 주어진 데이터와 문서만 근거로 한국어 마크다운으로 답한다. "
        "숫자는 주어진 값만 그대로 인용하고 새로 계산하거나 추정하지 않는다. "
        "문서에 없는 사실·상품명·금리는 만들지 않는다. "
        "제목(#)은 쓰지 않고, 요청한 분량을 넘기지 않는다."
    )


def _subject(ctx: AnalysisContext) -> str:
    return f"{ctx.region_label} {ctx.industry_label}"


def _grade_label(grade: str) -> str:
    return _GRADE_LABEL.get(grade, grade)


def _question(ctx: AnalysisContext) -> str:
    question = ctx.request.question
    return f"\n\n사용자 추가 질문(답변에 반영): {question}" if question else ""


def market_facts(ctx: AnalysisContext) -> str:
    cards = ", ".join(f"{c.label} {c.value}" for c in ctx.cards) or "지표 없음"
    risk = ctx.risk
    risk_text = (
        f"위험도 {risk.score:.1f}점(등급 {_grade_label(risk.grade)}, 구성 폐업 {risk.components['closure']}"
        f"·밀집 {risk.components['density']}·성장 {risk.components['growth']})"
        if risk
        else "위험도 데이터 없음"
    )
    return f"대상: {_subject(ctx)}\n상권 지표: {cards}\n{risk_text}"


def finance_facts(ctx: AnalysisContext) -> str:
    sim = ctx.simulation
    if sim is None:
        return "재무 시뮬레이션: 입력 없음"
    return (
        f"재무 시뮬레이션: 초기 투자 {sim.capex:,}원, 월 고정비 {sim.monthly_fixed:,}원, "
        f"손익분기 월매출 {sim.bep_revenue:,}원, 부족 자금 {sim.funding_gap:,}원"
    )


def products_text(ctx: AnalysisContext) -> str:
    lines = [
        f"- {p.provider} {p.product_name}: 한도 {p.loan_limit:,}원, 금리 {p.interest_rate}%"
        for p in ctx.products
    ]
    return "\n".join(lines) or "- 조건에 맞는 상품 없음"


def format_docs(docs: list[EvidenceDoc]) -> str:
    if not docs:
        return "(관련 문서 없음)"
    return "\n".join(
        f"[{i}] {d.title} ({d.org or '출처 미상'}, {d.published_at or '날짜 미상'})\n{d.snippet}"
        for i, d in enumerate(docs, start=1)
    )


def verdict_lead(ctx: AnalysisContext) -> str:
    risk = ctx.risk
    headline = f"위험도 {risk.score:.1f}점 — {_grade_label(risk.grade)}" if risk else "위험도 데이터 없음"
    return f"### 종합 진단\n\n**{_subject(ctx)} · {headline}**\n\n"


def market_lead(ctx: AnalysisContext) -> str:
    rows = [f"| {c.label} | {c.value} |" for c in ctx.cards]
    risk = ctx.risk
    if risk is not None:
        comps = risk.components
        rows.append(
            f"| 위험도 구성(폐업·밀집·성장) | {comps['closure']} · {comps['density']} · {comps['growth']} |"
        )
    table = "\n".join(["| 지표 | 값 |", "|---|---|", *rows]) if rows else "_상권 지표 데이터가 없습니다._"
    return f"### 상권 진단\n\n{table}\n\n"


def shock_lead(ctx: AnalysisContext) -> str:
    return "### 충격 분석\n\n"


def funding_lead(ctx: AnalysisContext) -> str:
    return f"### 정책자금\n\n**매칭 금융상품 (보증 → 은행 → 정책자금 순)**\n\n{products_text(ctx)}\n\n"


def verdict_prompt(ctx: AnalysisContext) -> str:
    return (
        f"{market_facts(ctx)}\n{finance_facts(ctx)}\n\n"
        "위 데이터로 이 창업 계획의 종합 판단을 3문장 이내로 써라. "
        "첫 문장은 위험 수준, 둘째 문장은 가장 큰 위험 변수, "
        "셋째 문장은 바꿔볼 만한 선택(입지·업종·자금 구성)이다." + _question(ctx)
    )


def market_prompt(ctx: AnalysisContext) -> str:
    return (
        f"{market_facts(ctx)}\n\n"
        "표의 지표가 창업자에게 무엇을 뜻하는지, 어떤 변수가 문제인지 불릿 3개 이내로 해석하라." + _question(ctx)
    )


def shock_prompt(ctx: AnalysisContext) -> str:
    return (
        f"대상: {_subject(ctx)}\n\n최근 뉴스:\n{format_docs(ctx.news)}\n\n"
        "이 업종·지역 창업에 영향을 줄 외부 충격(원가·금리·수요)을 불릿 3개 이내로 정리하고 "
        "근거 뉴스 번호를 [n] 형식으로 붙여라. 관련 뉴스가 없으면 없다고만 써라." + _question(ctx)
    )


def funding_prompt(ctx: AnalysisContext) -> str:
    return (
        f"대상: {_subject(ctx)}\n{finance_facts(ctx)}\n\n"
        f"매칭 금융상품:\n{products_text(ctx)}\n\n"
        f"정책자금·지원사업 공고:\n{format_docs(ctx.funding_docs)}\n\n"
        "자금 조달 경로를 보증 → 은행 → 정책자금 순서로 불릿 3개 이내로 제안하고 "
        "근거 공고 번호를 [n] 형식으로 붙여라." + _question(ctx)
    )


def _payback(months: float | None) -> str:
    return "회수 불가" if months is None else f"{months}개월"


def calculator_markdown(sim: SimulationSummary) -> str:
    rows = [
        f"| {s.name} | {s.monthly_revenue:,}원 | {s.operating_profit:,}원 | {_payback(s.payback_months)} |"
        for s in sim.scenarios
    ]
    return (
        "\n".join(
            [
                "### 재무 시뮬레이션",
                "",
                f"초기 투자 {sim.capex:,}원 · 월 고정비 {sim.monthly_fixed:,}원 · "
                f"손익분기 월매출 {sim.bep_revenue:,}원 · 부족 자금 {sim.funding_gap:,}원",
                "",
                "| 시나리오 | 월매출 | 영업이익 | 투자 회수 |",
                "|---|---|---|---|",
                *rows,
            ]
        )
        + "\n"
    )


def citations_from(ctx: AnalysisContext) -> list[Citation]:
    """공고 → 뉴스 순, URL 기준 중복 제거. URL 없는 문서는 링크를 못 걸어 제외."""
    by_url: dict[str, Citation] = {}
    for doc in [*ctx.funding_docs, *ctx.news]:
        if doc.url and doc.url not in by_url:
            by_url[doc.url] = Citation(
                title=doc.title, url=doc.url, grade=_CITATION_GRADE.get(doc.source_type, "signal")
            )
    return list(by_url.values())
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analysis_report_text.py -q`
Expected: `12 passed`

- [ ] **Step 5: 커밋**

```bash
git add backend/apps/analysis/domain/report_text.py backend/tests/test_analysis_report_text.py
git commit -m "feat(analysis): 리포트 첫머리·프롬프트·계산표·인용 텍스트 빌더

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: 출력 포트 + 수집 에이전트 3종 (Strategy)

**Files:**
- Create: `backend/apps/analysis/app/__init__.py`, `app/ports/__init__.py`, `app/ports/output/__init__.py`, `app/use_cases/__init__.py` (빈 파일, 모두 `backend/apps/analysis/` 아래)
- Create: `backend/apps/analysis/app/ports/output/analysis_port.py`
- Create: `backend/apps/analysis/app/use_cases/analysis_agents.py`
- Modify: `backend/tests/analysis_fakes.py` (파일 끝에 Fake 포트 추가)
- Test: `backend/tests/test_analysis_agents.py`

**Interfaces:**
- Consumes: Task 1 도메인 타입
- Produces:
  - 포트(ABC): `MarketDataPort.fetch(region_code: str, industry_id: str) -> MarketSnapshot | None` / `EvidenceSearchPort.search(query: str, source_type: str, top_k: int) -> list[EvidenceDoc]` / `SimulationPort.simulate(finance: dict) -> SimulationSummary` / `ProductMatchingPort.match(funding_gap: int, industry_id: str) -> list[MatchedProduct]` / `ReportWriterPort.stream(system: str, prompt: str) -> Iterator[str]` / `AnalysisRequestStorePort.save(request: AnalysisRequest) -> str`, `.take(analysis_id: str) -> AnalysisRequest | None`
  - `AnalysisAgent`(ABC): 클래스 상수 `name: str`, `collect(ctx: AnalysisContext) -> Iterator[ToolCallEvent]`
  - `MarketAgent(market: MarketDataPort)` — tool `region_metrics`, `risk_score`
  - `ShockAgent(search: EvidenceSearchPort, region_name: str)` — tool `news_search`
  - `FundingAgent(search, simulation: SimulationPort, matching: ProductMatchingPort, region_name: str)` — tool `finance_simulate`(finance 있을 때만), `product_matching`, `funding_search`
  - `NEWS_TOP_K = 5`, `FUNDING_TOP_K = 5`
  - fakes: `FakeMarketData`, `ExplodingMarketData`, `FakeEvidenceSearch`, `FakeSimulation`, `FakeMatching`, `FakeWriter`, `FailingWriter`

- [ ] **Step 1: Fake 포트 추가** — `backend/tests/analysis_fakes.py` 상단 import 블록에 추가하고, 파일 끝에 클래스 추가

import 추가:
```python
from collections.abc import Iterator

from apps.analysis.app.ports.output.analysis_port import (
    EvidenceSearchPort,
    MarketDataPort,
    ProductMatchingPort,
    ReportWriterPort,
    SimulationPort,
)
```

파일 끝에 추가:
```python
class FakeMarketData(MarketDataPort):
    def __init__(self, snapshot: MarketSnapshot | None = MARKET) -> None:
        self.snapshot = snapshot
        self.calls: list[tuple[str, str]] = []

    def fetch(self, region_code: str, industry_id: str) -> MarketSnapshot | None:
        self.calls.append((region_code, industry_id))
        return self.snapshot


class ExplodingMarketData(MarketDataPort):
    def fetch(self, region_code: str, industry_id: str) -> MarketSnapshot | None:
        raise RuntimeError("DB 장애")


class FakeEvidenceSearch(EvidenceSearchPort):
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int]] = []

    def search(self, query: str, source_type: str, top_k: int) -> list[EvidenceDoc]:
        self.calls.append((query, source_type, top_k))
        return {"news": [NEWS_DOC], "funding": [FUNDING_DOC]}[source_type]


class FakeSimulation(SimulationPort):
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def simulate(self, finance: dict) -> SimulationSummary:
        self.calls.append(finance)
        return SIMULATION


class FakeMatching(ProductMatchingPort):
    def __init__(self) -> None:
        self.calls: list[tuple[int, str]] = []

    def match(self, funding_gap: int, industry_id: str) -> list[MatchedProduct]:
        self.calls.append((funding_gap, industry_id))
        return [PRODUCT]


class FakeWriter(ReportWriterPort):
    def __init__(self, chunks: tuple[str, ...] = ("해석",)) -> None:
        self.chunks = chunks
        self.calls: list[tuple[str, str]] = []

    def stream(self, system: str, prompt: str) -> Iterator[str]:
        self.calls.append((system, prompt))
        yield from self.chunks


class FailingWriter(ReportWriterPort):
    def stream(self, system: str, prompt: str) -> Iterator[str]:
        yield "부분"
        raise RuntimeError("LLM 장애")
```

- [ ] **Step 2: 실패 테스트 작성** — `backend/tests/test_analysis_agents.py`

```python
"""수집 에이전트 3종 — Fake 포트로 컨텍스트 채움·tool_call 이벤트 검증."""

from apps.analysis.app.use_cases.analysis_agents import FundingAgent, MarketAgent, ShockAgent
from apps.analysis.domain.analysis_context import AnalysisContext, AnalysisRequest
from tests.analysis_fakes import (
    FINANCE,
    FUNDING_DOC,
    MARKET,
    NEWS_DOC,
    PRODUCT,
    SIMULATION,
    FakeEvidenceSearch,
    FakeMarketData,
    FakeMatching,
    FakeSimulation,
)


def _context(question: str | None = None, finance: dict | None = None) -> AnalysisContext:
    return AnalysisContext(
        analysis_id="abc",
        request=AnalysisRequest(region="2711059500", industry="cafe", question=question, finance=finance),
    )


def test_market_agent_fetches_snapshot_and_reports_two_tools():
    market = FakeMarketData()
    ctx = _context()

    events = list(MarketAgent(market).collect(ctx))

    assert market.calls == [("2711059500", "cafe")]
    assert ctx.market == MARKET
    assert [(e.agent, e.tool) for e in events] == [("market", "region_metrics"), ("market", "risk_score")]
    assert events[0].summary == "대신동 카페 점포수·폐업률·성장률 조회"


def test_shock_agent_searches_news_with_question():
    search = FakeEvidenceSearch()
    ctx = _context(question="원두값 오르면?")
    ctx.market = MARKET

    events = list(ShockAgent(search, "대구").collect(ctx))

    assert search.calls == [("대구 카페 소상공인 원가 금리 경기 원두값 오르면?", "news", 5)]
    assert ctx.news == [NEWS_DOC]
    assert [(e.agent, e.tool, e.summary) for e in events] == [("shock", "news_search", "뉴스 RAG 검색 — 1건")]


def test_funding_agent_without_finance_skips_simulation_and_matches_with_zero_gap():
    search, simulation, matching = FakeEvidenceSearch(), FakeSimulation(), FakeMatching()
    ctx = _context()
    ctx.market = MARKET

    events = list(FundingAgent(search, simulation, matching, "대구").collect(ctx))

    assert simulation.calls == []
    assert matching.calls == [(0, "cafe")]
    assert search.calls == [("대구 카페 소상공인 창업 정책자금 보증 대출", "funding", 5)]
    assert ctx.products == [PRODUCT]
    assert ctx.funding_docs == [FUNDING_DOC]
    assert [e.tool for e in events] == ["product_matching", "funding_search"]


def test_funding_agent_with_finance_simulates_first_and_matches_with_gap():
    search, simulation, matching = FakeEvidenceSearch(), FakeSimulation(), FakeMatching()
    ctx = _context(finance=FINANCE)

    events = list(FundingAgent(search, simulation, matching, "대구").collect(ctx))

    assert simulation.calls == [FINANCE]
    assert ctx.simulation == SIMULATION
    assert matching.calls == [(18_849_996, "cafe")]
    assert [e.tool for e in events] == ["finance_simulate", "product_matching", "funding_search"]
    assert events[0].summary == "재무 시뮬레이션 — 부족 자금 18,849,996원"
```

- [ ] **Step 3: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analysis_agents.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.analysis.app'`

- [ ] **Step 4: 포트 구현** — 빈 `__init__.py` 4개 생성 후 `backend/apps/analysis/app/ports/output/analysis_port.py`

```python
"""Driven Ports — analysis 가 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod
from collections.abc import Iterator

from apps.analysis.domain.analysis_context import (
    AnalysisRequest,
    EvidenceDoc,
    MarketSnapshot,
    MatchedProduct,
    SimulationSummary,
)


class MarketDataPort(ABC):
    @abstractmethod
    def fetch(self, region_code: str, industry_id: str) -> MarketSnapshot | None:
        """행정동×업종 상권 지표·위험도. 미등록 행정동이면 None."""


class EvidenceSearchPort(ABC):
    @abstractmethod
    def search(self, query: str, source_type: str, top_k: int) -> list[EvidenceDoc]:
        """RAG 문서 검색 — source_type: funding | news."""


class SimulationPort(ABC):
    @abstractmethod
    def simulate(self, finance: dict) -> SimulationSummary:
        """결정론 재무 엔진 실행 — finance 는 /finance/simulate 요청 13필드."""


class ProductMatchingPort(ABC):
    @abstractmethod
    def match(self, funding_gap: int, industry_id: str) -> list[MatchedProduct]:
        """부족 자금·업종 조건 금융상품 (보증 → 은행 → 정책자금 순)."""


class ReportWriterPort(ABC):
    @abstractmethod
    def stream(self, system: str, prompt: str) -> Iterator[str]:
        """LLM 해석 텍스트 조각 스트림."""


class AnalysisRequestStorePort(ABC):
    @abstractmethod
    def save(self, request: AnalysisRequest) -> str:
        """요청 보관 후 analysis_id 반환."""

    @abstractmethod
    def take(self, analysis_id: str) -> AnalysisRequest | None:
        """요청을 꺼내고 지운다(1회 소비). 없으면 None."""
```

- [ ] **Step 5: 에이전트 구현** — `backend/apps/analysis/app/use_cases/analysis_agents.py`

```python
"""수집 에이전트 (Strategy) — 각자 포트로 데이터를 모아 컨텍스트를 채우고 tool_call 이벤트를 낸다.

오케스트레이터(AnalysisInteractor)는 에이전트 종류를 모른 채 collect() 만 호출한다.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import ClassVar

from apps.analysis.app.ports.output.analysis_port import (
    EvidenceSearchPort,
    MarketDataPort,
    ProductMatchingPort,
    SimulationPort,
)
from apps.analysis.domain.agent_event import ToolCallEvent
from apps.analysis.domain.analysis_context import AnalysisContext

NEWS_TOP_K = 5
FUNDING_TOP_K = 5


def _with_question(base: str, ctx: AnalysisContext) -> str:
    return " ".join(part for part in (base, ctx.request.question) if part)


class AnalysisAgent(ABC):
    name: ClassVar[str]  # 프론트 AgentName: market | shock | funding

    @abstractmethod
    def collect(self, ctx: AnalysisContext) -> Iterator[ToolCallEvent]:
        """데이터를 모아 ctx 를 채우며 도구 호출마다 이벤트를 낸다."""


class MarketAgent(AnalysisAgent):
    name = "market"

    def __init__(self, market: MarketDataPort) -> None:
        self._market = market

    def collect(self, ctx: AnalysisContext) -> Iterator[ToolCallEvent]:
        ctx.market = self._market.fetch(ctx.request.region, ctx.request.industry)
        yield ToolCallEvent(
            agent=self.name,
            tool="region_metrics",
            summary=f"{ctx.region_label} {ctx.industry_label} 점포수·폐업률·성장률 조회",
        )
        yield ToolCallEvent(agent=self.name, tool="risk_score", summary="위험도 스코어(폐업·밀집·성장) 조회")


class ShockAgent(AnalysisAgent):
    name = "shock"

    def __init__(self, search: EvidenceSearchPort, region_name: str) -> None:
        self._search = search
        self._region_name = region_name

    def collect(self, ctx: AnalysisContext) -> Iterator[ToolCallEvent]:
        query = _with_question(f"{self._region_name} {ctx.industry_label} 소상공인 원가 금리 경기", ctx)
        ctx.news = self._search.search(query, "news", NEWS_TOP_K)
        yield ToolCallEvent(agent=self.name, tool="news_search", summary=f"뉴스 RAG 검색 — {len(ctx.news)}건")


class FundingAgent(AnalysisAgent):
    name = "funding"

    def __init__(
        self,
        search: EvidenceSearchPort,
        simulation: SimulationPort,
        matching: ProductMatchingPort,
        region_name: str,
    ) -> None:
        self._search = search
        self._simulation = simulation
        self._matching = matching
        self._region_name = region_name

    def collect(self, ctx: AnalysisContext) -> Iterator[ToolCallEvent]:
        if ctx.request.finance is not None:
            ctx.simulation = self._simulation.simulate(ctx.request.finance)
            yield ToolCallEvent(
                agent=self.name,
                tool="finance_simulate",
                summary=f"재무 시뮬레이션 — 부족 자금 {ctx.funding_gap:,}원",
            )
        ctx.products = self._matching.match(ctx.funding_gap, ctx.request.industry)
        yield ToolCallEvent(
            agent=self.name, tool="product_matching", summary=f"금융상품 매칭 — {len(ctx.products)}건"
        )
        query = _with_question(f"{self._region_name} {ctx.industry_label} 소상공인 창업 정책자금 보증 대출", ctx)
        ctx.funding_docs = self._search.search(query, "funding", FUNDING_TOP_K)
        yield ToolCallEvent(
            agent=self.name,
            tool="funding_search",
            summary=f"정책자금 공고 RAG 검색 — {len(ctx.funding_docs)}건",
        )
```

- [ ] **Step 6: 통과 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analysis_agents.py tests/test_analysis_domain.py tests/test_analysis_report_text.py -q`
Expected: `23 passed`

- [ ] **Step 7: 커밋**

```bash
git add backend/apps/analysis/app/ backend/tests/analysis_fakes.py backend/tests/test_analysis_agents.py
git commit -m "feat(analysis): 출력 포트와 market·shock·funding 수집 에이전트

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: 리포트 섹션 5종 (Strategy + Template Method, LLM 실패 폴백)

**Files:**
- Create: `backend/apps/analysis/app/use_cases/report_sections.py`
- Test: `backend/tests/test_analysis_sections.py`

**Interfaces:**
- Consumes: Task 2 텍스트 빌더, Task 3 `ReportWriterPort`, fakes `FakeWriter`/`FailingWriter`
- Produces:
  - `ReportSection`(ABC): 클래스 상수 `key: str`, `render(ctx, writer: ReportWriterPort) -> Iterator[str]`
  - `InterpretedSection(system: str)` — `lead(ctx)`·`prompt(ctx)` 추상, render = lead → writer.stream → (예외 시) `FALLBACK_MARKDOWN`
  - `VerdictSection`, `MarketSection`, `ShockSection`, `FundingSection`(각 `InterpretedSection`), `CalculatorSection()`
  - `default_sections(region_name: str) -> list[ReportSection]` — key 순서 `verdict, market, shock, funding, calculator`

- [ ] **Step 1: 실패 테스트 작성** — `backend/tests/test_analysis_sections.py`

```python
"""리포트 섹션 — 코드 첫머리 + LLM 스트림, LLM 실패 폴백, 계산표 조건부 출력."""

from apps.analysis.app.use_cases.report_sections import CalculatorSection, VerdictSection, default_sections
from apps.analysis.domain.report_text import FALLBACK_MARKDOWN, calculator_markdown, verdict_lead, verdict_prompt
from tests.analysis_fakes import SIMULATION, FailingWriter, FakeWriter, full_context


def test_default_sections_follow_frontend_section_order():
    assert [s.key for s in default_sections("대구")] == ["verdict", "market", "shock", "funding", "calculator"]


def test_interpreted_section_yields_code_lead_then_llm_chunks():
    ctx = full_context()
    writer = FakeWriter(chunks=("첫 조각", "둘째 조각"))

    chunks = list(VerdictSection("시스템").render(ctx, writer))

    assert chunks == [verdict_lead(ctx), "첫 조각", "둘째 조각"]
    assert writer.calls == [("시스템", verdict_prompt(ctx))]


def test_interpreted_section_falls_back_when_llm_fails_mid_stream():
    ctx = full_context()

    chunks = list(VerdictSection("시스템").render(ctx, FailingWriter()))

    assert chunks == [verdict_lead(ctx), "부분", FALLBACK_MARKDOWN]


def test_default_sections_pass_region_system_instruction_to_writer():
    writer = FakeWriter()
    list(default_sections("대구")[0].render(full_context(), writer))
    assert "대구" in writer.calls[0][0]


def test_calculator_section_renders_table_without_llm_when_simulated():
    writer = FakeWriter()
    assert list(CalculatorSection().render(full_context(), writer)) == [calculator_markdown(SIMULATION)]
    assert writer.calls == []


def test_calculator_section_renders_nothing_without_simulation():
    ctx = full_context()
    ctx.simulation = None
    assert list(CalculatorSection().render(ctx, FakeWriter())) == []
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analysis_sections.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.analysis.app.use_cases.report_sections'`

- [ ] **Step 3: 구현** — `backend/apps/analysis/app/use_cases/report_sections.py`

```python
"""리포트 섹션 (Strategy) — 섹션마다 무엇을 어떻게 쓰는지 스스로 안다.

InterpretedSection 은 Template Method: 코드가 쓰는 첫머리(수치) → LLM 해석 스트림.
LLM 이 실패해도 폴백 문구로 섹션을 닫아 스트림이 report_done 까지 가게 한다.
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import ClassVar

from apps.analysis.app.ports.output.analysis_port import ReportWriterPort
from apps.analysis.domain.analysis_context import AnalysisContext
from apps.analysis.domain.report_text import (
    FALLBACK_MARKDOWN,
    calculator_markdown,
    funding_lead,
    funding_prompt,
    market_lead,
    market_prompt,
    shock_lead,
    shock_prompt,
    system_instruction,
    verdict_lead,
    verdict_prompt,
)

LOGGER = logging.getLogger("localhostdaegu.analysis")


class ReportSection(ABC):
    key: ClassVar[str]  # 프론트 ReportView SECTION_ORDER 값

    @abstractmethod
    def render(self, ctx: AnalysisContext, writer: ReportWriterPort) -> Iterator[str]:
        """이 섹션의 markdown 조각들."""


class InterpretedSection(ReportSection):
    def __init__(self, system: str) -> None:
        self._system = system

    def render(self, ctx: AnalysisContext, writer: ReportWriterPort) -> Iterator[str]:
        yield self.lead(ctx)
        try:
            yield from writer.stream(self._system, self.prompt(ctx))
        except Exception:
            LOGGER.exception("리포트 섹션 %s LLM 생성 실패 — 폴백 문구로 대체", self.key)
            yield FALLBACK_MARKDOWN

    @abstractmethod
    def lead(self, ctx: AnalysisContext) -> str:
        """코드가 쓰는 첫머리 (제목·수치)."""

    @abstractmethod
    def prompt(self, ctx: AnalysisContext) -> str:
        """LLM 사용자 프롬프트."""


class VerdictSection(InterpretedSection):
    key = "verdict"

    def lead(self, ctx: AnalysisContext) -> str:
        return verdict_lead(ctx)

    def prompt(self, ctx: AnalysisContext) -> str:
        return verdict_prompt(ctx)


class MarketSection(InterpretedSection):
    key = "market"

    def lead(self, ctx: AnalysisContext) -> str:
        return market_lead(ctx)

    def prompt(self, ctx: AnalysisContext) -> str:
        return market_prompt(ctx)


class ShockSection(InterpretedSection):
    key = "shock"

    def lead(self, ctx: AnalysisContext) -> str:
        return shock_lead(ctx)

    def prompt(self, ctx: AnalysisContext) -> str:
        return shock_prompt(ctx)


class FundingSection(InterpretedSection):
    key = "funding"

    def lead(self, ctx: AnalysisContext) -> str:
        return funding_lead(ctx)

    def prompt(self, ctx: AnalysisContext) -> str:
        return funding_prompt(ctx)


class CalculatorSection(ReportSection):
    """재무 입력이 있을 때만 결정론 계산표 — LLM 호출 없음."""

    key = "calculator"

    def render(self, ctx: AnalysisContext, writer: ReportWriterPort) -> Iterator[str]:
        if ctx.simulation is not None:
            yield calculator_markdown(ctx.simulation)


def default_sections(region_name: str) -> list[ReportSection]:
    system = system_instruction(region_name)
    return [
        VerdictSection(system),
        MarketSection(system),
        ShockSection(system),
        FundingSection(system),
        CalculatorSection(),
    ]
```

- [ ] **Step 4: 통과 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analysis_sections.py -q`
Expected: `6 passed`

- [ ] **Step 5: 커밋**

```bash
git add backend/apps/analysis/app/use_cases/report_sections.py backend/tests/test_analysis_sections.py
git commit -m "feat(analysis): 리포트 섹션 Strategy — 코드 첫머리+LLM 해석, 실패 폴백

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: 오케스트레이터 인터랙터 + 인메모리 요청 저장소

**Files:**
- Create: `backend/apps/analysis/app/ports/input/__init__.py` (빈 파일)
- Create: `backend/apps/analysis/app/ports/input/analysis_use_case.py`
- Create: `backend/apps/analysis/app/use_cases/analysis_interactor.py`
- Create: `backend/apps/analysis/adapter/__init__.py`, `adapter/outbound/__init__.py`, `adapter/outbound/stores/__init__.py` (빈 파일)
- Create: `backend/apps/analysis/adapter/outbound/stores/in_memory_analysis_request_store.py`
- Modify: `backend/tests/analysis_fakes.py` (파일 끝에 `build_interactor` 추가)
- Test: `backend/tests/test_analysis_interactor.py`

**Interfaces:**
- Consumes: Task 1~4 전부
- Produces:
  - `AnalysisUseCase`(ABC): `start(request: AnalysisRequest) -> str`, `stream(analysis_id: str) -> Iterator[AgentEvent]` — 요청이 없으면 **호출 즉시**(첫 이벤트 전에) `AnalysisNotFoundError`
  - `AnalysisInteractor(store: AnalysisRequestStorePort, agents: list[AnalysisAgent], sections: list[ReportSection], writer: ReportWriterPort)`
  - `ORCHESTRATOR = "orchestrator"`
  - `InMemoryAnalysisRequestStore()` — `save` → `uuid4().hex`
  - fakes: `build_interactor(market: MarketDataPort | None = None, writer: ReportWriterPort | None = None) -> AnalysisInteractor`

- [ ] **Step 1: 헬퍼 추가** — `backend/tests/analysis_fakes.py` import 블록에 추가 + 파일 끝에 함수

import 추가:
```python
from apps.analysis.adapter.outbound.stores.in_memory_analysis_request_store import (
    InMemoryAnalysisRequestStore,
)
from apps.analysis.app.use_cases.analysis_agents import FundingAgent, MarketAgent, ShockAgent
from apps.analysis.app.use_cases.analysis_interactor import AnalysisInteractor
from apps.analysis.app.use_cases.report_sections import default_sections
```

파일 끝에 추가:
```python
def build_interactor(
    market: MarketDataPort | None = None, writer: ReportWriterPort | None = None
) -> AnalysisInteractor:
    """실제 에이전트·섹션 + Fake 포트로 조립한 인터랙터 (Composition Root 의 테스트판)."""
    search = FakeEvidenceSearch()
    return AnalysisInteractor(
        store=InMemoryAnalysisRequestStore(),
        agents=[
            MarketAgent(market or FakeMarketData()),
            ShockAgent(search, "대구"),
            FundingAgent(search, FakeSimulation(), FakeMatching(), "대구"),
        ],
        sections=default_sections("대구"),
        writer=writer or FakeWriter(),
    )
```

- [ ] **Step 2: 실패 테스트 작성** — `backend/tests/test_analysis_interactor.py`

```python
"""AnalysisInteractor — 이벤트 순서(mock SSE 와 동일), 에이전트·LLM 장애 내성, 1회 소비."""

import re

import pytest

from apps.analysis.adapter.outbound.stores.in_memory_analysis_request_store import (
    InMemoryAnalysisRequestStore,
)
from apps.analysis.domain.agent_event import Citation
from apps.analysis.domain.analysis_context import AnalysisRequest
from apps.analysis.domain.errors import AnalysisNotFoundError
from apps.analysis.domain.report_text import FALLBACK_MARKDOWN
from tests.analysis_fakes import (
    FINANCE,
    FUNDING_DOC,
    NEWS_DOC,
    ExplodingMarketData,
    FailingWriter,
    build_interactor,
)

_REQUEST = AnalysisRequest(region="2711059500", industry="cafe")


def _shape(event) -> tuple[str, str, str]:
    p = event.to_payload()
    return (p["type"], p.get("agent") or p.get("section") or "", p.get("status") or p.get("tool") or "")


def _run(interactor, request=_REQUEST):
    analysis_id = interactor.start(request)
    return analysis_id, list(interactor.stream(analysis_id))


def test_stream_emits_events_in_mock_sse_order():
    _, events = _run(build_interactor())

    assert [_shape(e) for e in events] == [
        ("agent_status", "orchestrator", "running"),
        ("agent_status", "market", "running"),
        ("tool_call", "market", "region_metrics"),
        ("tool_call", "market", "risk_score"),
        ("agent_status", "market", "done"),
        ("agent_status", "shock", "running"),
        ("tool_call", "shock", "news_search"),
        ("agent_status", "shock", "done"),
        ("agent_status", "funding", "running"),
        ("tool_call", "funding", "product_matching"),
        ("tool_call", "funding", "funding_search"),
        ("agent_status", "funding", "done"),
        ("report_delta", "verdict", ""),
        ("report_delta", "verdict", ""),
        ("report_delta", "market", ""),
        ("report_delta", "market", ""),
        ("report_delta", "shock", ""),
        ("report_delta", "shock", ""),
        ("report_delta", "funding", ""),
        ("report_delta", "funding", ""),
        ("agent_status", "orchestrator", "done"),
        ("report_done", "", ""),
    ]


def test_report_done_carries_analysis_id_and_citations():
    analysis_id, events = _run(build_interactor())
    done = events[-1].to_payload()
    assert done["report_id"] == analysis_id
    assert done["citations"] == [
        {"title": FUNDING_DOC.title, "url": FUNDING_DOC.url, "grade": "fact"},
        {"title": NEWS_DOC.title, "url": NEWS_DOC.url, "grade": "signal"},
    ]


def test_finance_input_adds_simulation_tool_and_calculator_section():
    _, events = _run(build_interactor(), AnalysisRequest(region="2711059500", industry="cafe", finance=FINANCE))
    shapes = [_shape(e) for e in events]
    assert ("tool_call", "funding", "finance_simulate") in shapes
    assert shapes.count(("report_delta", "calculator", "")) == 1


def test_failing_agent_reports_error_and_stream_still_completes():
    _, events = _run(build_interactor(market=ExplodingMarketData()))
    shapes = [_shape(e) for e in events]
    assert ("agent_status", "market", "error") in shapes
    assert ("agent_status", "market", "done") not in shapes
    assert shapes[-1] == ("report_done", "", "")
    verdict = [e.markdown for e in events if _shape(e) == ("report_delta", "verdict", "")]
    assert "위험도 데이터 없음" in verdict[0]


def test_llm_failure_uses_fallback_and_stream_still_completes():
    _, events = _run(build_interactor(writer=FailingWriter()))
    verdict = [e.markdown for e in events if _shape(e) == ("report_delta", "verdict", "")]
    assert verdict[1:] == ["부분", FALLBACK_MARKDOWN]
    assert _shape(events[-1]) == ("report_done", "", "")


def test_unknown_analysis_id_raises_before_streaming():
    with pytest.raises(AnalysisNotFoundError):
        build_interactor().stream("nope")


def test_request_is_consumed_once():
    interactor = build_interactor()
    analysis_id, _ = _run(interactor)
    with pytest.raises(AnalysisNotFoundError):
        interactor.stream(analysis_id)


def test_in_memory_store_issues_hex_id_and_take_removes():
    store = InMemoryAnalysisRequestStore()
    analysis_id = store.save(_REQUEST)
    assert re.fullmatch(r"[0-9a-f]{32}", analysis_id)
    assert store.take(analysis_id) == _REQUEST
    assert store.take(analysis_id) is None
```

- [ ] **Step 3: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analysis_interactor.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.analysis.adapter'`

- [ ] **Step 4: 입력 포트 구현** — `backend/apps/analysis/app/ports/input/analysis_use_case.py`

```python
"""Driving Port — AI 분석 리포트 UseCase (POST 시작 → GET SSE 스트림)."""

from abc import ABC, abstractmethod
from collections.abc import Iterator

from apps.analysis.domain.agent_event import AgentEvent
from apps.analysis.domain.analysis_context import AnalysisRequest


class AnalysisUseCase(ABC):
    @abstractmethod
    def start(self, request: AnalysisRequest) -> str:
        """요청을 보관하고 analysis_id 를 돌려준다 (분석은 스트림 구독 시 실행)."""

    @abstractmethod
    def stream(self, analysis_id: str) -> Iterator[AgentEvent]:
        """요청을 1회 꺼내 이벤트 스트림을 돌려준다. 없으면 호출 즉시 AnalysisNotFoundError."""
```

- [ ] **Step 5: 저장소 구현** — 빈 `__init__.py` 3개 생성 후 `backend/apps/analysis/adapter/outbound/stores/in_memory_analysis_request_store.py`

```python
"""Driven Adapter — 프로세스 메모리 요청 저장소.

POST(보관) → GET(1회 소비) 사이만 산다. 단일 uvicorn 워커 전제 — 다중 워커 배포 시 Redis 어댑터로 교체.
"""

import threading
from uuid import uuid4

from apps.analysis.app.ports.output.analysis_port import AnalysisRequestStorePort
from apps.analysis.domain.analysis_context import AnalysisRequest


class InMemoryAnalysisRequestStore(AnalysisRequestStorePort):
    def __init__(self) -> None:
        self._requests: dict[str, AnalysisRequest] = {}
        self._lock = threading.Lock()

    def save(self, request: AnalysisRequest) -> str:
        analysis_id = uuid4().hex
        with self._lock:
            self._requests[analysis_id] = request
        return analysis_id

    def take(self, analysis_id: str) -> AnalysisRequest | None:
        with self._lock:
            return self._requests.pop(analysis_id, None)
```

- [ ] **Step 6: 인터랙터 구현** — `backend/apps/analysis/app/use_cases/analysis_interactor.py`

```python
"""AnalysisInteractor — 오케스트레이터 (얇은 Application Service).

순서(프론트 mock SSE 와 동일): orchestrator running → 에이전트별 running/tool_call/done
→ 섹션별 report_delta → orchestrator done → report_done.
에이전트 하나가 실패해도 error 상태만 알리고 계속 — 스트림은 항상 report_done 으로 끝난다.
"""

import logging
from collections.abc import Iterator

from apps.analysis.app.ports.input.analysis_use_case import AnalysisUseCase
from apps.analysis.app.ports.output.analysis_port import AnalysisRequestStorePort, ReportWriterPort
from apps.analysis.app.use_cases.analysis_agents import AnalysisAgent
from apps.analysis.app.use_cases.report_sections import ReportSection
from apps.analysis.domain.agent_event import AgentEvent, AgentStatusEvent, ReportDeltaEvent, ReportDoneEvent
from apps.analysis.domain.analysis_context import AnalysisContext, AnalysisRequest
from apps.analysis.domain.errors import AnalysisNotFoundError
from apps.analysis.domain.report_text import citations_from

LOGGER = logging.getLogger("localhostdaegu.analysis")

ORCHESTRATOR = "orchestrator"


class AnalysisInteractor(AnalysisUseCase):
    def __init__(
        self,
        store: AnalysisRequestStorePort,
        agents: list[AnalysisAgent],
        sections: list[ReportSection],
        writer: ReportWriterPort,
    ) -> None:
        self._store = store
        self._agents = agents
        self._sections = sections
        self._writer = writer

    def start(self, request: AnalysisRequest) -> str:
        return self._store.save(request)

    def stream(self, analysis_id: str) -> Iterator[AgentEvent]:
        # 제너레이터가 아닌 일반 메서드 — 404 판단을 응답 시작 전에 끝내기 위해 take 를 즉시 수행한다.
        request = self._store.take(analysis_id)
        if request is None:
            raise AnalysisNotFoundError(analysis_id)
        return self._run(AnalysisContext(analysis_id=analysis_id, request=request))

    def _run(self, ctx: AnalysisContext) -> Iterator[AgentEvent]:
        yield AgentStatusEvent(agent=ORCHESTRATOR, status="running")
        for agent in self._agents:
            yield from self._collect(agent, ctx)
        for section in self._sections:
            for markdown in section.render(ctx, self._writer):
                yield ReportDeltaEvent(section=section.key, markdown=markdown)
        yield AgentStatusEvent(agent=ORCHESTRATOR, status="done")
        yield ReportDoneEvent(report_id=ctx.analysis_id, citations=citations_from(ctx))

    def _collect(self, agent: AnalysisAgent, ctx: AnalysisContext) -> Iterator[AgentEvent]:
        yield AgentStatusEvent(agent=agent.name, status="running")
        try:
            yield from agent.collect(ctx)
        except Exception:
            LOGGER.exception("분석 에이전트 %s 실패 — 나머지로 계속", agent.name)
            yield AgentStatusEvent(agent=agent.name, status="error")
            return
        yield AgentStatusEvent(agent=agent.name, status="done")
```

- [ ] **Step 7: 통과 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analysis_interactor.py tests/test_analysis_sections.py tests/test_analysis_agents.py -q`
Expected: `18 passed`

- [ ] **Step 8: 커밋**

```bash
git add backend/apps/analysis/app/ports/input/ backend/apps/analysis/app/use_cases/analysis_interactor.py backend/apps/analysis/adapter/__init__.py backend/apps/analysis/adapter/outbound/__init__.py backend/apps/analysis/adapter/outbound/stores/ backend/tests/analysis_fakes.py backend/tests/test_analysis_interactor.py
git commit -m "feat(analysis): 오케스트레이터 인터랙터와 1회 소비 인메모리 요청 저장소

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: 아웃바운드 게이트웨이 — 상권·RAG·재무/매칭 (타 BC ACL)

**Files:**
- Create: `backend/apps/analysis/adapter/outbound/gateways/__init__.py` (빈 파일)
- Create: `backend/apps/analysis/adapter/outbound/gateways/market_data_gateway.py`
- Create: `backend/apps/analysis/adapter/outbound/gateways/evidence_search_gateway.py`
- Create: `backend/apps/analysis/adapter/outbound/gateways/finance_gateways.py`
- Test: `backend/tests/test_analysis_gateways.py`

**Interfaces:**
- Consumes: Task 3 포트. 타 BC — `apps.master.app.ports.input.region_use_case.RegionUseCase.summary(region_code, industry_id) -> RegionSummaryDto(region_code, name, industry_id, cards: list[SummaryCardDto(label, value, grade)])`(미등록 시 `RegionNotFoundError`), `apps.metric.app.ports.input.risk_use_case.RiskUseCase.score_for(region_code, industry_id, year=None) -> RiskScoreDto | None`, `apps.master.adapter.outbound.orms.industry_orm.IndustryOrm`(industry_id, name), `apps.rag.app.ports.input.rag_use_case.RagSearchUseCase.search(query, top_k, source_type) -> list[RagHit]`, `apps.finance.domain.engine.FinanceInput`/`simulate`, `apps.matching.domain.matcher.match_products(products, funding_gap, category, business_age_months, owner_age)`, `apps.matching.adapter.outbound.gateways.manual_product_gateway.load_all_products`
- Produces:
  - `MarketDataGateway(region_use_case: RegionUseCase, risk_use_case: RiskUseCase)` (MarketDataPort)
  - `EvidenceSearchGateway(search_use_case: RagSearchUseCase)` (EvidenceSearchPort), `SNIPPET_CHARS = 300`
  - `EngineSimulationGateway()` (SimulationPort), `ManualProductMatchingGateway(load_products: Callable[[], list[dict]] = load_all_products)` (ProductMatchingPort)

- [ ] **Step 1: 실패 테스트 작성** — `backend/tests/test_analysis_gateways.py`

```python
"""analysis 아웃바운드 게이트웨이 — 타 BC 결과를 analysis 값 객체로 변환 (ACL).

업종명은 테스트 DB 마스터 시드(conftest seed_all: cafe=카페)를 읽는다. 나머지 타 BC 는 Fake 유스케이스.
"""

from datetime import datetime

from apps.analysis.adapter.outbound.gateways.evidence_search_gateway import EvidenceSearchGateway
from apps.analysis.adapter.outbound.gateways.finance_gateways import (
    EngineSimulationGateway,
    ManualProductMatchingGateway,
)
from apps.analysis.adapter.outbound.gateways.market_data_gateway import MarketDataGateway
from apps.analysis.domain.analysis_context import EvidenceDoc, MatchedProduct, MetricCard, RiskView
from apps.master.app.dtos.region_dto import RegionDto, RegionSummaryDto, SummaryCardDto
from apps.master.app.ports.input.region_use_case import RegionUseCase
from apps.master.domain.errors import RegionNotFoundError
from apps.metric.app.dtos.region_industry_metric_dto import RiskScoreDto
from apps.metric.app.ports.input.risk_use_case import RiskUseCase
from apps.rag.app.ports.input.rag_use_case import RagSearchUseCase
from apps.rag.domain.entities.rag_chunk_entity import RagHit
from tests.analysis_fakes import FINANCE, SIMULATION


class FakeRegionUseCase(RegionUseCase):
    def myself(self) -> RegionDto:
        raise NotImplementedError

    def geojson(self) -> dict:
        raise NotImplementedError

    def summary(self, region_code: str, industry_id: str) -> RegionSummaryDto:
        if region_code != "2711059500":
            raise RegionNotFoundError(region_code)
        return RegionSummaryDto(
            region_code=region_code,
            name="대신동",
            industry_id=industry_id,
            cards=[
                SummaryCardDto("점포수", "120개", "fact"),
                SummaryCardDto("폐업률", "6.4%", "fact"),
                SummaryCardDto("성장률", "+2.1%", "fact"),
            ],
        )


class FakeRiskUseCase(RiskUseCase):
    def __init__(self, dto: RiskScoreDto | None) -> None:
        self._dto = dto

    def rank_by_region(self, industry_id, year):
        raise NotImplementedError

    def rank_by_industry(self, region_code, year):
        raise NotImplementedError

    def score_for(self, region_code, industry_id, year):
        return self._dto


_RISK = RiskScoreDto("2711059500", "cafe", 72.5, "red", {"closure": 30.0, "density": 28.5, "growth": 14.0})


def test_market_gateway_maps_summary_risk_and_industry_name():
    snapshot = MarketDataGateway(FakeRegionUseCase(), FakeRiskUseCase(_RISK)).fetch("2711059500", "cafe")

    assert snapshot.region_name == "대신동"
    assert snapshot.industry_name == "카페"
    assert snapshot.cards == [MetricCard("점포수", "120개"), MetricCard("폐업률", "6.4%"), MetricCard("성장률", "+2.1%")]
    assert snapshot.risk == RiskView(72.5, "red", {"closure": 30.0, "density": 28.5, "growth": 14.0})


def test_market_gateway_returns_none_for_unknown_region():
    assert MarketDataGateway(FakeRegionUseCase(), FakeRiskUseCase(_RISK)).fetch("0000000000", "cafe") is None


def test_market_gateway_keeps_snapshot_without_risk_and_falls_back_to_industry_id():
    snapshot = MarketDataGateway(FakeRegionUseCase(), FakeRiskUseCase(None)).fetch("2711059500", "unknown_industry")
    assert snapshot.risk is None
    assert snapshot.industry_name == "unknown_industry"


class FakeRagSearch(RagSearchUseCase):
    def __init__(self, hits: list[RagHit]) -> None:
        self._hits = hits
        self.calls: list[tuple] = []

    def search(self, query, top_k=5, source_type=None):
        self.calls.append((query, top_k, source_type))
        return self._hits


def _hit(content: str, published_at: datetime | None = datetime(2026, 9, 10, 9, 0)) -> RagHit:
    return RagHit("news:1", "news", "1", content, 0.8, "https://news.example/1", "매일신문", published_at)


def test_evidence_gateway_splits_title_and_snippet_and_passes_filters():
    rag = FakeRagSearch([_hit("원두값 급등에 카페 원가 압박\n원두 선물 가격이 전년 대비 8% 상승했다.")])

    docs = EvidenceSearchGateway(rag).search("대구 카페", "news", 5)

    assert rag.calls == [("대구 카페", 5, "news")]
    assert docs == [
        EvidenceDoc("news", "원두값 급등에 카페 원가 압박", "원두 선물 가격이 전년 대비 8% 상승했다.",
                    "https://news.example/1", "매일신문", "2026-09-10")
    ]


def test_evidence_gateway_title_only_content_and_long_body_truncation():
    title_only = EvidenceSearchGateway(FakeRagSearch([_hit("제목만", published_at=None)])).search("q", "news", 5)[0]
    assert (title_only.title, title_only.snippet, title_only.published_at) == ("제목만", "제목만", None)

    long_doc = EvidenceSearchGateway(FakeRagSearch([_hit("제목\n" + "가" * 500)])).search("q", "news", 5)[0]
    assert len(long_doc.snippet) == 300


def test_simulation_gateway_runs_deterministic_engine():
    assert EngineSimulationGateway().simulate(FINANCE) == SIMULATION


def _product(product_id, provider, provider_type, name, loan_limit, rate, category):
    return {
        "product_id": product_id, "provider": provider, "provider_type": provider_type,
        "product_name": name, "business_age_min": 0, "business_age_max": None, "category": category,
        "owner_age_max": None, "loan_limit": loan_limit, "interest_rate": rate,
    }


def test_matching_gateway_filters_by_gap_and_industry_and_orders_guarantee_first():
    products = [
        _product("b1", "iM뱅크", "bank", "창업대출", 100_000_000, 5.5, ["cafe"]),
        _product("g1", "대구신용보증재단", "guarantee", "창업 보증", 50_000_000, 3.2, ["cafe"]),
        _product("b2", "iM뱅크", "bank", "소액대출", 5_000_000, 6.0, ["cafe"]),
        _product("r1", "iM뱅크", "bank", "음식점대출", 100_000_000, 5.0, ["restaurant"]),
    ]

    matched = ManualProductMatchingGateway(lambda: products).match(10_000_000, "cafe")

    assert matched == [
        MatchedProduct("대구신용보증재단", "창업 보증", 50_000_000, 3.2),
        MatchedProduct("iM뱅크", "창업대출", 100_000_000, 5.5),
    ]
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analysis_gateways.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.analysis.adapter.outbound.gateways'`

- [ ] **Step 3: 상권 게이트웨이** — 빈 `gateways/__init__.py` 생성 후 `market_data_gateway.py`

```python
"""Driven Adapter — master(region summary)·metric(risk) 유스케이스 결과를 MarketSnapshot 으로 변환 (ACL).

cross-BC 접근은 이 어댑터에서만 한다.
"""

from apps.analysis.app.ports.output.analysis_port import MarketDataPort
from apps.analysis.domain.analysis_context import MarketSnapshot, MetricCard, RiskView
from apps.master.adapter.outbound.orms.industry_orm import IndustryOrm
from apps.master.app.ports.input.region_use_case import RegionUseCase
from apps.master.domain.errors import RegionNotFoundError
from apps.metric.app.ports.input.risk_use_case import RiskUseCase
from core.matrix.grid_oracle_database_manager import session_scope


class MarketDataGateway(MarketDataPort):
    def __init__(self, region_use_case: RegionUseCase, risk_use_case: RiskUseCase) -> None:
        self._region = region_use_case
        self._risk = risk_use_case

    def fetch(self, region_code: str, industry_id: str) -> MarketSnapshot | None:
        try:
            summary = self._region.summary(region_code, industry_id)
        except RegionNotFoundError:
            return None
        risk = self._risk.score_for(region_code, industry_id, None)
        return MarketSnapshot(
            region_name=summary.name,
            industry_name=self._industry_name(industry_id),
            cards=[MetricCard(label=card.label, value=card.value) for card in summary.cards],
            risk=None if risk is None else RiskView(score=risk.score, grade=risk.grade, components=dict(risk.components)),
        )

    def _industry_name(self, industry_id: str) -> str:
        with session_scope() as session:
            orm = session.get(IndustryOrm, industry_id)
            return industry_id if orm is None else orm.name
```

- [ ] **Step 4: RAG 게이트웨이** — `evidence_search_gateway.py`

```python
"""Driven Adapter — rag BC 검색 결과(RagHit)를 EvidenceDoc 으로 변환 (ACL).

청크 content 는 "제목\\n본문" 형식(rag_chunk_entity.build_funding_chunk / build_news_chunk).
"""

from apps.analysis.app.ports.output.analysis_port import EvidenceSearchPort
from apps.analysis.domain.analysis_context import EvidenceDoc
from apps.rag.app.ports.input.rag_use_case import RagSearchUseCase
from apps.rag.domain.entities.rag_chunk_entity import RagHit

SNIPPET_CHARS = 300


def _to_doc(hit: RagHit) -> EvidenceDoc:
    title, _, body = hit.content.partition("\n")
    title = title.strip()
    return EvidenceDoc(
        source_type=hit.source_type,
        title=title,
        snippet=(body.strip() or title)[:SNIPPET_CHARS],
        url=hit.url,
        org=hit.org,
        published_at=hit.published_at.date().isoformat() if hit.published_at else None,
    )


class EvidenceSearchGateway(EvidenceSearchPort):
    def __init__(self, search_use_case: RagSearchUseCase) -> None:
        self._search = search_use_case

    def search(self, query: str, source_type: str, top_k: int) -> list[EvidenceDoc]:
        return [_to_doc(hit) for hit in self._search.search(query, top_k=top_k, source_type=source_type)]
```

- [ ] **Step 5: 재무·매칭 게이트웨이** — `finance_gateways.py`

```python
"""Driven Adapters — finance 결정론 엔진·matching 도메인 함수를 analysis 포트로 노출 (ACL)."""

from collections.abc import Callable

from apps.analysis.app.ports.output.analysis_port import ProductMatchingPort, SimulationPort
from apps.analysis.domain.analysis_context import MatchedProduct, ScenarioLine, SimulationSummary
from apps.finance.domain.engine import FinanceInput, simulate
from apps.matching.adapter.outbound.gateways.manual_product_gateway import load_all_products
from apps.matching.domain.matcher import match_products

_PRE_STARTUP_BUSINESS_AGE_MONTHS = 0  # 리포트 대상은 예비창업자 — 업력 0개월 전제


class EngineSimulationGateway(SimulationPort):
    def simulate(self, finance: dict) -> SimulationSummary:
        result = simulate(FinanceInput(**finance))
        return SimulationSummary(
            capex=result.capex,
            monthly_fixed=result.monthly_fixed,
            bep_revenue=result.bep_revenue,
            funding_gap=result.funding_gap,
            scenarios=[
                ScenarioLine(s.name, s.monthly_revenue, s.operating_profit, s.payback_months)
                for s in result.scenarios
            ],
        )


class ManualProductMatchingGateway(ProductMatchingPort):
    def __init__(self, load_products: Callable[[], list[dict]] = load_all_products) -> None:
        self._load_products = load_products

    def match(self, funding_gap: int, industry_id: str) -> list[MatchedProduct]:
        rows = match_products(
            self._load_products(), funding_gap, industry_id, _PRE_STARTUP_BUSINESS_AGE_MONTHS, None
        )
        return [
            MatchedProduct(p["provider"], p["product_name"], p["loan_limit"], p["interest_rate"]) for p in rows
        ]
```

- [ ] **Step 6: 통과 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analysis_gateways.py -q`
Expected: `7 passed`

- [ ] **Step 7: 커밋**

```bash
git add backend/apps/analysis/adapter/outbound/gateways/ backend/tests/test_analysis_gateways.py
git commit -m "feat(analysis): 상권·RAG·재무/매칭 아웃바운드 게이트웨이

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Gemini 리포트 작성기 + 모델 설정

**Files:**
- Create: `backend/apps/analysis/adapter/outbound/llm/__init__.py` (빈 파일)
- Create: `backend/apps/analysis/adapter/outbound/llm/gemini_report_writer.py`
- Modify: `backend/core/matrix/grid_keymaker_secret_manager.py` (`gemini_api_key` 줄 바로 아래 필드 1개)
- Modify: `backend/tests/test_settings_env_files.py` (테스트 1개 추가)
- Test: `backend/tests/test_analysis_gemini_writer.py`

**Interfaces:**
- Consumes: Task 3 `ReportWriterPort`
- Produces:
  - `Settings.gemini_report_model: str = "gemini-2.5-flash"`
  - `GeminiReportWriter(client, model: str)` — `client`는 `genai.Client` 호환 객체(`client.models.generate_content_stream(model=, contents=, config=)`)

- [ ] **Step 1: 실패 테스트 작성** — `backend/tests/test_analysis_gemini_writer.py`

```python
"""GeminiReportWriter — 가짜 클라이언트로 요청 구성·빈 조각 필터 검증 (네트워크 없음)."""

from types import SimpleNamespace

from apps.analysis.adapter.outbound.llm.gemini_report_writer import GeminiReportWriter


class _FakeModels:
    def __init__(self, texts: list[str | None]) -> None:
        self._texts = texts
        self.kwargs: dict = {}

    def generate_content_stream(self, **kwargs):
        self.kwargs = kwargs
        return iter(SimpleNamespace(text=text) for text in self._texts)


def test_stream_yields_non_empty_text_chunks_in_order():
    models = _FakeModels(["가", None, "", "나"])
    writer = GeminiReportWriter(client=SimpleNamespace(models=models), model="gemini-test")

    assert list(writer.stream("시스템 지시", "사용자 프롬프트")) == ["가", "나"]


def test_stream_sends_model_prompt_system_instruction_and_disables_thinking():
    models = _FakeModels(["가"])
    writer = GeminiReportWriter(client=SimpleNamespace(models=models), model="gemini-test")

    list(writer.stream("시스템 지시", "사용자 프롬프트"))

    assert models.kwargs["model"] == "gemini-test"
    assert models.kwargs["contents"] == "사용자 프롬프트"
    config = models.kwargs["config"]
    assert config.system_instruction == "시스템 지시"
    assert config.thinking_config.thinking_budget == 0
```

`backend/tests/test_settings_env_files.py` 끝에 추가:
```python
def test_settings_declares_gemini_report_model_with_default():
    assert Settings.model_fields["gemini_report_model"].default == "gemini-2.5-flash"
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analysis_gemini_writer.py tests/test_settings_env_files.py -q`
Expected: FAIL — `ModuleNotFoundError: ...gemini_report_writer`, `KeyError: 'gemini_report_model'`

- [ ] **Step 3: 설정 필드 추가** — `backend/core/matrix/grid_keymaker_secret_manager.py`

```python
    gemini_api_key: str = ""
    gemini_report_model: str = "gemini-2.5-flash"  # AI 리포트 생성 모델 — 환경변수 GEMINI_REPORT_MODEL 로 교체
```
(`gemini_api_key: str = ""` 줄을 위 두 줄로 바꾼다.)

- [ ] **Step 4: 작성기 구현** — 빈 `llm/__init__.py` 생성 후 `gemini_report_writer.py`

```python
"""Driven Adapter — Gemini 스트리밍 생성으로 ReportWriterPort 구현.

thinking_budget=0: 해석 문단 수준이라 추론 토큰 없이 첫 토큰 지연을 줄인다(2.5 Flash 계열 전제 —
모델을 바꾸면 해당 모델의 thinking 설정 지원 여부를 확인할 것).
"""

from collections.abc import Iterator

from google.genai import types

from apps.analysis.app.ports.output.analysis_port import ReportWriterPort

_TEMPERATURE = 0.3
_MAX_OUTPUT_TOKENS = 1024


class GeminiReportWriter(ReportWriterPort):
    def __init__(self, client, model: str) -> None:
        self._client = client
        self._model = model

    def stream(self, system: str, prompt: str) -> Iterator[str]:
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=_TEMPERATURE,
            max_output_tokens=_MAX_OUTPUT_TOKENS,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )
        for chunk in self._client.models.generate_content_stream(
            model=self._model, contents=prompt, config=config
        ):
            if chunk.text:
                yield chunk.text
```

- [ ] **Step 5: 통과 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analysis_gemini_writer.py tests/test_settings_env_files.py -q`
Expected: 전부 PASS (기존 settings 테스트 포함)

- [ ] **Step 6: 커밋**

```bash
git add backend/apps/analysis/adapter/outbound/llm/ backend/core/matrix/grid_keymaker_secret_manager.py backend/tests/test_analysis_gemini_writer.py backend/tests/test_settings_env_files.py
git commit -m "feat(analysis): Gemini 스트리밍 리포트 작성기와 리포트 모델 설정

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: 라우터·스키마·SSE 매퍼·Composition Root·앱 등록

**Files:**
- Create: `backend/apps/analysis/adapter/inbound/__init__.py`, `adapter/inbound/api/__init__.py`, `adapter/inbound/api/schemas/__init__.py`, `adapter/inbound/api/v1/__init__.py`, `adapter/inbound/mappers/__init__.py`, `backend/apps/analysis/dependencies/__init__.py` (빈 파일)
- Create: `backend/apps/analysis/adapter/inbound/api/schemas/analysis_schema.py`
- Create: `backend/apps/analysis/adapter/inbound/mappers/analysis_mapper.py`
- Create: `backend/apps/analysis/adapter/inbound/api/v1/analysis_router.py`
- Create: `backend/apps/analysis/dependencies/analysis_dependencies.py`
- Modify: `backend/main.py` (import 1줄 + `include_router` 1줄)
- Test: `backend/tests/test_analysis_router.py`

**Interfaces:**
- Consumes: Task 5 `AnalysisUseCase`·`build_interactor`, Task 6 게이트웨이, Task 7 작성기·설정, `apps.finance.adapter.inbound.api.schemas.finance_schema.SimulateRequest`, `apps.rag.dependencies.rag_dependencies.get_rag_search_use_case(provider)`, `apps.master.dependencies.region_dependencies.get_region_use_case()`, `apps.metric.dependencies.region_industry_metric_dependencies.get_risk_use_case()`, `core.matrix.grid_region_config.REGION_NAME`
- Produces:
  - `POST /analysis` → `{analysis_id}`; `GET /analysis/{analysis_id}/events` → `text/event-stream`; `GET /analysis/myself`
  - `get_analysis_use_case() -> AnalysisUseCase` (`lru_cache` 싱글턴)
  - `to_request(body: AnalysisStartRequest) -> AnalysisRequest`, `to_sse(event: AgentEvent) -> str`

- [ ] **Step 1: 실패 테스트 작성** — `backend/tests/test_analysis_router.py`

```python
"""/analysis API — POST 시작 → GET SSE 가 프론트 EventSource 계약대로 나오는지 (Fake 포트)."""

import json

from fastapi.testclient import TestClient

from apps.analysis.dependencies.analysis_dependencies import get_analysis_use_case
from main import app
from tests.analysis_fakes import FINANCE, build_interactor


def _client() -> TestClient:
    interactor = build_interactor()  # POST·GET 이 같은 저장소를 공유해야 한다
    app.dependency_overrides[get_analysis_use_case] = lambda: interactor
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        lines = dict(line.split(": ", 1) for line in block.split("\n"))
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def test_myself_is_wired():
    assert TestClient(app).get("/analysis/myself").json() == {"app": "analysis", "status": "wired"}


def test_post_returns_analysis_id():
    response = _client().post("/analysis", json={"region": "2711059500", "industry": "cafe"})
    assert response.status_code == 200
    assert len(response.json()["analysis_id"]) == 32


def test_events_stream_follows_frontend_eventsource_contract():
    client = _client()
    analysis_id = client.post(
        "/analysis", json={"region": "2711059500", "industry": "cafe", "question": "원두값 오르면?"}
    ).json()["analysis_id"]

    response = client.get(f"/analysis/{analysis_id}/events")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"
    assert "content-encoding" not in response.headers  # GZip 미들웨어가 스트림을 압축하지 않아야 한다
    events = _parse_sse(response.text)
    assert all(name == data["type"] for name, data in events)
    assert events[0] == ("agent_status", {"type": "agent_status", "agent": "orchestrator", "status": "running"})
    assert events[-1][0] == "report_done"
    assert events[-1][1]["report_id"] == analysis_id
    sections = [data["section"] for name, data in events if name == "report_delta"]
    assert sections[0] == "verdict"
    assert "calculator" not in sections


def test_finance_body_adds_calculator_section():
    client = _client()
    analysis_id = client.post(
        "/analysis", json={"region": "2711059500", "industry": "cafe", "finance": FINANCE}
    ).json()["analysis_id"]

    events = _parse_sse(client.get(f"/analysis/{analysis_id}/events").text)

    assert "calculator" in [data["section"] for name, data in events if name == "report_delta"]


def test_events_404_for_unknown_or_consumed_id():
    client = _client()
    analysis_id = client.post("/analysis", json={"region": "2711059500", "industry": "cafe"}).json()["analysis_id"]
    client.get(f"/analysis/{analysis_id}/events")

    for target in ("nope", analysis_id):
        response = client.get(f"/analysis/{target}/events")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "ANALYSIS_NOT_FOUND"


def test_post_rejects_missing_industry():
    assert _client().post("/analysis", json={"region": "2711059500"}).status_code == 422
```

- [ ] **Step 2: 실패 확인**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analysis_router.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'apps.analysis.dependencies'`

- [ ] **Step 3: 스키마** — 빈 `__init__.py` 6개 생성 후 `analysis_schema.py`

```python
from pydantic import BaseModel, Field

from apps.finance.adapter.inbound.api.schemas.finance_schema import SimulateRequest


class AnalysisStartRequest(BaseModel):
    """프론트 StartAnalysisParams {region, industry, question?} + 백엔드 선택 확장 finance."""

    region: str = Field(min_length=1)
    industry: str = Field(min_length=1)
    question: str | None = None
    finance: SimulateRequest | None = None


class AnalysisStartResponse(BaseModel):
    analysis_id: str
```

- [ ] **Step 4: 매퍼** — `analysis_mapper.py`

```python
"""Inbound Boundary Gate — schema → AnalysisRequest, AgentEvent → SSE 와이어 포맷.

와이어 포맷은 프론트 mock(src/app/api/mock/analysis/[id]/events/route.ts)과 동일:
event: <type>\\ndata: <JSON>\\n\\n  (JSON 이 개행을 이스케이프하므로 data 는 항상 한 줄)
"""

import json

from apps.analysis.adapter.inbound.api.schemas.analysis_schema import AnalysisStartRequest
from apps.analysis.domain.agent_event import AgentEvent
from apps.analysis.domain.analysis_context import AnalysisRequest


def to_request(body: AnalysisStartRequest) -> AnalysisRequest:
    return AnalysisRequest(
        region=body.region,
        industry=body.industry,
        question=body.question,
        finance=None if body.finance is None else body.finance.model_dump(),
    )


def to_sse(event: AgentEvent) -> str:
    return f"event: {event.TYPE}\ndata: {json.dumps(event.to_payload(), ensure_ascii=False)}\n\n"
```

- [ ] **Step 5: Composition Root** — `backend/apps/analysis/dependencies/analysis_dependencies.py`

```python
"""Composition Root (DIP) — analysis 포트에 어댑터를 주입한다.

lru_cache: 인메모리 요청 저장소가 POST↔GET 사이 상태를 들고 있으므로 프로세스당 1개 (단일 워커 전제).
"""

from functools import lru_cache

from google import genai

from apps.analysis.adapter.outbound.gateways.evidence_search_gateway import EvidenceSearchGateway
from apps.analysis.adapter.outbound.gateways.finance_gateways import (
    EngineSimulationGateway,
    ManualProductMatchingGateway,
)
from apps.analysis.adapter.outbound.gateways.market_data_gateway import MarketDataGateway
from apps.analysis.adapter.outbound.llm.gemini_report_writer import GeminiReportWriter
from apps.analysis.adapter.outbound.stores.in_memory_analysis_request_store import (
    InMemoryAnalysisRequestStore,
)
from apps.analysis.app.ports.input.analysis_use_case import AnalysisUseCase
from apps.analysis.app.use_cases.analysis_agents import FundingAgent, MarketAgent, ShockAgent
from apps.analysis.app.use_cases.analysis_interactor import AnalysisInteractor
from apps.analysis.app.use_cases.report_sections import default_sections
from apps.master.dependencies.region_dependencies import get_region_use_case
from apps.metric.dependencies.region_industry_metric_dependencies import get_risk_use_case
from apps.rag.dependencies.rag_dependencies import get_rag_search_use_case
from core.matrix.grid_keymaker_secret_manager import get_settings
from core.matrix.grid_region_config import REGION_NAME


@lru_cache
def get_analysis_use_case() -> AnalysisUseCase:
    settings = get_settings()
    # rag_chunk 는 전량 gemini-embedding-001 로 색인됨 — 질의 임베더도 같아야 한다 (기본 ollama 금지).
    search = EvidenceSearchGateway(get_rag_search_use_case(provider="gemini"))
    return AnalysisInteractor(
        store=InMemoryAnalysisRequestStore(),
        agents=[
            MarketAgent(MarketDataGateway(get_region_use_case(), get_risk_use_case())),
            ShockAgent(search, REGION_NAME),
            FundingAgent(search, EngineSimulationGateway(), ManualProductMatchingGateway(), REGION_NAME),
        ],
        sections=default_sections(REGION_NAME),
        writer=GeminiReportWriter(
            client=genai.Client(api_key=settings.gemini_api_key), model=settings.gemini_report_model
        ),
    )
```

- [ ] **Step 6: 라우터** — `backend/apps/analysis/adapter/inbound/api/v1/analysis_router.py`

```python
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from apps.analysis.adapter.inbound.api.schemas.analysis_schema import (
    AnalysisStartRequest,
    AnalysisStartResponse,
)
from apps.analysis.adapter.inbound.mappers.analysis_mapper import to_request, to_sse
from apps.analysis.app.ports.input.analysis_use_case import AnalysisUseCase
from apps.analysis.dependencies.analysis_dependencies import get_analysis_use_case
from apps.analysis.domain.errors import AnalysisNotFoundError

router = APIRouter(prefix="/analysis", tags=["analysis"])

# X-Accel-Buffering: 배포 시 리버스 프록시가 스트림을 모아 보내지 않도록.
_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


@router.get("/myself")
def myself() -> dict:
    return {"app": "analysis", "status": "wired"}


@router.post("", response_model=AnalysisStartResponse)
def start_analysis(
    body: AnalysisStartRequest,
    use_case: AnalysisUseCase = Depends(get_analysis_use_case),
) -> AnalysisStartResponse:
    return AnalysisStartResponse(analysis_id=use_case.start(to_request(body)))


@router.get("/{analysis_id}/events", response_model=None)
def stream_events(
    analysis_id: str,
    use_case: AnalysisUseCase = Depends(get_analysis_use_case),
) -> StreamingResponse | JSONResponse:
    """SSE — 동기 제너레이터는 Starlette 가 스레드풀에서 순회한다(DB·LLM 동기 호출 허용)."""
    try:
        events = use_case.stream(analysis_id)
    except AnalysisNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "ANALYSIS_NOT_FOUND", "message": f"분석 요청 없음 또는 이미 소비됨: {analysis_id}"}},
        )
    return StreamingResponse(
        (to_sse(event) for event in events), media_type="text/event-stream", headers=_SSE_HEADERS
    )
```

- [ ] **Step 7: 앱 등록** — `backend/main.py`

import 블록 맨 위(`finance_router` import 앞)에 추가:
```python
from apps.analysis.adapter.inbound.api.v1.analysis_router import router as analysis_router
```
`app.include_router(finance_router)` 바로 앞에 추가:
```python
app.include_router(analysis_router)
```

- [ ] **Step 8: 통과 확인 + 전체 회귀**

Run: `cd backend && .venv/bin/python -m pytest tests/test_analysis_router.py -q`
Expected: `6 passed`

Run: `cd backend && .venv/bin/python -m pytest tests/ -q`
Expected: 기준선 210 + 신규 53건(domain 7·report_text 12·agents 4·sections 6·interactor 8·gateways 7·gemini 2·settings 1·router 6) = `263 passed, 1 skipped`, 실패 0

Run: `cd backend && .venv/bin/python -c "from main import app; print(sorted(r.path for r in app.routes if r.path.startswith('/analysis')))"`
Expected: `['/analysis', '/analysis/myself', '/analysis/{analysis_id}/events']` (import 시 네트워크 호출 없음 — `lru_cache` 팩토리는 첫 요청에 실행)

- [ ] **Step 9: 커밋**

```bash
git add backend/apps/analysis/adapter/inbound/ backend/apps/analysis/dependencies/ backend/main.py backend/tests/test_analysis_router.py
git commit -m "feat(analysis): POST /analysis + GET /analysis/{id}/events SSE 라우터 등록

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: 프론트 AI 분석 탭 — mock 고정 해제, `config.apiBase` 사용

**Files:**
- Modify: `frontend/src/features/agent-report/hooks/use-agent-report.ts`
- Test: `frontend/src/features/agent-report/hooks/use-agent-report.test.ts` (세 번째 테스트 교체)

**Interfaces:**
- Consumes: `frontend/src/shared/config.ts`의 `config.apiBase`(`NEXT_PUBLIC_API_BASE ?? "/api/mock"`), `apiPost(path, body, base = config.apiBase)`
- Produces: `useAgentReport()` 시그니처 불변. 요청 URL `${config.apiBase}/analysis`, SSE `${config.apiBase}/analysis/${id}/events`. `NEXT_PUBLIC_API_BASE` 미설정 시 기존 mock 경로 그대로.

- [ ] **Step 1: 테스트 교체** — `use-agent-report.test.ts`의 마지막 테스트(`"NEXT_PUBLIC_API_BASE가 실 API여도 분석 요청·SSE는 mock 베이스를 유지한다"`) 전체를 아래로 바꾼다

```ts
it("분석 요청·SSE는 NEXT_PUBLIC_API_BASE(config.apiBase)를 따른다", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE", "http://localhost:8300");
  vi.resetModules();
  const { useAgentReport: freshUseAgentReport } = await import("./use-agent-report");

  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource as unknown as typeof EventSource);
  const fetchMock = stubFetch({ analysis_id: "abc" });

  const { result } = renderHook(() => freshUseAgentReport());

  act(() => {
    result.current.start({ region: "2711059500", industry: "cafe" });
  });
  await waitFor(() => expect(FakeEventSource.instances).toHaveLength(1));

  expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:8300/analysis");
  expect(FakeEventSource.instances[0].url).toBe("http://localhost:8300/analysis/abc/events");
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd frontend && npx vitest run src/features/agent-report/hooks/use-agent-report.test.ts`
Expected: FAIL — `expected '/api/mock/analysis' to be 'http://localhost:8300/analysis'`

- [ ] **Step 3: 구현** — `use-agent-report.ts`

import 추가(`apiPost` import 다음 줄):
```ts
import { config } from "@/shared/config";
```

아래 4줄(주석 2줄 + 상수 + 빈 줄) 삭제:
```ts
// TODO: RAG 분석 백엔드 미구현 — AI 분석 탭(분석 시작 POST + SSE)만 mock 베이스를 유지한다.
// 실 분석 API 전환 시 이 상수를 제거하고 config.apiBase로 복귀할 것.
const ANALYSIS_API_BASE = "/api/mock";
```

`start` 안의 두 줄을 교체:
```ts
      const { analysis_id } = await apiPost<{ analysis_id: string }>("/analysis", params);
      const source = new EventSource(`${config.apiBase}/analysis/${analysis_id}/events`);
```

- [ ] **Step 4: 통과 확인 + 전체 회귀**

Run: `cd frontend && npx vitest run src/features/agent-report`
Expected: 전부 PASS

Run: `cd frontend && npx vitest run && npx tsc --noEmit`
Expected: 84 passed(기준선과 동일 개수), tsc 출력 없음

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/features/agent-report/hooks/use-agent-report.ts frontend/src/features/agent-report/hooks/use-agent-report.test.ts
git commit -m "feat(frontend): AI 분석 탭 mock 고정 해제 — config.apiBase로 실백엔드 연결

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: 실연동 스모크 (실 Gemini 호출은 이 태스크에서만) + headless E2E + 문서

**Files:**
- Create: `frontend/tests/analysis.cjs`
- Modify: `docs/jekyll.md` (2026-09-17 섹션에 항목 추가 — 최신 날짜가 위)
- Modify: `docs/handoff.md` (§0 표의 `AI 리포트 SSE /analysis` 행 상태, §0-1 1번 항목)

**Interfaces:**
- Consumes: Task 8 엔드포인트, Task 9 프론트 전환, 실행 중인 :3300 dev 서버(`frontend/.env.local`의 `NEXT_PUBLIC_API_BASE=http://localhost:8300`)
- Produces: 실측 결과(이벤트 수·소요 시간·섹션·인용 수)를 devlog에 기록

- [ ] **Step 1: 사전 점검 (생성 호출 없음)**

Run: `cd backend && .venv/bin/python -c "from google import genai; from core.matrix.grid_keymaker_secret_manager import get_settings as g; s=g(); print(genai.Client(api_key=s.gemini_api_key).models.get(model=s.gemini_report_model).name)"`
Expected: `models/gemini-2.5-flash` 출력. 404/권한 오류면 **중단하고 사용자에게 모델명 결정 요청** (`backend/.env`에 `GEMINI_REPORT_MODEL=...`).

- [ ] **Step 2: 백엔드 재시작 — 사용자 승인 필수**

:8300 uvicorn은 `--reload`가 아니라 새 라우트를 반영하려면 재시작해야 한다. **사용자에게 재시작 승인을 받은 뒤에만** 실행:
```bash
pkill -f "uvicorn main:app --host 0.0.0.0 --port 8300"
cd /home/kimchungsik/projects/cloud.localhostdaegu/backend && nohup .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8300 > ../logs/uvicorn.log 2>&1 &
```
준비 확인(HTTP 폴링, 브라우저 금지): `curl -s --retry 20 --retry-connrefused --retry-delay 1 http://localhost:8300/health`
Expected: `{"status":"ok"}` 그리고 `curl -s http://localhost:8300/analysis/myself` → `{"app":"analysis","status":"wired"}`

- [ ] **Step 3: curl 스모크 — 실 Gemini 1회**

```bash
ID=$(curl -s -X POST http://localhost:8300/analysis -H 'Content-Type: application/json' \
  -d '{"region":"2711059500","industry":"cafe"}' | .venv/bin/python -c 'import sys,json;print(json.load(sys.stdin)["analysis_id"])')
time curl -sN --max-time 180 http://localhost:8300/analysis/$ID/events > /tmp/analysis-smoke.txt
grep -c '^event: ' /tmp/analysis-smoke.txt; grep '^event: ' /tmp/analysis-smoke.txt | sort | uniq -c; tail -2 /tmp/analysis-smoke.txt
```
(위 명령은 `backend/` 디렉터리에서 실행.) Expected:
- 마지막 이벤트 `event: report_done`, citations 1건 이상(URL 있는 공고·뉴스)
- `agent_status`에 `"status": "error"` 없음 (있으면 `logs/uvicorn.log`의 `localhostdaegu.analysis` 스택으로 원인 확인 → systematic-debugging)
- `report_delta` section에 verdict·market·shock·funding, 폴백 문구("AI 해석을 생성하지 못했습니다") 없음
- 첫 줄 verdict에 "대신동 카페 · 위험도 …점" (코드가 쓴 수치), 소요 시간 기록
- 리포트 본문에 "서울" 문자열 없음: `grep -c 서울 /tmp/analysis-smoke.txt` → `0`

- [ ] **Step 4: headless E2E 스크립트 작성** — `frontend/tests/analysis.cjs`

```js
#!/usr/bin/env node
/**
 * AI 분석 E2E 스모크 (headless). 실행 중인 :3300 dev 서버를 재사용한다(E2E_REUSE_SERVER=1 전용 — 서버를 띄우거나 끄지 않는다).
 *
 * 여정: /analysis?region=2711059500&industry=cafe → [분석 시작]
 *      → POST {API_BASE}/analysis 가 기대 베이스로 나감 → 오케스트레이터 "완료"
 *      → 리포트 제목 4개(종합 진단·상권 진단·충격 분석·정책자금) + 에러 alert 없음.
 *
 * 실백엔드: E2E_REUSE_SERVER=1 E2E_API_BASE=http://localhost:8300 node tests/analysis.cjs
 * 루트 CLAUDE.md 브라우저 규약: headless: true, 서버 준비 확인은 HTTP, try/finally 로 브라우저 정리, /analysis 재로드 금지.
 */
const http = require("http");
const { chromium } = require("playwright");

const BASE_URL = "http://localhost:3300";
const API_BASE = process.env.E2E_API_BASE || "/api/mock";
const EXPECTED_POST_URL = API_BASE.startsWith("http") ? `${API_BASE}/analysis` : `${BASE_URL}${API_BASE}/analysis`;
const REPORT_TIMEOUT_MS = 180_000; // 실 Gemini 4섹션 순차 스트림
const HEADINGS = ["종합 진단", "상권 진단", "충격 분석", "정책자금"];

let failed = false;

function step(label, ok, detail) {
  console.log(`[${ok ? "PASS" : "FAIL"}] ${label}${detail ? " — " + detail : ""}`);
  if (!ok) failed = true;
  return ok;
}

function checkServer(url) {
  return new Promise((resolve, reject) => {
    http
      .get(url, (res) => {
        res.resume();
        res.statusCode && res.statusCode < 500 ? resolve() : reject(new Error(`status ${res.statusCode}`));
      })
      .on("error", reject);
  });
}

async function main() {
  if (process.env.E2E_REUSE_SERVER !== "1") {
    console.log("E2E_REUSE_SERVER=1 로 실행 중인 :3300 서버에 대해서만 실행한다.");
    process.exit(2);
  }
  let browser = null;
  try {
    await checkServer(BASE_URL);
    step("dev 서버 응답", true, BASE_URL);

    browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const postUrls = [];
    page.on("request", (req) => {
      if (req.method() === "POST" && req.url().endsWith("/analysis")) postUrls.push(req.url());
    });

    await page.goto(`${BASE_URL}/analysis?region=2711059500&industry=cafe`, { waitUntil: "networkidle" });
    const started = Date.now();
    await page.getByRole("button", { name: "분석 시작" }).click();

    await page
      .locator("li", { hasText: "오케스트레이터" })
      .filter({ hasText: "완료" })
      .waitFor({ state: "visible", timeout: REPORT_TIMEOUT_MS });
    step("오케스트레이터 완료", true, `${((Date.now() - started) / 1000).toFixed(1)}초`);

    step("분석 요청 베이스", postUrls[0] === EXPECTED_POST_URL, `${postUrls[0]} (기대 ${EXPECTED_POST_URL})`);
    for (const name of HEADINGS) {
      step(`리포트 제목 "${name}"`, (await page.getByRole("heading", { name }).count()) > 0);
    }
    step("에러 alert 없음", (await page.getByRole("alert").count()) === 0);
    const citations = await page.getByRole("heading", { name: "참고 자료" }).count();
    step("참고 자료 블록", citations > 0);
  } catch (err) {
    step("예외 발생", false, err && err.stack ? err.stack : String(err));
  } finally {
    if (browser) await browser.close().catch(() => {});
  }
  console.log(failed ? "RESULT: FAIL" : "RESULT: PASS");
  process.exit(failed ? 1 : 0);
}

main();
```

- [ ] **Step 5: E2E 실행 — 실 Gemini 1회 (UI 경유)**

Run: `cd frontend && E2E_REUSE_SERVER=1 E2E_API_BASE=http://localhost:8300 node tests/analysis.cjs`
Expected: 모든 줄 `[PASS]`, `RESULT: PASS`, 분석 요청 베이스 `http://localhost:8300/analysis`. 실패 시 이 스크립트를 재실행하기 전에 원인부터 확인(재실행마다 Gemini 호출이 발생한다).

- [ ] **Step 6: 기존 깔때기 회귀**

Run: `cd frontend && E2E_REUSE_SERVER=1 E2E_API_BASE=http://localhost:8300 node tests/funnel.cjs`
Expected: `RESULT: PASS`

- [ ] **Step 7: 문서 갱신**

`docs/jekyll.md`의 `## 2026-09-17` 아래에 `### 백엔드·프론트 — AI 리포트 /analysis SSE` 소제목으로 항목을 추가한다(날짜 섹션은 최신이 위, 실측·미결 포함). 기록할 것: 엔드포인트 2종·이벤트 계약, 질의 임베더 gemini 고정 이유, curl 스모크 실측(이벤트 수·소요 초·인용 수·에러 유무), E2E 결과, pytest/vitest 통과 수, 남은 미결(매칭 수기 JSON 자리표시자로 상품 0건일 수 있음, 인메모리 저장소 단일 워커 전제).

`docs/handoff.md` §0 표 `**AI 리포트 SSE /analysis**` 행을 `✅ 완료 (9/17)` + 한 줄 요약으로, §0-1의 1번 항목을 완료 표기로 바꾼다.

- [ ] **Step 8: 커밋**

```bash
git add frontend/tests/analysis.cjs docs/jekyll.md docs/handoff.md
git commit -m "test(e2e): AI 분석 실백엔드 스모크 스크립트 + devlog·handoff 갱신

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

## 미결 사항 (실행 전 사용자 확인 권장)

1. **리포트 생성 모델** — 기본 `gemini-2.5-flash`(thinking_budget=0). 계정에서 더 최신 Flash 모델을 쓸 수 있으면 `GEMINI_REPORT_MODEL`로 교체. 교체 시 thinking 설정 호환 확인 (Task 10 Step 1에서 존재 여부만 검증).
2. **finance 선택 필드** — 프론트 분석 폼은 region·industry·question만 보내므로 현재 화면에서는 `calculator` 섹션이 나오지 않고 매칭은 funding_gap=0 기준. 시뮬레이터 결론 → AI 리포트 CTA(재무 입력 전달)는 이 계획 범위 밖.
3. **백엔드 재시작 승인** — :8300은 `--reload`가 아니라 Task 10 Step 2에서 재시작이 필요하다.

## 예상 위험

- **매칭 상품이 비어 보일 수 있음**: `data/manual/*.json`이 `[확인]` 자리표시자이고 category 값(`general_restaurants` 등)이 현재 업종 id(`cafe` 등)와 달라 매칭이 0건일 수 있다. 다른 에이전트가 수기 JSON을 작업 중이므로 이 계획에서는 손대지 않는다(`load_all_products`는 `lru_cache` — JSON 갱신 후 백엔드 재시작 필요).
- **지연**: RAG 질의 임베딩 2회 + LLM 스트림 4회 순차 → 수십 초 예상. 섹션 첫머리는 코드가 즉시 내보내 체감 지연을 줄인다. E2E 타임아웃 180초.
- **RAG 관련성**: 검색에 지역·기간 필터가 없어 전국·오래된 뉴스가 섞일 수 있다(만료 공고만 제외). 프롬프트가 "문서 없으면 없다고" 쓰게 해 환각을 줄인다.
- **인메모리 저장소**: 단일 uvicorn 워커 전제. 배포에서 워커를 늘리면 POST와 GET이 다른 워커로 가 404가 난다 → Redis 어댑터로 교체 필요.
- **배포 프록시 버퍼링**: `X-Accel-Buffering: no`를 넣었지만 Cloudflare Tunnel 등에서 SSE가 모아서 도착할 수 있다. 배포 후 별도 확인 필요.
- **EventSource 재연결**: 요청을 1회 소비하므로 연결이 끊긴 뒤 재연결하면 404가 난다. 프론트는 `onerror`에서 곧바로 닫고 에러를 표시하므로 LLM 중복 호출은 없다.
