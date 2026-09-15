import type { ParseIntentResult } from "@/features/intent-gate/api";

/** "예산 5천" → 5천만원(50,000,000원). 백엔드 파서의 축약 미러 — 화면 개발용. */
function parseBudget(text: string): number | null {
  const m = text.match(/예산\s*(\d+)\s*천/);
  return m ? Number(m[1]) * 10_000_000 : null;
}

export async function POST(request: Request) {
  const { text }: { text?: string } = await request.json().catch(() => ({}));
  const input = text ?? "";

  let result: ParseIntentResult;

  if (input.includes("서문시장")) {
    result = {
      intent_type: "A",
      district_code: "27110",
      region_name: "대신동",
      industry_id: "cafe",
      budget_krw: parseBudget(input),
      missing: [],
    };
  } else if (input.includes("동성로")) {
    const hasIndustry = input.includes("미용실");
    result = {
      intent_type: "B",
      district_code: "27110",
      region_name: "성내1동",
      industry_id: hasIndustry ? "hair_salon" : null,
      budget_krw: null,
      missing: hasIndustry ? [] : ["industry"],
    };
  } else {
    result = {
      intent_type: "C",
      district_code: null,
      region_name: null,
      industry_id: null,
      budget_krw: parseBudget(input),
      missing: ["region"],
    };
  }

  return Response.json(result);
}
