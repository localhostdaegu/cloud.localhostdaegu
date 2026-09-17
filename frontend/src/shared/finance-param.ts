import type { FinanceInput } from "@/shared/api/types";

/** 시뮬레이터 → AI 리포트로 재무 입력(백엔드 SimulateRequest 13필드)을 URL 한 파라미터로 넘긴다. */
const FINANCE_KEYS = [
  "deposit",
  "key_money",
  "interior_cost",
  "equipment_cost",
  "monthly_rent",
  "monthly_payroll",
  "monthly_insurance",
  "cost_ratio",
  "fee_ratio",
  "equity",
  "desired_loan",
  "loan_rate",
  "expected_monthly_revenue",
] as const satisfies readonly (keyof FinanceInput)[];

function pick(source: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(FINANCE_KEYS.map((key) => [key, source[key]]));
}

export function encodeFinanceParam(input: FinanceInput): string {
  return JSON.stringify(pick(input as unknown as Record<string, unknown>));
}

/** 13필드가 모두 유한 number일 때만 반환한다 — 손으로 고친 URL은 조용히 무시(계산표 없이 분석). */
export function parseFinanceParam(raw: string | null): FinanceInput | undefined {
  if (!raw) return undefined;
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return undefined;
  }
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) return undefined;
  const record = parsed as Record<string, unknown>;
  const valid = FINANCE_KEYS.every((key) => typeof record[key] === "number" && Number.isFinite(record[key]));
  return valid ? (pick(record) as unknown as FinanceInput) : undefined;
}
