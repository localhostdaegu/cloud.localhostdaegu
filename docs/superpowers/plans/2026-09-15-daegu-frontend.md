# localhostdaegu 프론트엔드 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Metabole 프론트를 이식·대구화하고, 채팅 랜딩 → 지도 진단 → 시뮬레이터 → 금융 매칭의 "한 문장 깔때기" UI를 완성한다.

**Architecture:** Metabole 프론트(Next.js 16 + maplibre-gl map-explorer + agent-report + mock API 라우트)가 뼈대. 핵심 설계 자산 두 개를 그대로 활용한다 — ① `MapPage`는 이미 URL 파라미터⇔상태 동기화 구조이므로 채팅 랜딩은 의도 추출 결과로 URL만 만들어 넘긴다(기획서 §4 관문형). ② `config.apiBase`가 env로 `/api/mock` ↔ 실백엔드(8300)를 전환하므로 백엔드 완성 전에도 mock으로 전 화면을 개발한다.

**Tech Stack:** Next.js 16 · React 19 · TypeScript 5 · Tailwind 4 · @tanstack/react-query · maplibre-gl · vitest (+Task 7에서만 recharts 추가)

**Spec:** `docs/daegunavi.md` §4(사용자 흐름)·§7-1(믹스 전략) + `docs/apilist.md` + 백엔드 계획 `2026-09-15-daegu-backend-port.md`의 API 계약(Task 6~9 Interfaces)

## Global Constraints

- dev 서버 포트 **3300** — 서버 기동이 브라우저를 열면 안 됨 (루트 CLAUDE.md 브라우저 규칙: `open`/`xdg-open` 금지, 준비 확인은 HTTP 요청)
- 자동 UI 검증은 `frontend/tests/*.cjs` Playwright **headless** 스크립트만
- 원본 `~/projects/cloud.beyondfacade/frontend`는 **읽기 전용**
- `frontend/.env.local`의 기존 항목 보존. `NEXT_PUBLIC_API_BASE=/api/mock`(개발) → `http://localhost:8300`(연동 시)
- 대구 중심좌표 (128.60, 35.87) / 8개 구·군 (27110 중구 · 27140 동구 · 27170 서구 · 27200 남구 · 27230 북구 · 27260 수성구 · 27290 달서구 · 27710 달성군)
- 백엔드 API 계약 (백엔드 계획 산출): `POST /intent {text}→{intent_type,district_code,industry_slug,budget_krw,missing[]}` · `GET /metrics/risk?industry=&region_code=→{score,grade,components}` · `POST /finance/simulate→{capex,monthly_fixed,bep_revenue,funding_gap,scenarios[3],stress[2]}` · `GET /matching?funding_gap=&category=&business_age_months=&owner_age=→상품배열`
- 업종 slug 7종: `general_restaurants, rest_cafes, beauty_salons, fitness_centers, billiard_halls, karaoke_rooms, pc_bangs`
- 신규 npm 의존성은 Task 7의 recharts 외 금지

---

### Task 1: Metabole 프론트 이식 — 복사·포트 3300·vitest 그린

**Files:**
- Create: `frontend/src/`, `frontend/public/`, `frontend/package.json`, `frontend/next.config.ts`, `frontend/tsconfig.json`, `frontend/postcss.config.mjs`, `frontend/vitest.config.ts` (SRC=`~/projects/cloud.beyondfacade/frontend`에서 복사)
- Modify: `frontend/package.json` (dev/start 포트 3200→3300), `frontend/.env.local` (기존 파일에 키 추가)
- 보존: `frontend/.gitignore`, `frontend/CLAUDE.md`, `frontend/AGENTS.md`

- [ ] **Step 1: 복사**

```bash
cd /home/kimchungsik/projects/cloud.localhostdaegu
SRC=~/projects/cloud.beyondfacade/frontend
rsync -a --exclude='node_modules' --exclude='.next' --exclude='.env.local' --exclude='.gitignore' \
  --exclude='CLAUDE.md' --exclude='AGENTS.md' --exclude='Dockerfile' --exclude='docs' \
  $SRC/ frontend/
```

