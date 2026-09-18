import { apiGet, apiPost } from "@/shared/api/client";
import type {
  ConsultationCandidate,
  ConsultationFinanceOutput,
  FinanceInput,
  LatestRate,
  MatchingProduct,
} from "@/shared/api/types";

export function simulateFinance(payload: FinanceInput): Promise<ConsultationFinanceOutput> {
  return apiPost<ConsultationFinanceOutput>("/finance/simulate", payload);
}

/** ECOS 적재 금리 중 rate_type의 최신 월 값 (GET /shocks/rates/latest). */
export function fetchLatestRate(rateType: string): Promise<LatestRate> {
  return apiGet<LatestRate>(`/shocks/rates/latest?${new URLSearchParams({ rate_type: rateType }).toString()}`);
}

/** 예비창업 전제(business_age_months=0)로 고정, owner_age는 미수집이라 전달하지 않는다.
 *  category는 백엔드(matching_router.py)가 필수 파라미터로 요구하므로 미지정이어도 빈 문자열로 항상 전송한다
 *  — 빈 문자열이면 matcher가 전업종(category=null) 상품만 통과시켜 의미론도 자연스럽다. */
export function fetchMatching(fundingGap: number, category?: string): Promise<MatchingProduct[]> {
  const params = new URLSearchParams({
    funding_gap: String(fundingGap),
    business_age_months: "0",
  });
  params.set("category", category ?? "");
  return apiGet<MatchingProduct[]>(`/matching?${params.toString()}`);
}


export interface ConsultationQuery {
  externalFundingNeed: number;
  category?: string;
  businessRegistered?: boolean | null;
  businessAgeMonths?: number | null;
  ownerAge?: number | null;
}

/** GET /matching/consultation — 미입력 값은 쿼리에서 생략한다.
 *  생략을 '해당 없음'으로 바꾸면 백엔드가 자격 판정을 잘못하게 된다(§5-2). */
export function fetchConsultationCandidates(query: ConsultationQuery): Promise<ConsultationCandidate[]> {
  const params = new URLSearchParams({
    external_funding_need: String(query.externalFundingNeed),
    category: query.category ?? "",
  });
  if (query.businessRegistered != null) params.set("business_registered", String(query.businessRegistered));
  if (query.businessAgeMonths != null) params.set("business_age_months", String(query.businessAgeMonths));
  if (query.ownerAge != null) params.set("owner_age", String(query.ownerAge));
  // 근거 미확인 상품도 '관련 기관 참고자료'로 받아 화면에서 분리해 보여준다(§5-2).
  params.set("include_unverified", "true");
  return apiGet<ConsultationCandidate[]>(`/matching/consultation?${params.toString()}`);
}
