export type AgentName = "orchestrator" | "market" | "shock" | "funding";

export type AgentEvent =
  | { type: "agent_status"; agent: AgentName; status: "running" | "done" | "error" }
  | { type: "tool_call"; agent: AgentName; tool: string; summary: string }
  | { type: "report_delta"; section: string; markdown: string }
  | { type: "report_done"; report_id: string; citations: unknown[] };

export type MetricKey = "closure_rate" | "growth_rate" | "store_count";

export interface MetricRow {
  region_code: string;
  value: number;
}

export interface SummaryCard {
  label: string;
  value: string;
  grade: "fact" | "signal";
}

export interface RegionSummary {
  region_code: string;
  name: string;
  industry_id: string;
  cards: SummaryCard[];
}

export interface Store {
  store_id: string;
  name: string;
  lat: number;
  lng: number;
  status_name: string;
  open_date: string;
}

export type RiskGrade = "red" | "yellow" | "green";

export interface RiskComponents {
  closure: number;
  density: number;
  growth: number;
}

/** region_code+industry 단건, 또는 industry 고정 전 region 랭킹(A유형)의 각 행 — {region_code, score, grade, components}. */
export interface RiskScore {
  region_code: string;
  score: number;
  grade: RiskGrade;
  components: RiskComponents;
}

/** region_code 고정 업종별 랭킹(B유형)의 각 행 — {industry_id, score, grade, components}. */
export interface IndustryRiskScore {
  industry_id: string;
  score: number;
  grade: RiskGrade;
  components: RiskComponents;
}
