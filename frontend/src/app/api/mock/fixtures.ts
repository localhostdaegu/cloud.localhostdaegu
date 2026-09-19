import type { Feature, FeatureCollection, MultiPolygon } from "geojson";
import type {
  AgentEvent,
  AgentName,
  IndustryRiskScore,
  MetricKey,
  MetricRow,
  RegionSummary,
  RiskComponents,
  RiskGrade,
  RiskScore,
  Store,
  SummaryCard,
} from "@/shared/api/types";
import { STORE_SAMPLES } from "./store-samples";

type RegionProperties = { region_code: string; name: string };
type RegionSeed = RegionProperties & { center: [number, number] };

/** 대구 행정동 5개 목업 시드 — 실제 위치 근방, region_code는 행안부 10자리 체계(구코드 5자리 + 동 일련번호)를 흉내낸 값.
 *  실 경계는 백엔드 GET /regions/geojson 연동 시 대체된다 — 여기서는 화면 개발용 사각 폴리곤 스텁만 제공. */
const REGION_SEEDS: RegionSeed[] = [
  { region_code: "2711051000", name: "성내1동", center: [128.593, 35.870] },
  { region_code: "2711059500", name: "대신동", center: [128.578, 35.867] },
  { region_code: "2711054000", name: "동인동", center: [128.605, 35.874] },
  { region_code: "2726052500", name: "상동", center: [128.614, 35.855] },
  { region_code: "2714052000", name: "신암동", center: [128.615, 35.885] },
];

const HALF_SIZE = 0.003;

function squareFeature({ region_code, name, center }: RegionSeed): Feature<MultiPolygon, RegionProperties> {
  const [lng, lat] = center;
  const ring = [
    [lng - HALF_SIZE, lat - HALF_SIZE],
    [lng + HALF_SIZE, lat - HALF_SIZE],
    [lng + HALF_SIZE, lat + HALF_SIZE],
    [lng - HALF_SIZE, lat + HALF_SIZE],
    [lng - HALF_SIZE, lat - HALF_SIZE],
  ];
  return {
    type: "Feature",
    properties: { region_code, name },
    geometry: { type: "MultiPolygon", coordinates: [[ring]] },
  };
}

/** 대구 행정동 5개 목업 경계 — 백엔드 GET /regions/geojson 응답 구조(FeatureCollection·properties 필드명)를 그대로 따르는
 *  사각 폴리곤 스텁. 서버 전용 모듈(mock 라우트·테스트)에서만 import — 클라이언트 번들에 실리지 않는다. */
export const SEOUL_REGIONS_GEOJSON: FeatureCollection<MultiPolygon, RegionProperties> = {
  type: "FeatureCollection",
  features: REGION_SEEDS.map(squareFeature),
};

const REGIONS: RegionProperties[] = SEOUL_REGIONS_GEOJSON.features.map((f) => f.properties!);

/** 문자열 시드 → 결정적 정수 해시 (FNV-1a). Math.random 사용 금지 — 테스트 재현성. */
function hashSeed(...parts: (string | number)[]): number {
  const str = parts.join("|");
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return Math.abs(h);
}

function unitFrom(seed: number): number {
  return (seed % 10000) / 10000; // [0, 1)
}

const METRIC_RANGES: Record<MetricKey, [number, number]> = {
  closure_rate: [0.02, 0.18],
  growth_rate: [-0.08, 0.12],
  store_count: [15, 320],
};

export function metricRows(metric: MetricKey, year: number, industry: string): MetricRow[] {
  const [min, max] = METRIC_RANGES[metric];
  return REGIONS.map(({ region_code }) => {
    const u = unitFrom(hashSeed(metric, year, industry, region_code));
    const raw = min + u * (max - min);
    const value = metric === "store_count" ? Math.round(raw) : Math.round(raw * 1000) / 1000;
    return { region_code, value };
  });
}

