export interface IntentResult {
  intent_type: "A" | "B" | "C";
  district_code: string | null;
  industry_slug: string | null;
  budget_krw: number | null;
  missing: string[];
}

export function intentToUrl(r: IntentResult): string {
  const p = new URLSearchParams();
  if (r.district_code) p.set("district", r.district_code);
  if (r.industry_slug) p.set("industry", r.industry_slug);
  if (r.budget_krw) p.set("budget", String(r.budget_krw));
  const q = p.toString();
  return q ? `/map?${q}` : "/map";
}
