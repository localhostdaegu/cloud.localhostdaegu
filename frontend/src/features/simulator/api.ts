import { apiGet, apiPost } from "@/shared/api/client";
import type { FinanceInput, FinanceOutput, MatchingProduct } from "@/shared/api/types";

export function simulateFinance(payload: FinanceInput): Promise<FinanceOutput> {
  return apiPost<FinanceOutput>("/finance/simulate", payload);
}

/** 예비창업 전제(business_age_months=0)로 고정, owner_age는 미수집이라 전달하지 않는다. */
export function fetchMatching(fundingGap: number, category?: string): Promise<MatchingProduct[]> {
  const params = new URLSearchParams({
    funding_gap: String(fundingGap),
    business_age_months: "0",
  });
  if (category) params.set("category", category);
  return apiGet<MatchingProduct[]>(`/matching?${params.toString()}`);
}