export function summaryOf(code: string, industry: string): RegionSummary {
  const name = REGIONS.find((r) => r.region_code === code)?.name ?? "알 수 없음";
  const storeCount = metricRows("store_count", 2026, industry).find((r) => r.region_code === code)?.value ?? 0;
  const closureRate = metricRows("closure_rate", 2026, industry).find((r) => r.region_code === code)?.value ?? 0;
  const growthRate = metricRows("growth_rate", 2026, industry).find((r) => r.region_code === code)?.value ?? 0;
  const newsSeed = unitFrom(hashSeed("news", code, industry));

  const cards: SummaryCard[] = [
    { label: "점포수", value: `${storeCount}개`, grade: "fact" },
    { label: "폐업률", value: `${(closureRate * 100).toFixed(1)}%`, grade: "fact" },
    { label: "점포 증감률", value: `${growthRate >= 0 ? "+" : ""}${(growthRate * 100).toFixed(1)}%`, grade: "fact" },
    {
      label: "뉴스 신호",
      value: newsSeed > 0.5 ? "최근 30일 신규 카페 오픈 소식 증가" : "임대료 상승 관련 언급 감지",
      grade: "signal",
    },
    {
      label: "상권 활력",
      value: newsSeed > 0.3 ? "유동인구 증가 추세 (SNS 언급 기반)" : "경쟁 점포 증가 신호",
      grade: "signal",
    },
  ];

  return { region_code: code, name, industry_id: industry, cards };
}

/** region_code·industry_id로 STORE_SAMPLES를 필터링해 마커용 점포 목록을 반환한다.
 *  실적재 데이터가 없는 업종/동 조합은 빈 배열 — 이는 오류가 아니라 실데이터 부재를 그대로 반영한 것. */
export function storesOf(regionCode: string, industryId: string): Store[] {
  const samples = STORE_SAMPLES[regionCode] ?? [];
  return samples
    .filter((s) => s.industry_id === industryId)
    .map(({ store_id, name, lat, lng, status_name, open_date }) => ({
      store_id,
      name,
      lat,
      lng,
      status_name,
      open_date,
    }));
}

/** risk API가 실제로 점수를 산출하는 업종 — shared/industries.ts INDUSTRIES(11종)의 부분집합.
 *  백엔드 Task 7 위험도 모델이 지원하는 7종 계약(cafe/restaurant/hair_salon/gym/billiard/karaoke/pc_bang)만 미러링한다. */
export const RISK_INDUSTRIES = [
  "cafe",
  "restaurant",
  "hair_salon",
  "gym",
  "billiard",
  "karaoke",
  "pc_bang",
] as const;

const RISK_W_CLOSURE = 0.4;
const RISK_W_DENSITY = 0.4;
const RISK_W_GROWTH = 0.2;

function riskGradeOf(score: number): RiskGrade {
  return score >= 70 ? "red" : score >= 40 ? "yellow" : "green";
}

function riskComponentsOf(regionCode: string, industry: string): RiskComponents {
  const closure = Math.round(unitFrom(hashSeed("risk-closure", regionCode, industry)) * RISK_W_CLOSURE * 1000) / 10;
  const density = Math.round(unitFrom(hashSeed("risk-density", regionCode, industry)) * RISK_W_DENSITY * 1000) / 10;
  const growth = Math.round(unitFrom(hashSeed("risk-growth", regionCode, industry)) * RISK_W_GROWTH * 1000) / 10;
  return { closure, density, growth };
}

/** region×industry 단건 위험도. REGIONS·RISK_INDUSTRIES 조합 밖은 데이터 없음(null) — 라우트가 404로 매핑한다
 *  (백엔드 실계약: 배열 폼은 데이터 없음=200 빈배열, 단건은 404 RISK_NOT_FOUND). */
