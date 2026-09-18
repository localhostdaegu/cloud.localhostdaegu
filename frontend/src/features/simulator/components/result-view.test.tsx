import { render, screen } from "@testing-library/react";
import { ResultView } from "./result-view";
import type { ConsultationFinanceOutput, FinanceInput } from "@/shared/api/types";

/** 전환계획 §7-2 — 희망대출 2,500만 때문에 부족액이 0원이 되는 필수 회귀 사례. */
const INPUT: FinanceInput = {
  deposit: 20_000_000, key_money: 0, interior_cost: 20_000_000, equipment_cost: 10_000_000,
  monthly_rent: 1_000_000, monthly_payroll: 900_000, monthly_insurance: 100_000,
  cost_ratio: 0.57, fee_ratio: 0.03,
  equity: 40_000_000, desired_loan: 25_000_000, loan_rate: 0.048,
  expected_monthly_revenue: 8_000_000,
};
const RESULT: ConsultationFinanceOutput = {
  capex: 50_000_000, monthly_fixed: 2_100_000, bep_revenue: 5_250_000,
  funding_gap: 0,
  reserve_months: 6, operating_reserve: 12_600_000,
  total_required_funds: 62_600_000, external_funding_need: 22_600_000,
  scenarios: [
    { name: "비관", monthly_revenue: 4_800_000, variable_cost: 2_880_000, operating_profit: -180_000, payback_months: null, runway_months: 5.8 },
    { name: "기준", monthly_revenue: 8_000_000, variable_cost: 4_800_000, operating_profit: 1_100_000, payback_months: 21.2, runway_months: null },
    { name: "낙관", monthly_revenue: 12_800_000, variable_cost: 7_680_000, operating_profit: 3_020_000, payback_months: 6.2, runway_months: null },
  ],
  stress: [{ rate_delta: 0.01, monthly_fixed: 2_120_833, base_operating_profit: 1_079_167 }],
};

test("세 시나리오와 회수·런웨이를 보여준다", () => {
  render(<ResultView result={RESULT} input={INPUT} />);
  expect(screen.getByText("비관")).toBeInTheDocument();
  expect(screen.getByText("낙관")).toBeInTheDocument();
  expect(screen.getByText(/5.8개월/)).toBeInTheDocument();
  expect(screen.getByText(/21.2개월/)).toBeInTheDocument();
});

test("주 지표는 손익분기 매출·총 준비자금·자기자본 외 조달 필요다", () => {
  render(<ResultView result={RESULT} input={INPUT} />);

  expect(screen.getByText("손익분기 매출")).toBeInTheDocument();
  expect(screen.getByText("총 준비자금")).toBeInTheDocument();
  expect(screen.getByText("자기자본 외 조달 필요")).toBeInTheDocument();
  expect(screen.getByText("6,260만원")).toBeInTheDocument();
  expect(screen.getByText("2,260만원")).toBeInTheDocument();
});

test("§7-2 — 부족액이 0원이어도 '자기자본으로 충분'이라고 쓰지 않는다", () => {
  render(<ResultView result={RESULT} input={INPUT} />);

  expect(screen.queryByText(/자기자본으로 충분/)).not.toBeInTheDocument();
  expect(screen.getByText(/미확보 희망대출/)).toBeInTheDocument();
  expect(screen.getByText(/2,500만원/)).toBeInTheDocument();
});

test("조달 필요가 있으면 부족액이 0원이어도 상담 후보를 계속 보여준다", () => {
  render(<ResultView result={RESULT} input={INPUT} />);

  expect(screen.getByText(/상품을 찾는 중|상담에서 확인할 후보/)).toBeInTheDocument();
});

test("운영준비금은 몇 개월치인지 함께 밝힌다", () => {
  render(<ResultView result={RESULT} input={INPUT} />);
  expect(screen.getByText(/6개월/)).toBeInTheDocument();
});

test("조달 필요도 희망대출도 0이면 후보를 강제하지 않는다", () => {
  const funded: ConsultationFinanceOutput = { ...RESULT, external_funding_need: 0 };
  render(<ResultView result={funded} input={{ ...INPUT, desired_loan: 0, equity: 70_000_000 }} />);

  expect(screen.queryByText(/상품을 찾는 중|상담에서 확인할 후보/)).not.toBeInTheDocument();
  expect(screen.getByText(/추가 조달 필요 없음/)).toBeInTheDocument();
});

test("analysisHref가 있을 때만 상담 준비 CTA 링크를 렌더한다", () => {
  const href = "/analysis?region=2711059500&industry=cafe&finance=%7B%7D";
  const { unmount } = render(<ResultView result={RESULT} input={INPUT} analysisHref={href} />);
  expect(screen.getByRole("link", { name: /이 안으로 상담 준비/ })).toHaveAttribute("href", href);
  unmount();

  render(<ResultView result={RESULT} input={INPUT} />);
  expect(screen.queryByRole("link", { name: /이 안으로 상담 준비/ })).not.toBeInTheDocument();
});
