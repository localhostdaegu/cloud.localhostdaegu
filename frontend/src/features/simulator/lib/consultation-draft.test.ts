import { beforeEach, describe, expect, it } from "vitest";

import {
  DRAFT_KEY,
  emptyDraft,
  loadDraft,
  recordCalculation,
  saveDraft,
  selectPlan,
  selectedPlan,
  toConsultationContext,
  withScope,
} from "./consultation-draft";
import type { ConsultationFinanceOutput, FinanceInput } from "@/shared/api/types";

/** 전환계획 §7-1 최초안 — 월세 200만. 숫자는 백엔드 엔진 검산값이다. */
const BASELINE_INPUT: FinanceInput = {
  deposit: 20_000_000, key_money: 0, interior_cost: 20_000_000, equipment_cost: 10_000_000,
  monthly_rent: 2_000_000, monthly_payroll: 900_000, monthly_insurance: 100_000,
  cost_ratio: 0.57, fee_ratio: 0.03,
  equity: 60_000_000, desired_loan: 0, loan_rate: 0.045,
  expected_monthly_revenue: 8_000_000,
};
const BASELINE_RESULT: ConsultationFinanceOutput = {
  capex: 50_000_000, monthly_fixed: 3_000_000, bep_revenue: 7_500_000, funding_gap: 8_000_000,
  reserve_months: 6, operating_reserve: 18_000_000,
  total_required_funds: 68_000_000, external_funding_need: 8_000_000,
  scenarios: [], stress: [],
};

/** §7-1 수정안 — 월세만 100만으로. */
const REVISED_INPUT: FinanceInput = { ...BASELINE_INPUT, monthly_rent: 1_000_000 };
const REVISED_RESULT: ConsultationFinanceOutput = {
  ...BASELINE_RESULT,
  monthly_fixed: 2_000_000, bep_revenue: 5_000_000, funding_gap: 2_000_000,
  operating_reserve: 12_000_000, total_required_funds: 62_000_000, external_funding_need: 2_000_000,
};

const SCOPE = { region: "2711059500", industry: "cafe" };

beforeEach(() => sessionStorage.clear());

describe("빈 세션", () => {
  it("저장값이 없으면 null 이다 — 다시 입력하도록 안내해야 한다", () => {
    expect(loadDraft()).toBeNull();
  });

  it("손상된 저장값도 null 이다 — 구조를 검증한다", () => {
    sessionStorage.setItem(DRAFT_KEY, "{not json");
    expect(loadDraft()).toBeNull();
  });

  it("금액·비율이 규약을 벗어나면 복원하지 않는다", () => {
    const broken = emptyDraft(SCOPE);
    broken.baseline = { input: { ...BASELINE_INPUT, cost_ratio: 1.2 }, result: BASELINE_RESULT };
    sessionStorage.setItem(DRAFT_KEY, JSON.stringify(broken));
    expect(loadDraft()).toBeNull();
  });
});

describe("계산안 기록", () => {
  it("첫 성공 계산이 최초안으로 고정되고 선택안이 된다", () => {
    const draft = recordCalculation(emptyDraft(SCOPE), BASELINE_INPUT, BASELINE_RESULT);

    expect(draft.baseline?.input.monthly_rent).toBe(2_000_000);
    expect(draft.current).toBeNull();
    expect(draft.selected).toBe("baseline");
  });

  it("두 번째 계산은 현재안을 갱신하고 최초안을 바꾸지 않는다", () => {
    let draft = recordCalculation(emptyDraft(SCOPE), BASELINE_INPUT, BASELINE_RESULT);
    draft = recordCalculation(draft, REVISED_INPUT, REVISED_RESULT);

    expect(draft.baseline?.input.monthly_rent).toBe(2_000_000);
    expect(draft.current?.input.monthly_rent).toBe(1_000_000);
    expect(draft.selected).toBe("current");
    expect(selectedPlan(draft)?.result.external_funding_need).toBe(2_000_000);
  });

  it("세 번째 계산도 현재안만 덮어쓴다", () => {
    let draft = recordCalculation(emptyDraft(SCOPE), BASELINE_INPUT, BASELINE_RESULT);
    draft = recordCalculation(draft, REVISED_INPUT, REVISED_RESULT);
    draft = recordCalculation(draft, BASELINE_INPUT, BASELINE_RESULT);

    expect(draft.baseline?.result.external_funding_need).toBe(8_000_000);
    expect(draft.current?.result.external_funding_need).toBe(8_000_000);
  });
});