- [ ] **Step 2: 포트 변경** — `frontend/package.json` scripts: `"dev": "next dev -p 3300"`, `"start": "next start -p 3300"`
- [ ] **Step 3: env** — `frontend/.env.local`에 추가(기존 내용 유지): `NEXT_PUBLIC_API_BASE=/api/mock`, `NEXT_PUBLIC_VWORLD_KEY=` (SRC의 .env.local 값 복사 — 브이월드 키는 도메인 등록 이슈로 localhost 사용 가능 `[확인]`)
- [ ] **Step 4: 설치·테스트** — `cd frontend && npm install && npm test` → 기존 vitest 전부 PASS
- [ ] **Step 5: dev 기동 확인 (브라우저 열지 않음)** — `npm run dev &` 후 `curl -s -o /dev/null -w '%{http_code}' http://localhost:3300` → 200, 서버 종료
- [ ] **Step 6: Commit** — `git add frontend && git commit -m "feat: port Metabole frontend (map-explorer, agent-report, mocks)"`

---

### Task 2: 대구화 — 중심좌표·mock 데이터·브랜딩

**Files:**
- Create: `frontend/src/shared/daegu.ts`
- Modify: `frontend/src/features/map-explorer/components/map-view.tsx` (`SEOUL_CENTER` 사용부), `frontend/src/app/api/mock/fixtures.ts`, `frontend/src/app/api/mock/regions/geojson/route.ts`, `frontend/src/shared/ui/top-bar.tsx` (브랜드명), `frontend/src/app/layout.tsx` (metadata title)
- Test: `frontend/src/shared/daegu.test.ts`

**Interfaces:**
- Produces: `DAEGU_CENTER: [128.60, 35.87]`, `DISTRICTS: Record<code, {name, center: [lng,lat]}>` 8개 — Task 3 라우팅과 Task 4 줌이 소비

- [ ] **Step 1: 실패 테스트** — `daegu.test.ts`

```ts
import { DAEGU_CENTER, DISTRICTS } from "./daegu";

test("daegu has 8 districts without gunwi", () => {
  expect(Object.keys(DISTRICTS)).toHaveLength(8);
  expect(DISTRICTS["27720"]).toBeUndefined();
  expect(DISTRICTS["27110"].name).toBe("중구");
});
test("center is in daegu bbox", () => {
  const [lng, lat] = DAEGU_CENTER;
  expect(lng).toBeGreaterThan(128.35); expect(lng).toBeLessThan(128.77);
  expect(lat).toBeGreaterThan(35.6); expect(lat).toBeLessThan(36.02);
});
```

- [ ] **Step 2: 실패 확인** — `npm test -- daegu` → FAIL
- [ ] **Step 3: 구현** — `frontend/src/shared/daegu.ts`

```ts
export const DAEGU_CENTER: [number, number] = [128.60, 35.87];
export const DISTRICTS: Record<string, { name: string; center: [number, number] }> = {
  "27110": { name: "중구", center: [128.606, 35.869] },
  "27140": { name: "동구", center: [128.635, 35.887] },
  "27170": { name: "서구", center: [128.559, 35.872] },
  "27200": { name: "남구", center: [128.598, 35.846] },
  "27230": { name: "북구", center: [128.583, 35.885] },
  "27260": { name: "수성구", center: [128.630, 35.858] },
  "27290": { name: "달서구", center: [128.533, 35.830] },
  "27710": { name: "달성군", center: [128.431, 35.775] },
};
export const INDUSTRY_LABELS: Record<string, string> = {
  general_restaurants: "일반음식점", rest_cafes: "카페·휴게음식점", beauty_salons: "미용실",
  fitness_centers: "헬스장", billiard_halls: "당구장", karaoke_rooms: "노래방", pc_bangs: "PC방",
};
```

- [ ] **Step 4: 그린 확인** → PASS
- [ ] **Step 5: 적용** — map-view의 `SEOUL_CENTER` 상수를 `DAEGU_CENTER` import로 교체(식별자명도 교체), top-bar 브랜드명 → "localhostdaegu", layout metadata title → "localhostdaegu — 대구 창업 금융 네비게이터"
- [ ] **Step 6: mock 대구화** — mock fixtures의 지역 코드·명칭을 대구 행정동 3~5개(성내1동·대신동·상동 등, 코드 `27110…` 체계)로 교체, mock geojson은 해당 동 위치의 단순 사각 폴리곤 스텁으로 (실 경계는 백엔드 `/regions/geojson` 연동 시 대체 — mock은 화면 개발용)
- [ ] **Step 7: 전체 테스트 + dev 스모크** — `npm test` 그린, dev 기동 후 `curl localhost:3300` 200
- [ ] **Step 8: Commit** — `git commit -m "feat: daegu-ize frontend (center, districts, mocks, branding)"`

