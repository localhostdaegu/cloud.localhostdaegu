import { afterEach, expect, it, test, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProgressPanel } from "./progress-panel";
import { applyAgentEvent, initialAgentState } from "../lib/agent-events";

afterEach(() => vi.restoreAllMocks());

it("동일 tool+summary 이벤트가 반복돼도 key 중복 경고가 없다", () => {
  const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

  const ev = { type: "tool_call", agent: "market", tool: "sql.query", summary: "매출 추이 조회" } as const;
  let state = initialAgentState();
  state = applyAgentEvent(state, ev);
  state = applyAgentEvent(state, ev); // 같은 도구를 같은 요약으로 두 번 호출

  render(<ProgressPanel state={state} />);

  const dupKeyWarnings = errorSpy.mock.calls.filter((args) => String(args[0]).includes("same key"));
  expect(dupKeyWarnings).toHaveLength(0);
});

test("진행 단계를 내부 에이전트·도구명이 아니라 사용자가 읽는 말로 보여준다", () => {
  const state = {
    ...initialAgentState(),
    agents: {
      ...initialAgentState().agents,
      funding: { status: "running" as const, tools: [
        { tool: "finance_simulate", summary: "재무 시뮬레이션 — 조달 필요 100원" },
        { tool: "product_matching", summary: "금융상품 매칭 — 3건" },
      ] },
    },
  };

  render(<ProgressPanel state={state} />);

  expect(screen.getByText("자금 계산")).toBeInTheDocument();
  expect(screen.getByText("상담 후보 정리")).toBeInTheDocument();
  expect(screen.getByText("준비자금 계산")).toBeInTheDocument();
  expect(screen.queryByText("충격 분석")).not.toBeInTheDocument();
  expect(screen.queryByText("finance_simulate")).not.toBeInTheDocument();
});