export function riskScoreOf(regionCode: string, industry: string): RiskScore | null {
  if (!REGIONS.some((r) => r.region_code === regionCode)) return null;
  if (!(RISK_INDUSTRIES as readonly string[]).includes(industry)) return null;
  const components = riskComponentsOf(regionCode, industry);
  const score = Math.round((components.closure + components.density + components.growth) * 10) / 10;
  return { region_code: regionCode, score, grade: riskGradeOf(score), components };
}

/** industry 고정 — 전 region 위험도 랭킹(score 내림차순, A유형). 지원하지 않는 industry는 빈 배열
 *  (백엔드는 industry 카탈로그를 검증하지 않고 자연히 빈 결과를 낸다 — 500/404 아님). */
export function riskRankingByIndustry(industry: string): RiskScore[] {
  return REGIONS.map((r) => riskScoreOf(r.region_code, industry))
    .filter((r): r is RiskScore => r !== null)
    .sort((a, b) => b.score - a.score);
}

/** region 고정 — 업종별 위험도 랭킹(score 내림차순, B유형). 미등록 region은 빈 배열. */
export function riskRankingByRegion(regionCode: string): IndustryRiskScore[] {
  return RISK_INDUSTRIES.map((industry): IndustryRiskScore | null => {
    const s = riskScoreOf(regionCode, industry);
    return s ? { industry_id: industry, score: s.score, grade: s.grade, components: s.components } : null;
  })
    .filter((r): r is IndustryRiskScore => r !== null)
    .sort((a, b) => b.score - a.score);
}

const AGENT_TOOLS: Record<Exclude<AgentName, "orchestrator">, { tool: string; summary: string }[]> = {
  market: [
    { tool: "region_metrics", summary: "대신동 카페 지역 지표 조회" },
    { tool: "risk_score", summary: "업종 위험도 조회 — 83.1점" },
  ],
  shock: [{ tool: "news_search", summary: "관련 뉴스 검색 — 3건" }],
  funding: [
    { tool: "finance_simulate", summary: "재무 시뮬레이션 — 조달 필요 22,600,000원" },
    { tool: "product_matching", summary: "상담 후보 정리 — 3건" },
    { tool: "funding_search", summary: "정책자금 공고 검색 — 4건" },
  ],
};

const CALCULATOR_MARKDOWN = [
  "### 재무 시뮬레이션",
  "",
  "초기 투자 50,000,000원 · 운영준비금 6개월치 12,600,000원 · 총 준비자금 62,600,000원",
  "",
  "월 고정비 2,100,000원 · 손익분기 월매출 5,250,000원 · 자기자본 외 조달 필요 22,600,000원 · 희망대출 반영 후 남는 부족액 0원",
  "",
  "| 시나리오 | 월매출 | 영업이익 | 투자 회수 |",
  "|---|---|---|---|",
  "| 비관 | 4,800,000원 | -180,000원 | 회수 불가 |",
  "| 기준 | 8,000,000원 | 1,100,000원 | 45.5개월 |",
  "| 낙관 | 12,800,000원 | 3,020,000원 | 16.6개월 |",
].join("\n");

/** 상담자료(handoff) 시연용 — 대구 대신동 카페, 월세 250만 → 100만.
 *  수치는 backend/apps/finance/domain/engine.py 로 검산했다(2026-09-18).
 *  최초안 고정비 360만 · 조달 필요 3,160만 / 현재안 고정비 210만 · 조달 필요 2,260만. */