---

### Task 3: 채팅 랜딩 (⓪①) — 한 문장 → URL 상태 → /map

**Files:**
- Create: `frontend/src/features/intent-gate/components/chat-landing.tsx`, `frontend/src/features/intent-gate/lib/intent-url.ts`, `frontend/src/features/intent-gate/api.ts`, `frontend/src/app/map/page.tsx`
- Modify: `frontend/src/app/page.tsx` (홈=랜딩으로 교체), `frontend/src/features/map-explorer/lib/map-state.ts` (`district`·`budget` 파라미터 추가)
- Test: `frontend/src/features/intent-gate/lib/intent-url.test.ts`

**Interfaces:**
- Consumes: `POST /intent` (백엔드 계약 — mock 라우트도 이 태스크에서 추가: `frontend/src/app/api/mock/intent/route.ts`)
- Produces: `intentToUrl(intent): string` — `/map?district=27110&industry=rest_cafes&budget=50000000` 형태. MapPage가 `district`로 줌, Task 5가 `budget` 소비

- [ ] **Step 1: 실패 테스트** — `intent-url.test.ts`

```ts
import { intentToUrl } from "./intent-url";

test("full intent A routes to map with all params", () => {
  expect(intentToUrl({ intent_type: "A", district_code: "27260", industry_slug: "rest_cafes",
    budget_krw: 50_000_000, missing: [] }))
    .toBe("/map?district=27260&industry=rest_cafes&budget=50000000");
});
test("type B omits industry", () => {
  expect(intentToUrl({ intent_type: "B", district_code: "27110", industry_slug: null,
    budget_krw: null, missing: ["industry", "budget"] }))
    .toBe("/map?district=27110");
});
test("type C without region stays on daegu overview", () => {
  expect(intentToUrl({ intent_type: "C", district_code: null, industry_slug: "rest_cafes",
    budget_krw: 50_000_000, missing: ["region"] }))
    .toBe("/map?industry=rest_cafes&budget=50000000");
});
```

- [ ] **Step 2: 실패 확인** → FAIL
- [ ] **Step 3: 구현** — `intent-url.ts`

```ts
export interface IntentResult {
  intent_type: "A" | "B" | "C";
  district_code: string | null;
  industry_slug: string | null;
  budget_krw: number | null;
  missing: string[];
}

export function intentToUrl(r: IntentResult): string {
  const p = new URLSearchParams();
  if (r.district_code) p.set("district", r.district_code);
  if (r.industry_slug) p.set("industry", r.industry_slug);
  if (r.budget_krw) p.set("budget", String(r.budget_krw));
  const q = p.toString();
  return q ? `/map?${q}` : "/map";
}
```

- [ ] **Step 4: 그린 확인** → PASS
- [ ] **Step 5: 랜딩 컴포넌트** — `chat-landing.tsx`: 중앙 정렬 입력창 + 헤드라인 "무엇을 알아볼까요?" + 예시 칩 3개(`서문시장 근처 카페, 예산 5천` / `동성로에 미용실` / `예산 5천이면 뭐 하지?` — 클릭 시 입력창에 채움) + 하단 "지도에서 직접 둘러보기 →" 링크(`/map`). 제출 시 `api.ts`의 `parseIntent(text)`(POST /intent) 호출 → `missing`에 region이 포함되고 intent_type이 C가 아니면… 없음 — 단순 규칙: **industry가 missing이면 업종 칩 7개를 입력창 아래 노출**해 선택 후 재제출, 그 외에는 `router.push(intentToUrl(result))`. react-query mutation 사용, 로딩 중 버튼 비활성.
- [ ] **Step 6: mock 라우트** — `app/api/mock/intent/route.ts`: 요청 text에 "서문시장" 포함→A/27110/rest_cafes, "동성로"→27110, "예산"만→C … 백엔드 파서의 축약 미러 (하드코딩 3케이스면 충분 — mock은 화면 개발용)
- [ ] **Step 7: 라우팅 재배치** — `app/page.tsx`→`<ChatLanding/>`, `app/map/page.tsx`→기존 홈 내용(`<MapPage/>` Suspense 래핑). `map-state.ts`의 parse/serialize에 `district`·`budget` 옵션 필드 추가(없으면 생략). MapPage: `district` 있고 `region` 없으면 `DISTRICTS[district].center`로 `map.flyTo(zoom 13)` 1회 실행.
- [ ] **Step 8: 검증** — `npm test` 그린 + dev 기동 후 curl로 `/`(200)·`/map`(200) 확인
- [ ] **Step 9: Commit** — `git commit -m "feat: chat landing with intent gate and URL handoff"`

