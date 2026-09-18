import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { PlanComparison } from "./plan-comparison";
import type { PlanSnapshot } from "../lib/consultation-draft";
import type { ConsultationFinanceOutput, FinanceInput } from "@/shared/api/types";

/** 전환계획 §7-1 — 월세만 200만 → 100만으로 바꾼 두 안. */
const INPUT: FinanceInput = {
  deposit: 20_000_000, key_money: 0, interior_cost: 20_000_000, equipment_cost: 10_000_000,
  monthly_rent: 2_000_000, monthly_payroll: 900_000, monthly_insurance: 100_000,
  cost_ratio: 0.57, fee_ratio: 0.03,
  equity: 60_000_000, desired_loan: 0, loan_rate: 0.045,
  expected_monthly_revenue: 8_000_000,
};
const RESULT: ConsultationFinanceOutput = {
  capex: 50_000_000, monthly_fixed: 3_000_000, bep_revenue: 7_500_000, funding_gap: 8_000_000,
  reserve_months: 6, operating_reserve: 18_000_000,
  total_required_funds: 68_000_000, external_funding_need: 8_000_000,
  scenarios: [], stress: [],
};

const BASELINE: PlanSnapshot = { input: INPUT, result: RESULT };
const CURRENT: PlanSnapshot = {
  input: { ...INPUT, monthly_rent: 1_000_000 },
  result: {
    ...RESULT, monthly_fixed: 2_000_000, bep_revenue: 5_000_000, funding_gap: 2_000_000,
    operating_reserve: 12_000_000, total_required_funds: 62_000_000, external_funding_need: 2_000_000,
  },
};

test("현재안이 없으면 비교표를 그리지 않는다 — 비교할 대상이 없다", () => {
  const { container } = render(
    <PlanComparison baseline={BASELINE} current={null} selected="baseline" onSelect={vi.fn()} />,
  );
  expect(container).toBeEmptyDOMElement();
});

test("두 안의 조달 필요를 각각 보여준다", () => {
  render(<PlanComparison baseline={BASELINE} current={CURRENT} selected="current" onSelect={vi.fn()} />);

  expect(screen.getByText("800만원")).toBeInTheDocument();
  expect(screen.getByText("200만원")).toBeInTheDocument();
});

test("바뀐 조건만 보여준다 — 최초 조건을 현재 조건처럼 설명하지 않는다", () => {
  render(<PlanComparison baseline={BASELINE} current={CURRENT} selected="current" onSelect={vi.fn()} />);

  expect(screen.getByText(/월세 200만원 → 100만원/)).toBeInTheDocument();
  expect(screen.getAllByRole("listitem")).toHaveLength(1); // 바뀐 건 월세 하나뿐이다
  expect(screen.queryByText(/원가율/)).not.toBeInTheDocument();
});

test("선택안이 표시된다", () => {
  render(<PlanComparison baseline={BASELINE} current={CURRENT} selected="current" onSelect={vi.fn()} />);

  expect(screen.getByRole("radio", { name: /현재안/ })).toBeChecked();
  expect(screen.getByRole("radio", { name: /최초안/ })).not.toBeChecked();
});

test("다른 안을 고르면 그 안을 알린다", () => {
  const onSelect = vi.fn();
  render(<PlanComparison baseline={BASELINE} current={CURRENT} selected="current" onSelect={onSelect} />);

  fireEvent.click(screen.getByRole("radio", { name: /최초안/ }));

  expect(onSelect).toHaveBeenCalledWith("baseline");
});

test("바뀐 조건이 없으면 같은 조건임을 밝힌다", () => {
  render(
    <PlanComparison baseline={BASELINE} current={{ ...BASELINE }} selected="baseline" onSelect={vi.fn()} />,
  );

  expect(screen.getByText(/바뀐 조건 없음/)).toBeInTheDocument();
});
