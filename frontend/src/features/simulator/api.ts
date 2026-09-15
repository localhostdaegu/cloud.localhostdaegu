import { apiPost } from "@/shared/api/client";
import type { FinanceInput, FinanceOutput } from "@/shared/api/types";

export function simulateFinance(payload: FinanceInput): Promise<FinanceOutput> {
  return apiPost<FinanceOutput>("/finance/simulate", payload);
}
