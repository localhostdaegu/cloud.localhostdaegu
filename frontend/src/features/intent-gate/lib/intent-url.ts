export interface IntentResult {
  intent_type: "A" | "B" | "C";
  district_code: string | null;
  /** 말한 동네(서문시장→대신동)의 행정동 코드 — 있으면 지도가 그 동을 바로 고른다. */
  region_code?: string | null;
  industry_id: string | null;
  budget_krw: number | null;
  missing: string[];
}

export function intentToUrl(r: IntentResult): string {
  const p = new URLSearchParams();
  if (r.district_code) p.set("district", r.district_code);
  if (r.region_code) p.set("region", r.region_code);
  if (r.industry_id) p.set("industry", r.industry_id);
  if (r.budget_krw) p.set("budget", String(r.budget_krw));
  const q = p.toString();
  return q ? `/map?${q}` : "/map";
}
