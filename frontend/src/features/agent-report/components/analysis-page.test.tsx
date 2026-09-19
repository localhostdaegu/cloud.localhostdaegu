import { beforeEach, afterEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AnalysisPage } from "./analysis-page";
import { DRAFT_KEY, emptyDraft, recordCalculation } from "@/features/simulator/lib/consultation-draft";
import type { ConsultationFinanceOutput, FinanceInput } from "@/shared/api/types";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("region=2711059500&industry=cafe&year=2025"),
}));

// 동 이름 목록은 지도 경계 캐시에서 온다 — 이 테스트의 관심사(리포트 요청·세션 기록)가 아니므로 비워 둔다.
vi.mock("@/shared/api/use-region-names", () => ({ useRegionNames: () => [] }));

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
let requests: [string, string][] = [];

beforeEach(() => {
  sessionStorage.clear();
  posted = null;
  requests = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const path = String(url);
      requests.push([init?.method ?? "GET", path]);
      if (path.includes("/consultation")) {
        return new Response(JSON.stringify({ session_id: "sess-1" }), { status: 201 });
      }
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

it("상담자료를 만들 때 세션을 서버에 기록한다 — 감사·재현용 스냅샷", async () => {
  const draft = { ...recordCalculation(emptyDraft({ region: "2711059500", industry: "cafe" }), INPUT, RESULT), change_reason: "월세가 낮은 자리" };
  sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft));

  render(<AnalysisPage />);
  submit();

  await waitFor(() => expect(requests.some(([m, p]) => m === "POST" && p.endsWith("/consultation"))).toBe(true));
  await waitFor(() =>
    expect(requests.some(([m, p]) => m === "PUT" && p.endsWith("/consultation/sess-1/plans/baseline"))).toBe(true),
  );
});

it("저장된 선택안이 없으면 세션도 기록하지 않는다", async () => {
  render(<AnalysisPage />);
  submit();

  await waitFor(() => expect(posted).not.toBeNull());
  expect(requests.some(([, p]) => p.includes("/consultation"))).toBe(false);
});

it("지도에서 고른 연도를 리포트 요청에 싣는다 — 화면과 기준연도를 맞춘다", async () => {
  render(<AnalysisPage />);
  submit();

  await waitFor(() => expect(posted).not.toBeNull());
  expect(posted!.year).toBe(2025);
});

it("기록한 세션 id를 초안에 남긴다 — 다시 만들 때 재사용한다", async () => {
  const draft = recordCalculation(emptyDraft({ region: "2711059500", industry: "cafe" }), INPUT, RESULT);
  sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft));

  render(<AnalysisPage />);
  submit();

  await waitFor(() =>
    expect(JSON.parse(sessionStorage.getItem(DRAFT_KEY)!).session_id).toBe("sess-1"),
  );
});