---

### Task 4: 진단 무대 확장 (②) — 위험도 카드·업종 랭킹

**Files:**
- Create: `frontend/src/features/map-explorer/components/risk-card.tsx`, `frontend/src/app/api/mock/metrics/risk/route.ts`
- Modify: `frontend/src/features/map-explorer/components/side-panel.tsx` (risk-card 삽입), `frontend/src/shared/api/types.ts` (RiskScore 타입 추가)
- Test: `frontend/src/features/map-explorer/components/risk-card.test.tsx`

**Interfaces:**
- Consumes: `GET /metrics/risk?industry=&region_code=` → `{score: number, grade: "red"|"yellow"|"green", components: {closure, density, growth}}` (region_code 미지정 시 배열 — 랭킹)
- Produces: `<RiskCard score grade components/>` — side-panel 상단 삽입. industry 미지정(B유형) 시 side-panel이 업종 랭킹 리스트 렌더

- [ ] **Step 1: 실패 테스트** — `risk-card.test.tsx`

```tsx
import { render, screen } from "@testing-library/react";
import { RiskCard } from "./risk-card";

test("renders score, grade label, and three components", () => {
  render(<RiskCard score={68} grade="yellow" components={{ closure: 30, density: 28, growth: 10 }} />);
  expect(screen.getByText("68")).toBeInTheDocument();
  expect(screen.getByText("진입 주의")).toBeInTheDocument();   // yellow=주의, red=고위험, green=양호
  expect(screen.getByText(/폐업률/)).toBeInTheDocument();
  expect(screen.getByText(/경쟁밀도/)).toBeInTheDocument();
  expect(screen.getByText(/신규진입/)).toBeInTheDocument();
});
```

- [ ] **Step 2: 실패 확인** → FAIL
- [ ] **Step 3: 구현** — RiskCard: 큰 숫자 + 등급 뱃지(red `진입 고위험`/yellow `진입 주의`/green `진입 양호` — grade-badge.tsx 스타일 관행 재사용) + 구성요소 3개 미니 바(폐업률·경쟁밀도·신규진입, 각 기여 점수 표기). 색은 기존 테마 토큰.
- [ ] **Step 4: 그린 확인** → PASS
- [ ] **Step 5: 연결** — side-panel: region+industry 있으면 react-query로 risk 단건 fetch→RiskCard. industry 없으면(B유형) 같은 엔드포인트 region_code 지정·업종 7종 각각 호출 대신 **`GET /metrics/risk?region_code=` 1회로 업종별 배열 응답을 받아** 랭킹 리스트 렌더(높은 score부터, 클릭 시 industry 파라미터 설정) — mock 라우트가 이 두 형태 모두 응답. ※ 백엔드 risk API가 region 단건×업종 배열 형태를 지원하는지 백엔드 Task 7 산출로 확인 — 미지원이면 7회 병렬 호출로 구현하고 백엔드에 배열 지원을 후속 요청 `[컨트롤러 확인]`
- [ ] **Step 6: 검증·Commit** — `npm test` 그린 → `git commit -m "feat: risk card and industry ranking in side panel"`

---

### Task 5: 시뮬레이터 (③) — 프리필 확인 폼

**Files:**
- Create: `frontend/src/features/simulator/components/simulator-form.tsx`, `frontend/src/features/simulator/lib/form-defaults.ts`, `frontend/src/app/simulate/page.tsx`, `frontend/src/app/api/mock/finance/simulate/route.ts`
- Test: `frontend/src/features/simulator/lib/form-defaults.test.ts`
- Modify: `frontend/src/features/map-explorer/components/side-panel.tsx` (CTA 버튼 "이 자리에서 시뮬레이션" → `/simulate?` + 현재 URL 파라미터 승계)

