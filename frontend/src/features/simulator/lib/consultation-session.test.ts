import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { recordConsultationSession } from "./consultation-session";
import { emptyDraft, recordCalculation, type ConsultationDraft } from "./consultation-draft";
import type { ConsultationFinanceOutput, FinanceInput } from "@/shared/api/types";

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
const SCOPE = { region: "2711059500", industry: "cafe" };

/** 호출된 요청을 [method, path, body] 로 모은다. */
let calls: [string, string, Record<string, unknown>][] = [];

function stubApi(sessionOk = true) {
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const path = String(url);
      calls.push([init?.method ?? "GET", path, JSON.parse(String(init?.body ?? "{}"))]);
      if (!sessionOk) return new Response("{}", { status: 500 });
      if (path.endsWith("/consultation")) {
        return new Response(JSON.stringify({ session_id: "sess-1" }), { status: 201 });
      }
      // 세션 교체는 ConsultationDetailResponse 를 돌려준다 (계획안 저장과 형태가 다르다).
      if (/\/consultation\/[^/]+$/.test(path)) {
        return new Response(
          JSON.stringify({ session: { session_id: "sess-1" }, plans: [], notes: [] }),
          { status: 200 },
        );
      }
      return new Response(JSON.stringify({ plan_kind: "baseline" }), { status: 200 });
    }),
  );
}

const twoPlans = (): ConsultationDraft => {
  let draft = recordCalculation(emptyDraft(SCOPE), INPUT, RESULT);
  draft = recordCalculation(draft, { ...INPUT, monthly_rent: 1_000_000 }, RESULT);
  return { ...draft, change_reason: "월세가 낮은 자리" };
};

beforeEach(() => stubApi());
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("상담 세션 기록", () => {
  it("세션을 만들고 두 계획안을 저장한다", async () => {
    const sessionId = await recordConsultationSession(twoPlans());

    expect(sessionId).toBe("sess-1");
    expect(calls.map(([method, path]) => `${method} ${path.replace(/^.*\/api\/mock/, "")}`)).toEqual([
      "POST /consultation",
      "PUT /consultation/sess-1/plans/baseline",
      "PUT /consultation/sess-1/plans/current",
    ]);
  });

  it("선택안과 변경 이유를 세션에 싣는다", async () => {
    await recordConsultationSession(twoPlans());

    const [, , body] = calls[0];
    expect(body.selected_plan_kind).toBe("current");
    expect(body.change_reason).toBe("월세가 낮은 자리");
    expect(body.region_code).toBe("2711059500");
  });

  it("'모름'은 null 로 보낸다 — 아니오로 바꾸지 않는다", async () => {
    const draft = { ...twoPlans(), profile: { ...emptyDraft(SCOPE).profile, business_registered: "unknown" as const } };

    await recordConsultationSession(draft);

    expect(calls[0][2].business_registered).toBeNull();
  });

  it("계산 결과 8필드를 감사용 스냅샷으로 함께 보낸다", async () => {
    await recordConsultationSession(twoPlans());

    const [, , body] = calls[1];
    expect(body.monthly_rent).toBe(2_000_000); // 최초안 입력
    expect(body.external_funding_need).toBe(8_000_000); // 결과 스냅샷
    expect(body.reserve_months).toBe(6);
  });

  it("현재안이 없으면 최초안만 저장한다", async () => {
    await recordConsultationSession(recordCalculation(emptyDraft(SCOPE), INPUT, RESULT));

    expect(calls.map(([, path]) => path.split("/").pop())).toEqual(["consultation", "baseline"]);
  });

  it("계산안이 없으면 아무것도 보내지 않는다", async () => {
    expect(await recordConsultationSession(emptyDraft(SCOPE))).toBeNull();
    expect(calls).toEqual([]);
  });

  it("서버 저장이 실패해도 던지지 않는다 — 상담자료 생성을 막지 않는다", async () => {
    stubApi(false);

    await expect(recordConsultationSession(twoPlans())).resolves.toBeNull();
  });

  it("가정과 미확인 항목을 세션에 함께 남긴다 — 노트로 저장된다", async () => {
    await recordConsultationSession(twoPlans());

    const [, , body] = calls[0];
    expect(body.assumptions).toEqual(expect.arrayContaining([expect.stringMatching(/원가율/)]));
    expect(body.open_questions).toEqual(
      expect.arrayContaining([expect.stringMatching(/보증기관 보증서 진행 상태 미확인/)]),
    );
  });
});

describe("세션 재사용", () => {
  it("세션이 없으면 새로 만든다", async () => {
    await recordConsultationSession(twoPlans());

    expect(calls[0][0]).toBe("POST");
  });

  it("세션이 있으면 교체한다 — 다시 만들 때마다 쌓이지 않는다", async () => {
    await recordConsultationSession({ ...twoPlans(), session_id: "sess-1" });

    const [method, path] = calls[0];
    expect(method).toBe("PUT");
    expect(path).toContain("/consultation/sess-1");
    expect(path).not.toContain("/plans/");
  });

  it("교체 뒤에도 계획안을 다시 저장한다 — 선택안이 바뀌었을 수 있다", async () => {
    await recordConsultationSession({ ...twoPlans(), session_id: "sess-1" });

    expect(calls.map(([, p]) => p.split("/").pop())).toEqual(["sess-1", "baseline", "current"]);
  });
});
