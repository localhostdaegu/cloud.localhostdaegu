import { afterEach, expect, test, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { BankHandoff } from "./bank-handoff";
import { initialAgentState } from "../lib/agent-events";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

const DONE = {
  ...initialAgentState(),
  done: true,
  sections: { plan: "### 상담할 계획\n\n총 준비자금 62,600,000원\n" },
  citations: [],
};
const META = { regionLabel: "성내1동", industryLabel: "카페", generatedAt: "2026-09-18" };

const renderHandoff = (state = DONE) => render(<BankHandoff state={state} meta={META} />);

test("자료가 완성되기 전에는 저장할 수 없다", () => {
  renderHandoff({ ...DONE, done: false });

  expect(screen.getByRole("button", { name: /상담자료 저장/ })).toBeDisabled();
});

test("이전 review 결과는 저장할 수 없다 — 선택안이 바뀌면 옛 자료가 나가지 않는다", () => {
  renderHandoff({ ...DONE, sections: { verdict: "### 결론\n" } });

  expect(screen.getByRole("button", { name: /상담자료 저장/ })).toBeDisabled();
});

test("완성된 자료는 Markdown 으로 저장한다", () => {
  const createObjectURL = vi.fn(() => "blob:fake");
  vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL: vi.fn() });
  renderHandoff();

  fireEvent.click(screen.getByRole("button", { name: /상담자료 저장/ }));

  expect(createObjectURL).toHaveBeenCalledTimes(1);
});

test("인쇄로 PDF 저장을 안내한다 — PDF 전용 라이브러리를 쓰지 않는다", () => {
  const print = vi.fn();
  vi.stubGlobal("print", print);
  renderHandoff();

  fireEvent.click(screen.getByRole("button", { name: /인쇄/ }));

  expect(print).toHaveBeenCalled();
});

test("iM뱅크 공식 상담 안내 링크를 제공한다", () => {
  renderHandoff();

  const link = screen.getByRole("link", { name: /iM뱅크 공식 상담 안내/ });
  expect(link).toHaveAttribute("href", expect.stringContaining("imbank.co.kr"));
  expect(link).toHaveAttribute("target", "_blank");
});

test("링크 이동이 은행에 자료를 보내는 것이 아님을 밝힌다", () => {
  renderHandoff();

  // <strong> 때문에 텍스트가 여러 노드로 나뉜다 — 문단 단위로 확인한다.
  expect(screen.getByText(/자료가 전송되지 않습니다/).closest("p")).toHaveTextContent(
    /직접 지참.*전송되지 않습니다/,
  );
});
