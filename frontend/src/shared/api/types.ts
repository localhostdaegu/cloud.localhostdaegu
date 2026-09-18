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

/** POST /finance/simulate 요청 바디 — 백엔드 FinanceInput 필드명 그대로(원 단위 int). */
export interface FinanceInput {
  deposit: number;
  key_money: number;
  interior_cost: number;
  equipment_cost: number;
  monthly_rent: number;
  monthly_payroll: number;
  monthly_insurance: number;
  cost_ratio: number;
  fee_ratio: number;
  equity: number;
  desired_loan: number;
  loan_rate: number;
  expected_monthly_revenue: number;
}

export interface FinanceScenario {
  name: string;
  monthly_revenue: number;
  variable_cost: number;
  operating_profit: number;
  payback_months: number | null;
  runway_months: number | null;
}

export interface FinanceStress {
  rate_delta: number;
  monthly_fixed: number;
  base_operating_profit: number;
}

export interface FinanceOutput {
  capex: number;
  monthly_fixed: number;
  bep_revenue: number;
  funding_gap: number;
  scenarios: FinanceScenario[];
  stress: FinanceStress[];
}

/** 전환계획 §4-1 자금 구성 4수치를 더한 확장 응답.
 *  funding_gap 은 '희망대출 반영 후 남는 부족액', external_funding_need 는
 *  '자기자본 외 조달 필요액'으로 서로 다른 금액이다. */
export interface ConsultationFinanceOutput extends FinanceOutput {
  reserve_months: number;
  operating_reserve: number;
  total_required_funds: number;
  external_funding_need: number;
}

/** 전환계획 §5-1 — POST /analysis 에 실어 보내는 상담 정보 계약.
 *  화면 상태(consultation-draft)와 달리 '모름'은 null 로 보내고 확인 목록에 남긴다. */
export type PreparationStatus = "not_started" | "in_progress" | "issued" | "unknown";

export interface ConsultationProfileWire {
  business_registered: boolean | null;
  business_age_months: number | null;
  planned_opening_date: string | null;
  funds_needed_by: string | null;
  owner_age: number | null;
  guarantee_status: PreparationStatus;
  policy_confirmation_status: PreparationStatus;
}

export interface ConsultationContext {
  profile: ConsultationProfileWire;
  baseline_finance: FinanceInput | null;
  change_reason: string;
  assumptions: string[];
  open_questions: string[];
}

export type ProviderType = "guarantee" | "bank" | "policy";

/** GET /matching 응답 각 항목 — 백엔드 필드명 그대로. */
export interface MatchingProduct {
  product_id: string;
  provider: string;
  provider_type: ProviderType;
  product_name: string;
  target: string;
  region: string;
  business_age_min: number;
  business_age_max: number | null;
  category: string[] | null;
  owner_age_max: number | null;
  loan_limit: number | null;
  interest_rate: number | null;
  guarantee_fee: number | null;
  url: string;
  source_url: string;
}

/** GET /shocks/rates/latest 응답 — ECOS 월별 금리의 최신 1점. */
export interface LatestRate {
  rate_type: string;
  period: string; // YYYYMM
  value_percent: number; // 연%
  value_ratio: number; // 비율 — FinanceInput.loan_rate 단위
}