describe("선택안", () => {
  it("최초안 → 현재안 → 최초안 재선택에도 각 안의 입력·결과가 유지된다", () => {
    let draft = recordCalculation(emptyDraft(SCOPE), BASELINE_INPUT, BASELINE_RESULT);
    draft = recordCalculation(draft, REVISED_INPUT, REVISED_RESULT);
    draft = selectPlan(draft, "baseline");

    const chosen = selectedPlan(draft);
    expect(draft.selected).toBe("baseline");
    expect(chosen?.input.monthly_rent).toBe(2_000_000);
    expect(chosen?.result.bep_revenue).toBe(7_500_000);
    expect(chosen?.result.external_funding_need).toBe(8_000_000);
    expect(draft.current?.input.monthly_rent).toBe(1_000_000);
  });

  it("없는 계산안은 선택되지 않는다 — 최종자료 생성을 막는 근거다", () => {
    const draft = selectPlan(recordCalculation(emptyDraft(SCOPE), BASELINE_INPUT, BASELINE_RESULT), "current");

    expect(draft.selected).toBe("baseline");
    expect(selectedPlan(draft)?.input.monthly_rent).toBe(2_000_000);
  });

  it("계산 전에는 선택안이 없다", () => {
    expect(selectedPlan(emptyDraft(SCOPE))).toBeNull();
  });
});

describe("저장·복원", () => {
  it("저장한 선택안이 그대로 돌아온다", () => {
    let draft = recordCalculation(emptyDraft(SCOPE), BASELINE_INPUT, BASELINE_RESULT);
    draft = recordCalculation(draft, REVISED_INPUT, REVISED_RESULT);
    saveDraft(draft);

    const restored = loadDraft();
    expect(restored?.selected).toBe("current");
    expect(selectedPlan(restored!)?.input.monthly_rent).toBe(1_000_000);
    expect(selectedPlan(restored!)?.result.bep_revenue).toBe(5_000_000);
  });
});

describe("지역·업종 변경", () => {
  it("비교 대상이 바뀌면 이전 결과와 선택을 무효화한다", () => {
    let draft = recordCalculation(emptyDraft(SCOPE), BASELINE_INPUT, BASELINE_RESULT);
    draft = recordCalculation(draft, REVISED_INPUT, REVISED_RESULT);

    const moved = withScope(draft, { region: "2711054000", industry: "cafe" });

    expect(moved.baseline).toBeNull();
    expect(moved.current).toBeNull();
    expect(moved.selected).toBeNull();
    expect(moved.region).toBe("2711054000");
  });

  it("같은 지역·업종이면 계산안을 유지한다", () => {
    const draft = recordCalculation(emptyDraft(SCOPE), BASELINE_INPUT, BASELINE_RESULT);

    expect(withScope(draft, SCOPE).baseline?.input.monthly_rent).toBe(2_000_000);
  });

  it("상담 정보는 지역이 바뀌어도 남는다 — 사람에 대한 정보다", () => {
    const draft = { ...emptyDraft(SCOPE), profile: { ...emptyDraft(SCOPE).profile, business_registered: false } };

    expect(withScope(draft, { region: "2711054000", industry: "cafe" }).profile.business_registered).toBe(false);
  });
});