**Interfaces:**
- Consumes: URL `?district=&industry=&budget=`, `POST /finance/simulate` (백엔드 계약의 FinanceInput 필드명 그대로)
- Produces: 시뮬레이션 요청 페이로드 + 응답을 `/simulate` 화면 하단 결과 섹션에 전달 (Task 6이 결과 섹션 구현)

- [ ] **Step 1: 실패 테스트** — `form-defaults.test.ts`

```ts
import { buildDefaults } from "./form-defaults";

test("budget from url becomes equity default", () => {
  const d = buildDefaults({ budget: "50000000", industry: "rest_cafes" });
  expect(d.equity).toBe(50_000_000);
  expect(d.cost_ratio).toBe(0.35);           // 카페 기본 원가율
});
test("industry benchmark cost ratios", () => {
  expect(buildDefaults({ industry: "general_restaurants" }).cost_ratio).toBe(0.40);
  expect(buildDefaults({}).cost_ratio).toBe(0.40);   // 미지정 기본
});
```

- [ ] **Step 2: 실패 확인** → FAIL
- [ ] **Step 3: 구현** — `form-defaults.ts`: URL 파라미터 → FinanceInput 초기값. 업종별 기본 원가율 딕셔너리(음식점 0.40, 카페 0.35, 미용실 0.25, 헬스장 0.15, 당구장·노래방·PC방 0.20 — 소상공인 실태조사 근사, 사용자 수정 가능이 전제), `fee_ratio: 0.03`, `loan_rate: 0.045`, 나머지 0.
- [ ] **Step 4: 그린 확인** → PASS
- [ ] **Step 5: 폼 + 페이지** — simulator-form: 섹션 2개 — "확인해주세요"(프리필: 자기자본=budget, 원가율·수수료율·금리) / "입력해주세요"(보증금·권리금·인테리어·설비·월세·인건비·보험·희망대출·예상 월매출). 숫자 입력은 만원 단위 표시. 제출 → `apiPost("/finance/simulate", payload)` → 결과를 같은 페이지 하단에 (Task 6). mock 라우트는 백엔드 계약 형태의 고정 응답.
- [ ] **Step 6: CTA 연결** — side-panel 하단 버튼 → `/simulate?${searchParams}` 승계
- [ ] **Step 7: 검증·Commit** — `npm test` 그린 → `git commit -m "feat: prefilled simulator form"`

---

### Task 6: 결론 화면 (④) — 3시나리오·Funding Gap·금융 매칭

**Files:**
- Create: `frontend/src/features/simulator/components/result-view.tsx`, `frontend/src/features/simulator/components/matching-cards.tsx`, `frontend/src/app/api/mock/matching/route.ts`
- Test: `frontend/src/features/simulator/components/result-view.test.tsx`
- Modify: `frontend/src/app/simulate/page.tsx` (결과 연결)

**Interfaces:**
- Consumes: `/finance/simulate` 응답, `GET /matching?funding_gap=&category=&business_age_months=0&owner_age=`
- Produces: 결론 한 화면 — 기획서 §4 ④ 그대로

- [ ] **Step 1: 실패 테스트** — `result-view.test.tsx`

```tsx
import { render, screen } from "@testing-library/react";
import { ResultView } from "./result-view";

const RESULT = {
  capex: 60_000_000, monthly_fixed: 8_575_000, bep_revenue: 15_043_859, funding_gap: 20_000_000,
  scenarios: [
    { name: "비관", monthly_revenue: 12_000_000, variable_cost: 5_160_000, operating_profit: -1_735_000, payback_months: null, runway_months: 5.8 },
    { name: "기준", monthly_revenue: 20_000_000, variable_cost: 8_600_000, operating_profit: 2_825_000, payback_months: 21.2, runway_months: null },
    { name: "낙관", monthly_revenue: 32_000_000, variable_cost: 13_760_000, operating_profit: 9_665_000, payback_months: 6.2, runway_months: null },
  ],
  stress: [{ rate_delta: 0.01, monthly_fixed: 8_591_666, base_operating_profit: 2_808_334 }],
};

test("renders three scenarios and funding gap headline", () => {
  render(<ResultView result={RESULT} />);
  expect(screen.getByText("비관")).toBeInTheDocument();
  expect(screen.getByText("낙관")).toBeInTheDocument();
  expect(screen.getByText(/부족한 2,000만원/)).toBeInTheDocument();
});
test("runway shown for loss scenario, payback for profit", () => {
  render(<ResultView result={RESULT} />);
  expect(screen.getByText(/5.8개월/)).toBeInTheDocument();     // 비관 runway
  expect(screen.getByText(/21.2개월/)).toBeInTheDocument();    // 기준 회수
});
```

