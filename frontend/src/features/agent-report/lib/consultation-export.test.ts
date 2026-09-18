import { describe, expect, it } from "vitest";

import { canExport, toConsultationMarkdown } from "./consultation-export";
import { initialAgentState } from "./agent-events";

const HANDOFF = {
  ...initialAgentState(),
  done: true,
  sections: {
    plan: "### 상담할 계획\n\n총 준비자금 62,600,000원\n",
    comparison: "### 최초안과 현재안\n\n| 항목 | 최초안 | 현재안 |\n",
    questions: "### 상담에서 확인할 것\n\n- 설비 견적 미확정\n",
  },
  citations: [
    { title: "iM뱅크 소상공인 정책자금", url: "https://www.imbank.co.kr/example", grade: "fact" as const },
  ],
};

const META = { regionLabel: "성내1동", industryLabel: "카페", generatedAt: "2026-09-18" };

describe("내보내기 가능 조건", () => {
  it("상담자료가 끝나야 내보낼 수 있다", () => {
    expect(canExport(HANDOFF)).toBe(true);
  });

  it("생성이 끝나지 않았으면 내보내지 않는다 — 미완성을 완성으로 표시하지 않는다", () => {
    expect(canExport({ ...HANDOFF, done: false })).toBe(false);
  });

  it("이전 review 리포트는 상담자료가 아니다", () => {
    expect(canExport({ ...HANDOFF, sections: { verdict: "### 결론\n", market: "### 상권\n" } })).toBe(false);
  });

  it("빈 상태는 내보내지 않는다", () => {
    expect(canExport(initialAgentState())).toBe(false);
  });
});

describe("Markdown 변환", () => {
  it("플랫폼이 작성한 상담 준비자료임을 밝힌다", () => {
    const md = toConsultationMarkdown(HANDOFF, META);

    expect(md).toContain("상담 준비자료");
    expect(md).toContain("성내1동");
    expect(md).toContain("카페");
    expect(md).toContain("2026-09-18");
  });

  it("화면에 보인 섹션 내용을 그대로 싣는다", () => {
    const md = toConsultationMarkdown(HANDOFF, META);

    expect(md).toContain("총 준비자금 62,600,000원");
    expect(md).toContain("설비 견적 미확정");
  });

  it("출처를 링크로 남긴다", () => {
    const md = toConsultationMarkdown(HANDOFF, META);

    expect(md).toContain("[iM뱅크 소상공인 정책자금](https://www.imbank.co.kr/example)");
  });

  it("승인·접수 보장이 아님을 문서에 남긴다", () => {
    expect(toConsultationMarkdown(HANDOFF, META)).toMatch(/승인|보장/);
  });
});
