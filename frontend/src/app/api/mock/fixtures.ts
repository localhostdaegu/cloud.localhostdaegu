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
  { region_code: "2711053500", name: "대신동", center: [128.578, 35.867] },
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
    { label: "성장률", value: `${growthRate >= 0 ? "+" : ""}${(growthRate * 100).toFixed(1)}%`, grade: "fact" },
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
    { tool: "closure_rate_lookup", summary: "강남구 카페 폐업률 조회" },
    { tool: "sales_trend_lookup", summary: "인근 상권 매출 데이터 조회" },
  ],
  shock: [
    { tool: "interest_rate_history", summary: "금리 변동 이력 조회" },
    { tool: "commodity_index_lookup", summary: "원두 가격 지수 조회" },
    { tool: "supply_chain_news", summary: "원두 공급망 뉴스 스캔" },
  ],
  funding: [
    { tool: "policy_fund_catalog", summary: "소상공인 정책자금 목록 조회" },
    { tool: "rent_market_lookup", summary: "임대료 시세 데이터 조회" },
  ],
};

const CALCULATOR_MARKDOWN = [
  "### 월세 vs 매입 비교",
  "",
  "| 구분 | 월세 (보증금 5,000만원 + 월 300만원) | 매입 (10억원, 대출 70%) |",
  "|---|---|---|",
  "| 초기 투자금 | 5,000만원 | 3억원 |",
  "| 월 고정비 | 300만원 | 대출이자 약 175만원 (연 3.5%) |",
  "| 5년 누적 비용 | 1억 8,500만원 | 1억 500만원 + 대출 원금 상환 |",
  "| 자산 형성 | 없음 | 부동산 자산 10억원 (시세 변동 별도) |",
].join("\n");

/** 발표 시연용 에이전트 이벤트 스크립트 — orchestrator → market/shock/funding → 리포트 → 완료. */
export function agentEventScript(): AgentEvent[] {
  const events: AgentEvent[] = [{ type: "agent_status", agent: "orchestrator", status: "running" }];

  (Object.keys(AGENT_TOOLS) as Exclude<AgentName, "orchestrator">[]).forEach((agent) => {
    events.push({ type: "agent_status", agent, status: "running" });
    for (const { tool, summary } of AGENT_TOOLS[agent]) {
      events.push({ type: "tool_call", agent, tool, summary });
    }
    events.push({ type: "agent_status", agent, status: "done" });
  });

  events.push(
    {
      type: "report_delta",
      section: "verdict",
      markdown: "### 종합 진단\n\n강남구 카페 상권은 **안정적 성장세**이나 원두 가격 상승발 원가 압박이 존재합니다.",
    },
    {
      type: "report_delta",
      section: "market",
      markdown: "### 상권 진단\n\n최근 1년 신규 카페 개업이 12% 증가했고, 폐업률은 6.4%로 서울 평균 대비 낮습니다.",
    },
    {
      type: "report_delta",
      section: "shock",
      markdown: "### 충격 분석\n\n기준금리는 동결 기조지만 원두 원가는 전년 대비 8% 상승 — 마진 압박 요인입니다.",
    },
    {
      type: "report_delta",
      section: "funding",
      markdown: "### 정책자금\n\n소상공인 정책자금(최대 7,000만원, 금리 2.5%) 신청 조건을 충족합니다.",
    },
    { type: "report_delta", section: "calculator", markdown: CALCULATOR_MARKDOWN },
  );

  events.push(
    { type: "agent_status", agent: "orchestrator", status: "done" },
    {
      type: "report_done",
      report_id: "mock-report-001",
      citations: [
        { title: "서울시 상권분석 서비스 — 강남구 폐업률 통계", url: "https://data.seoul.go.kr", grade: "fact" },
        { title: "소상공인시장진흥공단 정책자금 공고", url: "https://semas.or.kr", grade: "fact" },
        { title: "국제 원두 선물 가격 동향 리포트", url: "https://example-news.com/coffee-price", grade: "fact" },
        { title: "강남 카페 상권 SNS 언급량 분석", url: "https://example-news.com/sns-trend", grade: "signal" },
      ],
    },
  );

  return events;
}
