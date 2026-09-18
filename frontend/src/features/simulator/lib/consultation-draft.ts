import type { ConsultationFinanceOutput, FinanceInput } from "@/shared/api/types";

/** 전환계획 §5-3 — 한 탭의 한 계획을 보관한다. 장기 저장이 아니다. */
export const DRAFT_KEY = "localhostdaegu.consultation.v1";
const VERSION = 1;

export type PlanKind = "baseline" | "current";

/** 창업 단계·시점 — 사용자가 직접 확인해 입력한다. 모름을 0·아니오로 바꾸지 않는다(§4-2). */
export interface ConsultationProfile {
  /** null = 아직 묻지 않음 / "unknown" = 사용자가 모른다고 답함. 둘 다 미확인이지만
   *  전자는 물어봐야 하고 후자는 상담에서 확인할 항목이다(§4-2). */
  business_registered: boolean | "unknown" | null;
  business_age_months: number | null;
  opening_date: string | null;
  funds_needed_date: string | null;
  owner_age: number | null;
  /** 보증·정책자금 확인서 진행 상태 — 선행 절차가 남았는지 상담에서 확인한다(§3-3). */
  prerequisite_status: PrerequisiteStatus | null;
}

export type PrerequisiteStatus = "not_started" | "in_progress" | "done";

export interface PlanSnapshot {
  input: FinanceInput;
  result: ConsultationFinanceOutput;
}

export interface ConsultationScope {
  region: string | null;
  industry: string | null;
}

export interface ConsultationDraft extends ConsultationScope {
  version: number;
  /** 최초안 — 첫 성공 계산으로 고정한다. */
  baseline: PlanSnapshot | null;
  /** 현재안 — 이후 계산이 갱신한다. */
  current: PlanSnapshot | null;
  selected: PlanKind | null;
  profile: ConsultationProfile;
}

const AMOUNT_FIELDS = [
  "deposit", "key_money", "interior_cost", "equipment_cost",
  "monthly_rent", "monthly_payroll", "monthly_insurance",
  "equity", "desired_loan", "expected_monthly_revenue",
] as const;
const RATIO_FIELDS = ["cost_ratio", "fee_ratio", "loan_rate"] as const;

export function emptyDraft(scope: ConsultationScope): ConsultationDraft {
  return {
    version: VERSION,
    region: scope.region,
    industry: scope.industry,
    baseline: null,
    current: null,
    selected: null,
    profile: {
      business_registered: null,
      business_age_months: null,
      opening_date: null,
      funds_needed_date: null,
      owner_age: null,
      prerequisite_status: null,
    },
  };
}

/** 첫 성공 계산은 최초안으로 고정하고, 이후 계산은 현재안을 갱신한다.
 *  방금 계산한 안을 선택안으로 둬 선택안이 늘 유효한 계산안을 가리키게 한다. */
export function recordCalculation(
  draft: ConsultationDraft,
  input: FinanceInput,
  result: ConsultationFinanceOutput,
): ConsultationDraft {
  const snapshot: PlanSnapshot = { input: { ...input }, result: { ...result } };
  return draft.baseline === null
    ? { ...draft, baseline: snapshot, selected: "baseline" }
    : { ...draft, current: snapshot, selected: "current" };
}

/** 없는 계산안은 선택하지 않는다 — 최종자료가 빈 선택안을 쓰지 못하게 한다. */
export function selectPlan(draft: ConsultationDraft, kind: PlanKind): ConsultationDraft {
  return draft[kind] === null ? draft : { ...draft, selected: kind };
}

export function selectedPlan(draft: ConsultationDraft): PlanSnapshot | null {
  return draft.selected === null ? null : draft[draft.selected];
}

/** 지역·업종이 바뀌면 비교 대상이 달라지므로 이전 결과·선택을 무효화한다.
 *  상담 정보는 사람에 대한 정보라 유지한다. */
export function withScope(draft: ConsultationDraft, scope: ConsultationScope): ConsultationDraft {
  if (draft.region === scope.region && draft.industry === scope.industry) return draft;
  return { ...emptyDraft(scope), profile: draft.profile };
}

export function saveDraft(draft: ConsultationDraft): void {
  try {
    sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
  } catch {
    // 저장 실패는 계산을 막지 않는다 — 복원 시 다시 입력하도록 안내한다.
  }
}

/** 구조·금액·비율을 검증해 복원한다. 어긋나면 null 이다 — 다시 입력하도록 안내해야 한다. */
export function loadDraft(): ConsultationDraft | null {
  let raw: string | null;
  try {
    raw = sessionStorage.getItem(DRAFT_KEY);
  } catch {
    return null;
  }
  if (raw === null) return null;

  try {
    const parsed = JSON.parse(raw) as ConsultationDraft;
    return isValidDraft(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function isValidDraft(draft: ConsultationDraft): boolean {
  if (draft?.version !== VERSION) return false;
  if (!isValidPlan(draft.baseline) || !isValidPlan(draft.current)) return false;
  if (draft.selected !== null && draft[draft.selected] == null) return false;
  return true;
}

function isValidPlan(plan: PlanSnapshot | null): boolean {
  if (plan == null) return true;
  const { input, result } = plan;
  if (input == null || result == null) return false;
  if (!AMOUNT_FIELDS.every((f) => Number.isFinite(input[f]) && input[f] >= 0)) return false;
  if (!RATIO_FIELDS.every((f) => Number.isFinite(input[f]) && input[f] >= 0 && input[f] < 1)) return false;
  // 백엔드 422 와 같은 규칙 — 변동비율 ≥ 1 이면 BEP 가 성립하지 않는다.
  if (input.cost_ratio + input.fee_ratio >= 1) return false;
  return Number.isFinite(result.external_funding_need) && Number.isFinite(result.total_required_funds);
}
