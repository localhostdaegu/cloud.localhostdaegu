import { apiGet, apiPost } from "@/shared/api/client";
import type { FinanceInput, FinanceOutput, MatchingProduct } from "@/shared/api/types";

export function simulateFinance(payload: FinanceInput): Promise<FinanceOutput> {
  return apiPost<FinanceOutput>("/finance/simulate", payload);
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
