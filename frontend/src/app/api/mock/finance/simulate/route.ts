import type { ConsultationFinanceOutput } from "@/shared/api/types";

/** 백엔드 계약(POST /finance/simulate) 형태의 고정 응답.
 *  값은 backend/tests/test_finance_engine.py의 BASE 입력을 backend/apps/finance/domain/engine.py로
 *  검산한 결과와 정확히 일치한다(화면 개발용 고정 fixture). */
const FIXED_RESPONSE: ConsultationFinanceOutput = {
  capex: 60_000_000,
  monthly_fixed: 8_575_000,
  bep_revenue: 15_043_859,
  funding_gap: 41_450_000,
  reserve_months: 6,
  operating_reserve: 51_450_000,
  total_required_funds: 111_450_000,
  external_funding_need: 61_450_000,
  scenarios: [
    {
      name: "비관",
      monthly_revenue: 12_000_000,
      variable_cost: 5_160_000,
      operating_profit: -1_735_000,
      payback_months: null,
      runway_months: 5.8,
    },
    {
      name: "기준",
      monthly_revenue: 20_000_000,
      variable_cost: 8_600_000,
      operating_profit: 2_825_000,
      payback_months: 21.2,
      runway_months: null,
    },
    {
      name: "낙관",
      monthly_revenue: 32_000_000,
      variable_cost: 13_760_000,
      operating_profit: 9_665_000,
      payback_months: 6.2,
      runway_months: null,
    },
  ],
  stress: [
    { rate_delta: 0.01, monthly_fixed: 8_591_666, base_operating_profit: 2_808_334 },
    { rate_delta: 0.02, monthly_fixed: 8_608_333, base_operating_profit: 2_791_667 },
  ],
};

export async function POST() {
  return Response.json(FIXED_RESPONSE);
}