- [ ] **Step 2: 실패 확인** → FAIL
- [ ] **Step 3: 구현** — ResultView: 상단 요약 스트립(CAPEX·월고정비·BEP매출) → 시나리오 3열 카드(월매출·영업이익·회수기간 또는 Runway, 비관=적자 시 빨강) → **Funding Gap 헤드라인** "부족한 N만원, 이렇게 메울 수 있어요"(gap=0이면 "자기자본으로 충분해요" + 매칭 생략) → `<MatchingCards fundingGap category/>`. MatchingCards: react-query로 `/matching` fetch, provider_type 뱃지(보증=파랑·은행=초록·정책=보라), 각 카드에 한도·금리·기관·상세 링크.
- [ ] **Step 4: 그린 확인** → PASS
- [ ] **Step 5: 금액 표기 유틸** — 원 단위 int → "2,000만원"/"1.2억원" 포맷 함수(`shared/format.ts`, 테스트 포함: 20_000_000→"2,000만원", 120_000_000→"1.2억원")
- [ ] **Step 6: 검증·Commit** — `npm test` 그린 → `git commit -m "feat: simulation result with funding-gap matching cards"`

---

### Task 7 (P1, 선택): redoceanmap 진단 차트 이식

- [ ] `gh api`로 `jangminseok-dev/com.redoceanmap` 저장소 `www/components/market/PopulationCharts.tsx`·`SalesTrendChart.tsx` 소스 확보 → `frontend/src/features/map-explorer/components/`에 이식, `npm i recharts`
- [ ] 데이터 소스를 우리 `/metrics` 응답(연도별 시계열)에 맞춰 어댑트 — 개폐업 추이 차트로 용도 변경 (매출 데이터는 로드맵)
- [ ] side-panel에 삽입, 컴포넌트 테스트 1개, Commit
- 판단 기준: Task 1~6 완료 후 여력 있을 때만. 스타일 충돌(shadcn 클래스) 시 차트 로직만 취하고 마크업은 기존 관행으로 재작성

---

### Task 8: 깔때기 E2E 스모크 (headless)

**Files:**
- Create: `frontend/tests/funnel.cjs` (Playwright headless — 루트 CLAUDE.md 규약)

- [ ] **Step 1: 스크립트 작성** — `funnel.cjs`: headless chromium으로 ①`/` 접속→입력창에 "서문시장 근처 카페, 예산 5천" 입력→제출→②URL이 `/map?district=27110…`인지 assert→③시뮬레이션 CTA 클릭→`/simulate` 도달→④폼 제출(mock)→"부족한" 텍스트 노출 assert. `try/finally`로 브라우저·서버 정리. mock API 기준(`NEXT_PUBLIC_API_BASE=/api/mock`).
- [ ] **Step 2: 실행** — `node frontend/tests/funnel.cjs` → PASS 출력 확인
- [ ] **Step 3: Commit** — `git commit -m "test: headless funnel e2e"`

---

### 최종 검증 게이트

- [ ] `npm test` 전체 그린 (vitest)
- [ ] `node frontend/tests/funnel.cjs` PASS (mock 기준)
- [ ] `NEXT_PUBLIC_API_BASE=http://localhost:8300`로 전환 후 백엔드 실데이터 스모크: `/map`에서 대구 폴리곤·지표 렌더, `/simulate` 실계산 응답 `[백엔드 Task 4·6 완료 이후]`
- [ ] 기획서 §4 ⓪~④ 각 단계가 화면으로 존재; ⑤ 루프백은 URL 재진입으로 성립함을 확인
