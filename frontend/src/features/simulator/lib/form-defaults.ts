import type { FinanceInput } from "@/shared/api/types";

/** 업종별 원가율 벤치마크 — 소상공인 실태조사 근사값. 사용자가 폼에서 수정 가능. */
const COST_RATIO_BY_INDUSTRY: Record<string, number> = {
  restaurant: 0.4,
  cafe: 0.35,
  hair_salon: 0.25,
  gym: 0.15,
  billiard: 0.2,
  karaoke: 0.2,
  pc_bang: 0.2,
};
const DEFAULT_COST_RATIO = 0.4;
const FEE_RATIO = 0.03;
const LOAN_RATE = 0.045;

export interface BuildDefaultsParams {
  budget?: string | null;
  industry?: string | null;
}

/** URL 파라미터(budget·industry) → FinanceInput 초기값. 자기자본=budget, 원가율은 업종 벤치마크, 나머지 0. */
export function buildDefaults(params: BuildDefaultsParams): FinanceInput {
  const budget = params.budget ? Number(params.budget) : NaN;
  const equity = Number.isFinite(budget) ? budget : 0;
  const cost_ratio = params.industry
    ? (COST_RATIO_BY_INDUSTRY[params.industry] ?? DEFAULT_COST_RATIO)
    : DEFAULT_COST_RATIO;

  return {
    deposit: 0,
    key_money: 0,
    interior_cost: 0,
    equipment_cost: 0,
    monthly_rent: 0,
    monthly_payroll: 0,
    monthly_insurance: 0,
    cost_ratio,
    fee_ratio: FEE_RATIO,
    equity,
    desired_loan: 0,
    loan_rate: LOAN_RATE,
    expected_monthly_revenue: 0,
  };
}