const HANDOFF_SECTIONS: { section: string; markdown: string }[] = [
  {
    section: "plan",
    markdown: [
      "### 상담할 계획",
      "",
      "총 준비자금 62,600,000원 (초기 투자 50,000,000원 + 운영준비금 6개월치 12,600,000원)",
      "",
      "자기자본 외 조달 필요 22,600,000원 · 희망대출 반영 후 남는 부족액 0원 · 손익분기 월매출 5,250,000원",
      "",
      "변경 이유: 월세가 낮은 자리로 바꿨습니다",
      "",
      "희망대출 25,000,000원은 아직 확보하지 않은 금액입니다. 부족액이 0원이라는 것은 이 대출을 받는다는 가정 위에서만 성립합니다.",
    ].join("\n"),
  },
  {
    section: "comparison",
    markdown: [
      "### 최초안과 현재안",
      "",
      "| 항목 | 최초안 | 현재안 |",
      "|---|---|---|",
      "| 손익분기 월매출 | 9,000,000원 | 5,250,000원 |",
      "| 총 준비자금 | 71,600,000원 | 62,600,000원 |",
      "| 자기자본 외 조달 필요 | 31,600,000원 | 22,600,000원 |",
      "| 희망대출 반영 후 부족액 | 6,600,000원 | 0원 |",
      "",
      "바뀐 조건: 월세 250만원 → 100만원",
    ].join("\n"),
  },
  {
    section: "calculator",
    markdown: [
      "### 재무 시뮬레이션",
      "",
      "초기 투자 50,000,000원 · 운영준비금 6개월치 12,600,000원 · 총 준비자금 62,600,000원",
      "",
      "월 고정비 2,100,000원 · 손익분기 월매출 5,250,000원 · 자기자본 외 조달 필요 22,600,000원 · 희망대출 반영 후 남는 부족액 0원",
      "",
      "| 시나리오 | 월매출 | 영업이익 | 투자 회수 |",
      "|---|---|---|---|",
      "| 비관 | 4,800,000원 | -180,000원 | 회수 불가 |",
      "| 기준 | 8,000,000원 | 1,100,000원 | 45.5개월 |",
      "| 낙관 | 12,800,000원 | 3,020,000원 | 16.6개월 |",
    ].join("\n"),
  },
  {
    section: "funding",
    markdown: [
      "### 자금 후보",
      "",
      "공개 자료에서 iM뱅크 취급·연계 근거를 확인한 상품만 후보로 둡니다.",
      "",
      "- **소상공인시장진흥공단 정책자금 (운전자금)** — iM뱅크 직접 취급으로 확인됨 (2026-09-18 확인)",
      "  - 먼저 밟을 절차: 소진공 지역센터 신청 후 '정책자금 지원대상 확인서' 발급 → 신용보증기관 연계 시 보증서 발급",
      "  - 신청 경로: 은행 영업점에 확인서 제출",
      "  - 상담에서 확인할 것: 사업자등록 필요 여부·준비서류·적용 금리 (공식 안내에 없음)",
      "",
      "운영 상품 12건 중 근거를 확인한 것은 3건이고 9건은 미확인입니다. 확인하지 못한 상품은 후보에 넣지 않았습니다.",
    ].join("\n"),
  },
  {
    section: "questions",
    markdown: [
      "### 상담에서 확인할 것",
      "",
      "**아직 확인하지 못한 것**",
      "",
      "- 설비 견적 미확정",
      "- 사업자등록 여부 미확인",
      "- 보증기관 보증서 진행 상태 미확인",
      "",
      "**계산에 사용한 가정**",
      "",
      "- 원가율 57% · 수수료율 3% 가정",
      "- 대출금리 연 4.8% 가정",
      "- 예상 월매출 8,000,000원 가정",
      "",
      "보증기관 보증서: 미확인 · 소진공 정책자금 확인서: 진행 중",
      "",
      "상담 질문 — ① 예비창업자도 정책자금 확인서를 먼저 받을 수 있나요? ② 확인서 발급부터 실행까지 얼마나 걸리나요? ③ 2,260만원 규모에 어떤 상품 조합이 가능한가요? ④ 보증서가 필요한 경우 절차가 어떻게 되나요?",
    ].join("\n"),
  },
  {
    section: "market",
    markdown: [
      "### 지역 근거",
      "",
      "대구 중구 대신동 카페 — 개폐업 이력 기준(2025년 집계). 이 수치는 개별 점포의 매출 예측이 아니라 지역 추세입니다.",
    ].join("\n"),
  },
];

