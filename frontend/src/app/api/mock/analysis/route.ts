import { rememberPurpose } from "../analysis-purpose";

export async function POST(request: Request) {
  const analysisId = crypto.randomUUID();
  // 본문이 없거나 깨져도 mock 이 멈추지 않게 한다 — 목적을 모르면 review 다.
  const body = await request.json().catch(() => ({}));
  if (body?.purpose === "handoff") rememberPurpose(analysisId, "handoff");
  return Response.json({ analysis_id: analysisId });
}
