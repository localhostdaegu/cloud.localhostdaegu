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
