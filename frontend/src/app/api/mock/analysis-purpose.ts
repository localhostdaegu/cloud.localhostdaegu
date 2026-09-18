/** mock 전용 — POST /analysis 의 purpose 를 SSE(GET .../events)까지 잇는다.
 *
 *  SSE 요청에는 analysis_id 만 실리므로 목적을 어딘가 기억해야 한다. 실백엔드의
 *  InMemoryAnalysisRequestStore 와 같은 규칙으로 1회 소비하며, 단일 워커(dev 서버)를 전제한다.
 */
type Purpose = "review" | "handoff";

const purposes = new Map<string, Purpose>();

export function rememberPurpose(analysisId: string, purpose: Purpose): void {
  purposes.set(analysisId, purpose);
}

/** 꺼내고 지운다. 없으면 기존 경로와 같은 review. */
export function takePurpose(analysisId: string): Purpose {
  const purpose = purposes.get(analysisId) ?? "review";
  purposes.delete(analysisId);
  return purpose;
}
