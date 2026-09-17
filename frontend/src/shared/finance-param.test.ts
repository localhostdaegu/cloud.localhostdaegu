import { describe, expect, it } from "vitest";
import type { FinanceInput } from "@/shared/api/types";
import { encodeFinanceParam, parseFinanceParam } from "./finance-param";

const INPUT: FinanceInput = {
  deposit: 20_000_000,
  key_money: 0,
  interior_cost: 30_000_000,
  equipment_cost: 10_000_000,
  monthly_rent: 1_500_000,
  monthly_payroll: 3_000_000,
  monthly_insurance: 300_000,
  cost_ratio: 0.35,
  fee_ratio: 0.03,
  equity: 40_000_000,
  desired_loan: 20_000_000,
  loan_rate: 0.05,
  expected_monthly_revenue: 20_000_000,
};

describe("finance URL 파라미터", () => {
  it("URLSearchParams 왕복 후에도 13필드를 그대로 복원한다", () => {
    const qs = new URLSearchParams({ finance: encodeFinanceParam(INPUT) }).toString();
    expect(parseFinanceParam(new URLSearchParams(qs).get("finance"))).toEqual(INPUT);
  });

  it("13필드 밖의 키는 인코딩하지 않는다", () => {
    const withExtra = { ...INPUT, extra: 1 } as FinanceInput;
    expect(Object.keys(JSON.parse(encodeFinanceParam(withExtra)))).toHaveLength(13);
  });

  it("없거나·JSON이 깨졌거나·필드가 빠졌거나·숫자가 아니면 undefined", () => {
    const partial: Partial<FinanceInput> = { ...INPUT };
    delete partial.loan_rate;
    expect(parseFinanceParam(null)).toBeUndefined();
    expect(parseFinanceParam("{not json")).toBeUndefined();
    expect(parseFinanceParam("[]")).toBeUndefined();
    expect(parseFinanceParam(JSON.stringify(partial))).toBeUndefined();
    expect(parseFinanceParam(JSON.stringify({ ...INPUT, deposit: "20000000" }))).toBeUndefined();
  });
});
