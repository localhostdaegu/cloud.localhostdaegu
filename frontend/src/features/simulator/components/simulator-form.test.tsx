import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { SimulatorForm } from "./simulator-form";
import type { FinanceInput } from "@/shared/api/types";

const DEFAULTS: FinanceInput = {
  deposit: 0, key_money: 0, interior_cost: 0, equipment_cost: 0,
  monthly_rent: 0, monthly_payroll: 0, monthly_insurance: 0,
  cost_ratio: 0.35, fee_ratio: 0.03,
  equity: 50_000_000, desired_loan: 0, loan_rate: 0.045,
  expected_monthly_revenue: 0,
};

const submit = () => fireEvent.click(screen.getByRole("button", { name: "시뮬레이션 실행" }));

test("손대지 않은 0원 금액을 미입력으로 알린다", () => {
  const onSubmit = vi.fn();
  render(<SimulatorForm defaults={DEFAULTS} onSubmit={onSubmit} />);

  submit();

  const [, unconfirmed] = onSubmit.mock.calls[0];
  expect(unconfirmed).toContain("deposit");
  expect(unconfirmed).toContain("monthly_rent");
  expect(unconfirmed).not.toContain("equity"); // 프리필로 값이 있다
});

test("사용자가 직접 0을 넣은 항목은 미입력이 아니다 — 유효한 0원", () => {
  const onSubmit = vi.fn();
  render(<SimulatorForm defaults={DEFAULTS} onSubmit={onSubmit} />);

  fireEvent.change(screen.getByLabelText(/권리금/), { target: { value: "0" } });
  submit();

  const [, unconfirmed] = onSubmit.mock.calls[0];
  expect(unconfirmed).not.toContain("key_money");
  expect(unconfirmed).toContain("deposit"); // 손대지 않은 것은 그대로
});

test("값을 넣은 항목은 미입력이 아니다", () => {
  const onSubmit = vi.fn();
  render(<SimulatorForm defaults={DEFAULTS} onSubmit={onSubmit} />);

  fireEvent.change(screen.getByLabelText(/월세/), { target: { value: "100" } });
  submit();

  const [values, unconfirmed] = onSubmit.mock.calls[0];
  expect(values.monthly_rent).toBe(1_000_000);
  expect(unconfirmed).not.toContain("monthly_rent");
});

test("비율 필드는 미입력 판정 대상이 아니다 — 기본값에 출처가 있다", () => {
  const onSubmit = vi.fn();
  render(<SimulatorForm defaults={DEFAULTS} onSubmit={onSubmit} />);

  submit();

  const [, unconfirmed] = onSubmit.mock.calls[0];
  expect(unconfirmed).not.toContain("cost_ratio");
  expect(unconfirmed).not.toContain("loan_rate");
});
