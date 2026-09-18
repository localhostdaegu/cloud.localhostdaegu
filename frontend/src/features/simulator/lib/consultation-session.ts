import { apiPost, apiPut } from "@/shared/api/client";
import type { ConsultationDraft, PlanKind, PlanSnapshot } from "./consultation-draft";

/** 상담 세션 서버 기록 — 화면 상태의 정본은 여전히 sessionStorage 다(§5-3).
 *
 *  서버에 남기는 것은 **감사·재현용 스냅샷**이다. 어떤 수치를 보고 상담을 준비했는지
 *  나중에 재현하기 위한 기록이며, 리포트는 이 값을 읽지 않고 13필드로 다시 계산한다.
 *  그래서 저장 실패는 삼킨다 — 기록이 안 됐다고 상담자료 생성을 막지 않는다.
 */
const PLAN_ORDER: PlanKind[] = ["baseline", "current"];

function toPlanBody(plan: PlanSnapshot): Record<string, number> {
  const { input, result } = plan;
  return {
    ...input,
    // 계산 결과 8필드 — 서버 docstring이 '감사·재현용 스냅샷'으로 못 박은 자리다.
    capex: result.capex,
    monthly_fixed: result.monthly_fixed,
    bep_revenue: result.bep_revenue,
    funding_gap: result.funding_gap,
    reserve_months: result.reserve_months,
    operating_reserve: result.operating_reserve,
    total_required_funds: result.total_required_funds,
    external_funding_need: result.external_funding_need,
  };
}

/** 세션을 만들고 보유한 계획안을 저장한다. 실패하거나 계산안이 없으면 null. */
export async function recordConsultationSession(draft: ConsultationDraft): Promise<string | null> {
  const plans = PLAN_ORDER.filter((kind) => draft[kind] !== null);
  if (plans.length === 0) return null;

  const profile = draft.profile;
  try {
    const { session_id } = await apiPost<{ session_id: string }>("/consultation", {
      region_code: draft.region,
      industry_id: draft.industry,
      // '모름'은 null 로 보낸다 — 아니오로 바꾸면 신청 요건 판단이 틀어진다(§4-2).
      business_registered: profile.business_registered === "unknown" ? null : profile.business_registered,
      business_age_months: profile.business_age_months,
      planned_opening_date: profile.planned_opening_date,
      funds_needed_by: profile.funds_needed_by,
      owner_age: profile.owner_age,
      guarantee_status: profile.guarantee_status,
      policy_confirmation_status: profile.policy_confirmation_status,
      selected_plan_kind: draft.selected,
      change_reason: draft.change_reason,
    });

    // 순서를 보존한다 — 같은 plan_kind 재전송은 서버가 멱등 upsert 한다.
    for (const kind of plans) {
      await apiPut(`/consultation/${session_id}/plans/${kind}`, toPlanBody(draft[kind]!));
    }
    return session_id;
  } catch {
    return null;
  }
}
