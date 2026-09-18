import type { AgentState } from "./agent-events";

/** 상담자료에만 있는 섹션 — 이전 review 리포트와 구분하는 기준이다(§6 T5). */
const HANDOFF_MARKER = "plan";

/** 섹션 출력 순서 — 요약이 앞, 상세 근거가 뒤(§6 T5). */
const SECTION_TITLES: [key: string, title: string][] = [
  ["plan", "상담할 계획"],
  ["comparison", "최초안과 현재안"],
  ["calculator", "재무 계산"],
  ["questions", "상담에서 확인할 것"],
  ["funding", "자금 후보"],
  ["market", "지역 근거"],
];

export interface ExportMeta {
  regionLabel: string;
  industryLabel: string;
  generatedAt: string;
}

interface Citation {
  title: string;
  url: string;
}

function isCitation(value: unknown): value is Citation {
  const c = value as Partial<Citation> | null;
  return typeof c === "object" && c !== null && typeof c.title === "string" && typeof c.url === "string";
}

/** 완성된 상담자료만 내보낸다.
 *  생성 중이거나 이전 review 결과이면 막는다 — 미완성을 완성으로 표시하지 않는다(§7-3). */
export function canExport(state: AgentState): boolean {
  return state.done && Boolean(state.sections[HANDOFF_MARKER]);
}

export function toConsultationMarkdown(state: AgentState, meta: ExportMeta): string {
  const body = SECTION_TITLES.filter(([key]) => state.sections[key]).map(([key]) => state.sections[key].trim());

  const citations = state.citations.filter(isCitation);
  const sources =
    citations.length === 0
      ? ["- 인용한 외부 자료 없음"]
      : citations.map((c) => `- [${c.title}](${c.url})`);

  return [
    `# 창업자금 상담 준비자료 — ${meta.regionLabel} ${meta.industryLabel}`,
    "",
    `작성일: ${meta.generatedAt} · 작성: localhostdaegu 플랫폼`,
    "",
    "> 이 자료는 사용자가 입력한 조건으로 계산한 상담 준비용 문서입니다.",
    "> 대출 승인·한도·금리를 보장하지 않으며, 상품의 현재 접수 가능 여부는 각 기관에서 확인해야 합니다.",
    "",
    ...body,
    "",
    "## 출처",
    "",
    ...sources,
  ].join("\n");
}
