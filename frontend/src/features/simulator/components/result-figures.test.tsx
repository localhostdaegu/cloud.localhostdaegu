import { expect, test } from "vitest";
import { render, screen } from "@testing-library/react";
import type { ConsultationFinanceOutput, FinanceInput } from "@/shared/api/types";
import { ResultFigures } from "./result-view";

const INPUT = { equity: 40_000_000, desired_loan: 10_000_000 } as FinanceInput;
const RESULT: ConsultationFinanceOutput = {
  capex: 50_000_000, monthly_fixed: 3_000_000, bep_revenue: 7_500_000, funding_gap: 18_000_000,
  reserve_months: 6, operating_reserve: 18_000_000,
  total_required_funds: 68_000_000, external_funding_need: 28_000_000,
  scenarios: [
    { name: "기준", monthly_revenue: 9_000_000, variable_cost: 5_400_000, operating_profit: 600_000, payback_months: 83.3, runway_months: null },
  ],
  stress: [{ rate_delta: 0.01, monthly_fixed: 3_010_000, base_operating_profit: 590_000 }],
};

test("자금 구성 막대는 자기자본·미확보 희망대출·남는 부족액을 나눠 보여준다", () => {
  render(<ResultFigures result={RESULT} input={INPUT} />);

  expect(screen.getByRole("img", { name: "자기자본 4,000만원, 희망대출(미확보) 1,000만원, 남는 부족액 1,800만원" })).toBeInTheDocument();
});

test("희망대출이 있으면 금리 +1%p의 월 고정비·기준 영업이익을 표로 보여준다", () => {
  render(<ResultFigures result={RESULT} input={INPUT} />);

  expect(screen.getByRole("row", { name: "+1%p 301만원 59만원" })).toBeInTheDocument();
});

test("희망대출이 0원이면 금리 표를 그리지 않는다 — 이자가 없어 변화가 없다", () => {
  render(<ResultFigures result={RESULT} input={{ ...INPUT, desired_loan: 0 }} />);

  expect(screen.queryByText(/금리가 오르면/)).not.toBeInTheDocument();
});

test("비교 기준안이 있으면 주 지표 아래에 전후 차이를 방향과 금액으로 표시한다", () => {
  render(<ResultFigures result={RESULT} input={INPUT} compareTo={{ ...RESULT, bep_revenue: 10_000_000 }} />);

  expect(screen.getByText("최초안 대비 ▼ 250만원")).toBeInTheDocument();
  expect(screen.getAllByText("최초안과 같음")).toHaveLength(2);
});
