import { expect, it } from "vitest";
import { INDUSTRIES } from "@/shared/industries";
import { EXAMPLE_QUESTIONS, FALLBACK_QUESTION, exampleQuestions } from "./example-questions";

it("등록 업종 11종 전부에 예시 질문이 3개씩 있다", () => {
  for (const id of INDUSTRIES) {
    expect(EXAMPLE_QUESTIONS[id], id).toHaveLength(3);
  }
});

it("예시 질문은 손익분기·매출 같은 계산 질문을 담지 않는다 — LLM은 계산하지 않는다", () => {
  for (const id of INDUSTRIES) {
    for (const q of EXAMPLE_QUESTIONS[id]) {
      expect(q, `${id}: ${q}`).not.toMatch(/손익분기|매출/);
    }
  }
});

it("미등록 업종(딥링크 임의 값)은 일반 문구 1개로 폴백한다", () => {
  expect(exampleQuestions("unknown_industry")).toEqual([FALLBACK_QUESTION]);
  expect(exampleQuestions("")).toEqual([FALLBACK_QUESTION]);
});

it("등록 업종은 사전의 문구를 그대로 돌려준다", () => {
  expect(exampleQuestions("cafe")).toEqual(EXAMPLE_QUESTIONS.cafe);
});
