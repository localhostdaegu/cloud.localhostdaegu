import { expect, test } from "vitest";
import { render, screen } from "@testing-library/react";
import type { FinanceInput } from "@/shared/api/types";
import { AdjustmentHints } from "./adjustment-hints";

const INPUT = {
  deposit: 20_000_000, key_money: 15_000_000, interior_cost: 25_000_000, equipment_cost: 12_000_000,
  monthly_rent: 1_300_000, monthly_payroll: 0,
} as FinanceInput;

test("영향이 큰 비용 3개를 10% 줄였을 때의 준비자금 감소로 보여준다 — 월 비용은 준비금 개월 수만큼 곱한다", () => {
  render(<AdjustmentHints input={INPUT} externalFundingNeed={60_000_000} reserveMonths={6} />);

  const items = screen.getAllByRole("listitem").map((li) => li.textContent);
  expect(items).toEqual([
    "인테리어 비용 2,500만원을 10% 줄이면 준비자금이 250만원 줄어요",
    "보증금 2,000만원을 10% 줄이면 준비자금이 200만원 줄어요",
    "권리금 1,500만원을 10% 줄이면 준비자금이 150만원 줄어요",
  ]);
  expect(screen.getByText(/계약을 미루는 것도 계획입니다/)).toBeInTheDocument();
});

test("월세는 6개월치가 준비자금에 들어가므로 10%가 6배로 반영된다", () => {
  render(<AdjustmentHints input={{ ...INPUT, interior_cost: 0, deposit: 0, key_money: 0, equipment_cost: 0 }} externalFundingNeed={1} reserveMonths={6} />);
  expect(screen.getByRole("listitem")).toHaveTextContent("월세 130만원을 10% 줄이면 준비자금이 78만원 줄어요");
});

test("추가 조달이 필요 없으면 그리지 않는다", () => {
  const { container } = render(<AdjustmentHints input={INPUT} externalFundingNeed={0} reserveMonths={6} />);
  expect(container).toBeEmptyDOMElement();
});
