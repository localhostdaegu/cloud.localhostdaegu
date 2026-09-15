import type { MetricKey } from "@/shared/api/types";
import { INDUSTRIES } from "@/shared/industries";

export const METRICS = ["closure_rate", "growth_rate", "store_count"] as const;

export const YEARS = Array.from({ length: 8 }, (_, i) => 2019 + i);

/** 화면 표기용 한국어 라벨. URL 파라미터·API 값은 영문 id를 그대로 쓴다. */
export const METRIC_LABELS: Record<(typeof METRICS)[number], string> = {
  closure_rate: "폐업률",
  growth_rate: "성장률",
  store_count: "점포수",
};

export interface MapState {
  /** null = URL에 industry가 없어 미지정 상태(B유형 랭킹 진입 조건). 소비처(MapView·ControlBar 등)가
   *  표시·조회용 기본값을 직접 적용한다 — 여기서 기본값으로 채우면 미지정을 표현할 수 없다. */
  industry: string | null;
  metric: MetricKey;
  year: number;
  region: string | null;
  /** 채팅 랜딩(intent-gate)에서 넘어온 구·군 코드 — region 미선택 시 초기 flyTo에 쓰인다. */
  district: string | null;
  /** 채팅 랜딩에서 넘어온 예산(원) — Task 5 소비. */
  budget: number | null;
}

/** industry 미지정 시 화면 조회·표시에 쓰는 기본 업종. */
export const DEFAULT_INDUSTRY = "cafe";

export const DEFAULT_STATE: MapState = {
  industry: null,
  metric: "closure_rate",
  year: 2026,
  region: null,
  district: null,
  budget: null,
};

export function serializeMapState(state: MapState): string {
  const params = new URLSearchParams();
  if (state.industry) {
    params.set("industry", state.industry);
  }
  params.set("metric", state.metric);
  params.set("year", String(state.year));
  if (state.region) {
    params.set("region", state.region);
  }
  if (state.district) {
    params.set("district", state.district);
  }
  if (state.budget) {
    params.set("budget", String(state.budget));
  }
  return params.toString();
}

export function parseMapState(sp: URLSearchParams): MapState {
  const industry = sp.get("industry");
  const metric = sp.get("metric");
  const year = sp.get("year");
  const region = sp.get("region");
  const district = sp.get("district");
  const budget = sp.get("budget");

  return {
    industry: industry && INDUSTRIES.includes(industry as any) ? industry : DEFAULT_STATE.industry,
    metric: METRICS.includes(metric as any) ? (metric as MetricKey) : DEFAULT_STATE.metric,
    year: YEARS.includes(Number(year)) ? Number(year) : DEFAULT_STATE.year,
    region: region || null,
    district: district || null,
    budget: budget && Number.isFinite(Number(budget)) ? Number(budget) : null,
  };
}