/** 상담자료 경로의 도구 이름 — 진행 패널이 한국어 라벨로 바꾼다(progress-panel TOOL_LABEL). */
const HANDOFF_AGENT_TOOLS: Record<Exclude<AgentName, "orchestrator">, { tool: string; summary: string }[]> = {
  market: [
    { tool: "region_metrics", summary: "대신동 카페 지역 지표 조회" },
    { tool: "risk_score", summary: "업종 위험도 조회" },
  ],
  shock: [{ tool: "news_search", summary: "관련 뉴스 검색 — 3건" }],
  funding: [
    { tool: "finance_simulate", summary: "재무 시뮬레이션 — 조달 필요 22,600,000원" },
    { tool: "product_matching", summary: "상담 후보 정리 — 1건" },
    { tool: "funding_search", summary: "정책자금 공고 검색 — 4건" },
  ],
};

/** 발표 시연용 에이전트 이벤트 스크립트 — orchestrator → market/shock/funding → 리포트 → 완료. */
export function agentEventScript(purpose: "review" | "handoff" = "review"): AgentEvent[] {
  const handoff = purpose === "handoff";
  const tools = handoff ? HANDOFF_AGENT_TOOLS : AGENT_TOOLS;
  const events: AgentEvent[] = [{ type: "agent_status", agent: "orchestrator", status: "running" }];

  (Object.keys(tools) as Exclude<AgentName, "orchestrator">[]).forEach((agent) => {
    events.push({ type: "agent_status", agent, status: "running" });
    for (const { tool, summary } of tools[agent]) {
      events.push({ type: "tool_call", agent, tool, summary });
    }
    events.push({ type: "agent_status", agent, status: "done" });
  });

  if (handoff) {
    // 목적마다 섹션 구성이 다르다 — 백엔드 report_sections._SECTION_PLANS 와 같은 순서다.
    for (const { section, markdown } of HANDOFF_SECTIONS) {
      events.push({ type: "report_delta", section, markdown });
    }
  } else {
  events.push(
    {
      type: "report_delta",
      section: "verdict",
      markdown: "### 종합 진단\n\n대구 중구 대신동 카페 상권은 폐업률이 높아 **진입 시 준비자금 여유가 중요**합니다. 아래 수치는 시연용 고정 데이터입니다.",
    },
    {
      type: "report_delta",
      section: "market",
      markdown: "### 상권 진단\n\n대신동 카페 점포수 66개 · 폐업률 57.4% · 점포 증감률 +8.2% (2025년 집계). 개별 점포의 매출 예측이 아니라 지역 추세입니다.",
    },
    {
      type: "report_delta",
      section: "shock",
      markdown: "### 관련 뉴스\n\n지역 상권 관련 보도를 참고 자료로 붙입니다. 계산한 금리 민감도와는 별개입니다.",
    },
    {
      type: "report_delta",
      section: "funding",
      markdown: "### 자금 후보\n\n공개 자료에서 iM뱅크 취급·연계 근거를 확인한 상품만 후보로 둡니다. 확인하지 못한 상품은 차선 후보로 따로 표시합니다.",
    },
    { type: "report_delta", section: "calculator", markdown: CALCULATOR_MARKDOWN },
  );
  }

  events.push(
    { type: "agent_status", agent: "orchestrator", status: "done" },
    {
      type: "report_done",
      report_id: "mock-report-001",
      citations: [
        { title: "행정안전부 지방행정 인허가 데이터 — 대구 개폐업 이력", url: "https://www.localdata.go.kr", grade: "fact" },
        { title: "iM뱅크 소상공인시장진흥공단 정책자금 안내", url: "https://www.imbank.co.kr", grade: "fact" },
        { title: "대구신용보증재단 보증상품 소개", url: "https://www.dgsinbo.or.kr", grade: "fact" },
      ],
    },
  );

  return events;
}