describe("상담 정보 전송 형태", () => {
  it("'모름'은 null 로 보내되 확인 목록에 남긴다 — 숫자 가정으로 바뀌며 사라지지 않게", () => {
    const draft = recordCalculation(
      { ...emptyDraft(SCOPE), profile: { ...emptyDraft(SCOPE).profile, business_registered: "unknown" } },
      BASELINE_INPUT,
      BASELINE_RESULT,
    );

    const context = toConsultationContext(draft);

    expect(context.profile.business_registered).toBeNull();
    expect(context.open_questions).toContain("사업자등록 여부 미확인");
  });

  it("아직 묻지 않은 항목도 확인 목록에 남는다", () => {
    const context = toConsultationContext(emptyDraft(SCOPE));

    expect(context.open_questions).toContain("보증기관 보증서 진행 상태 미확인");
    expect(context.open_questions).toContain("소진공 정책자금 확인서 진행 상태 미확인");
  });

  it("비교 원본으로 최초안의 입력을 보낸다 — 계산 결과는 보내지 않는다", () => {
    let draft = recordCalculation(emptyDraft(SCOPE), BASELINE_INPUT, BASELINE_RESULT);
    draft = recordCalculation(draft, REVISED_INPUT, REVISED_RESULT);

    const context = toConsultationContext(draft);

    expect(context.baseline_finance?.monthly_rent).toBe(2_000_000);
    expect(context.baseline_finance).not.toHaveProperty("bep_revenue");
  });

  it("선택안의 가정을 사람이 읽는 문장으로 싣는다", () => {
    const draft = recordCalculation(emptyDraft(SCOPE), BASELINE_INPUT, BASELINE_RESULT);

    const context = toConsultationContext(draft);

    expect(context.assumptions.join(" ")).toMatch(/원가율 57%/);
    expect(context.assumptions.join(" ")).toMatch(/대출금리 연 4.5%/);
  });

  it("변경 이유를 그대로 전달한다", () => {
    const draft = { ...recordCalculation(emptyDraft(SCOPE), BASELINE_INPUT, BASELINE_RESULT), change_reason: "월세가 싼 자리" };

    expect(toConsultationContext(draft).change_reason).toBe("월세가 싼 자리");
  });
});

describe("미입력 금액 보존", () => {
  it("계산안에 미입력 항목을 함께 기록한다", () => {
    const draft = recordCalculation(emptyDraft(SCOPE), BASELINE_INPUT, BASELINE_RESULT, ["deposit", "key_money"]);

    expect(draft.baseline?.unconfirmed).toEqual(["deposit", "key_money"]);
  });

  it("미입력 항목이 없으면 빈 배열이다", () => {
    expect(recordCalculation(emptyDraft(SCOPE), BASELINE_INPUT, BASELINE_RESULT).baseline?.unconfirmed).toEqual([]);
  });

  it("선택안의 미입력 항목이 확인 목록에 사람 말로 실린다", () => {
    const draft = recordCalculation(emptyDraft(SCOPE), BASELINE_INPUT, BASELINE_RESULT, ["deposit", "desired_loan"]);

    const questions = toConsultationContext(draft).open_questions;

    expect(questions).toContain("보증금 미입력 — 0원이 맞는지 확인 필요");
    expect(questions).toContain("희망 대출금 미입력 — 0원이 맞는지 확인 필요");
  });

  it("입력한 0원은 확인 목록에 넣지 않는다 — 유효한 0원과 미입력을 구분한다", () => {
    const draft = recordCalculation(emptyDraft(SCOPE), { ...BASELINE_INPUT, key_money: 0 }, BASELINE_RESULT, []);

    expect(toConsultationContext(draft).open_questions.join(" ")).not.toMatch(/권리금/);
  });

  it("복원 시 미입력 항목이 없어도 구조 검증을 통과한다 — 이전 버전 저장값 호환", () => {
    const draft = recordCalculation(emptyDraft(SCOPE), BASELINE_INPUT, BASELINE_RESULT);
    delete (draft.baseline as { unconfirmed?: string[] }).unconfirmed;
    sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft));

    expect(loadDraft()).not.toBeNull();
  });
});
