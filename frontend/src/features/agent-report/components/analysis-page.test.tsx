import { beforeEach, afterEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AnalysisPage } from "./analysis-page";
import { DRAFT_KEY, emptyDraft, recordCalculation } from "@/features/simulator/lib/consultation-draft";
import type { ConsultationFinanceOutput, FinanceInput } from "@/shared/api/types";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("region=2711059500&industry=cafe"),
}));

const INPUT: FinanceInput = {
  deposit: 20_000_000, key_money: 0, interior_cost: 20_000_000, equipment_cost: 10_000_000,
  monthly_rent: 1_000_000, monthly_payroll: 900_000, monthly_insurance: 100_000,
  cost_ratio: 0.57, fee_ratio: 0.03,
  equity: 40_000_000, desired_loan: 25_000_000, loan_rate: 0.048,
  expected_monthly_revenue: 8_000_000,
};
const RESULT: ConsultationFinanceOutput = {
  capex: 50_000_000, monthly_fixed: 2_100_000, bep_revenue: 5_250_000, funding_gap: 0,
  reserve_months: 6, operating_reserve: 12_600_000,
  total_required_funds: 62_600_000, external_funding_need: 22_600_000,
  scenarios: [], stress: [],
};

let posted: Record<string, unknown> | null = null;

beforeEach(() => {
  sessionStorage.clear();
  posted = null;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (_url: string, init?: RequestInit) => {
      posted = JSON.parse(String(init?.body ?? "{}"));
      return new Response(JSON.stringify({ analysis_id: "a".repeat(32) }), { status: 200 });
    }),
  );
  vi.stubGlobal(
    "EventSource",
    class {
      addEventListener() {}
      close() {}
    },
  );
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

const submit = () => fireEvent.click(screen.getByRole("button", { name: /분석 시작/ }));

it("저장된 선택안이 있으면 상담자료(handoff)로 요청한다", async () => {
  const draft = { ...recordCalculation(emptyDraft({ region: "2711059500", industry: "cafe" }), INPUT, RESULT), change_reason: "월세가 낮은 자리" };
  sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft));

  render(<AnalysisPage />);
  submit();

  await waitFor(() => expect(posted).not.toBeNull());
  expect(posted!.purpose).toBe("handoff");
  expect((posted!.finance as FinanceInput).monthly_rent).toBe(1_000_000);
  expect((posted!.consultation as { change_reason: string }).change_reason).toBe("월세가 낮은 자리");
});

it("저장된 선택안이 없으면 기존 review 경로를 유지한다", async () => {
  render(<AnalysisPage />);
  submit();

  await waitFor(() => expect(posted).not.toBeNull());
  expect(posted!.purpose).toBeUndefined();
  expect(posted!.consultation).toBeUndefined();
});
