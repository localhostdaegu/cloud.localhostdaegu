import { describe, expect, it } from "vitest";

import { POST } from "./route";

/** 전환계획 §4-1 — mock 계약이 백엔드 응답과 같은 자금 구성 4수치를 실어야 한다.
 *  값은 backend/tests/test_finance_engine.py 의 BASE 를 실제 엔진으로 검산한 결과다. */
describe("mock POST /finance/simulate", () => {
  it("자금 구성 4수치를 함께 반환한다", async () => {
    const body = await (await POST()).json();

    expect(body.reserve_months).toBe(6);
    expect(body.operating_reserve).toBe(51_450_000);
    expect(body.total_required_funds).toBe(111_450_000);
    expect(body.external_funding_need).toBe(61_450_000);
    expect(body.funding_gap).toBe(41_450_000);
  });
});
