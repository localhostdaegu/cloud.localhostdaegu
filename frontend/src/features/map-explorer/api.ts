import type { FeatureCollection, MultiPolygon, Polygon } from "geojson";
import { apiGet } from "@/shared/api/client";
import type {
  IndustryRiskScore,
  MetricKey,
  MetricRow,
  PopulationSummary,
  RegionalIndicator,
  RegionSummary,
  RiskScore,
  ShockEvent,
  Store,
} from "@/shared/api/types";

export type RegionProperties = { region_code: string; name: string };
export type RegionGeoJSON = FeatureCollection<Polygon | MultiPolygon, RegionProperties>;

export function fetchRegionsGeoJson(): Promise<RegionGeoJSON> {
  return apiGet<RegionGeoJSON>("/regions/geojson");
}

export function fetchMetrics(industry: string, metric: MetricKey, year: number): Promise<MetricRow[]> {
  const params = new URLSearchParams({ industry, metric, year: String(year) });
  return apiGet<MetricRow[]>(`/metrics?${params.toString()}`);
}

export function fetchRegionSummary(regionCode: string, industry: string): Promise<RegionSummary> {
  const params = new URLSearchParams({ industry });
  return apiGet<RegionSummary>(`/regions/${regionCode}/summary?${params.toString()}`);
}

export function fetchStores(regionCode: string, industry: string): Promise<Store[]> {
  const params = new URLSearchParams({ region: regionCode, industry });
  return apiGet<Store[]>(`/stores?${params.toString()}`);
}

/** region×industry 단건 위험도. 데이터 없으면 ApiError(code="RISK_NOT_FOUND")로 404를 던진다 — 정상 케이스. */
export function fetchRiskScore(regionCode: string, industry: string): Promise<RiskScore> {
  const params = new URLSearchParams({ region_code: regionCode, industry });
  return apiGet<RiskScore>(`/metrics/risk?${params.toString()}`);
}

/** region 고정 업종별 위험도 랭킹(B유형) — industry 미지정 시 side-panel이 1회 호출로 받는다. */
export function fetchIndustryRiskRanking(regionCode: string): Promise<IndustryRiskScore[]> {
  const params = new URLSearchParams({ region_code: regionCode });
  return apiGet<IndustryRiskScore[]>(`/metrics/risk?${params.toString()}`);
}

/** industry 고정 전 행정동 랭킹(A유형) — 점수 내림차순. 선택한 동이 몇 번째인지 셀 때 쓴다. */
export function fetchRegionRiskRanking(industry: string): Promise<RiskScore[]> {
  const params = new URLSearchParams({ industry });
  return apiGet<RiskScore[]>(`/metrics/risk?${params.toString()}`);
}

/** 업종에 영향을 준 사건 목록 — 추이 차트에서 "그해 무슨 일이 있었나"를 짚는 데 쓴다. */
export function fetchShockEvents(industry: string): Promise<ShockEvent[]> {
  const params = new URLSearchParams({ industry, limit: "100" });
  return apiGet<ShockEvent[]>(`/shocks?${params.toString()}`);
}

/** 주민등록 인구 요약. 적재되지 않은 동은 ApiError(code="POPULATION_NOT_FOUND"). */
export function fetchPopulationSummary(regionCode: string): Promise<PopulationSummary> {
  return apiGet<PopulationSummary>(`/populations/${regionCode}/summary`);
}

/** 동네 특성 지표(전통시장·백년가게·지하철 승차 등) — 없는 동은 빈 배열. */
export function fetchRegionalIndicators(regionCode: string): Promise<RegionalIndicator[]> {
  const params = new URLSearchParams({ region_code: regionCode });
  return apiGet<RegionalIndicator[]>(`/indicators?${params.toString()}`);
}
