import { render, screen } from "@testing-library/react";
import { ReportView } from "./report-view";
import { initialAgentState } from "../lib/agent-events";

function stateWith(sections: Record<string, string>) {
  return { ...initialAgentState(), sections };
}

test("섹션이 없으면 안내 문구를 보여준다", () => {
  render(<ReportView state={stateWith({})} />);
  expect(screen.getByText("아직 리포트가 없습니다")).toBeInTheDocument();
});

test("상담자료 섹션을 도착 순서대로 그린다", () => {
  render(
    <ReportView
      state={stateWith({
        plan: "## 상담할 계획\n",
        comparison: "## 최초안과 현재안\n",
        calculator: "## 재무 시뮬레이션\n",
        funding: "## 자금 후보\n",
        questions: "## 상담에서 확인할 것\n",
        market: "## 지역 근거\n",
      })}
    />,
  );

  const headings = screen.getAllByRole("heading").map((h) => h.textContent);
  expect(headings).toEqual([
    "상담할 계획", "최초안과 현재안", "재무 시뮬레이션", "자금 후보", "상담에서 확인할 것", "지역 근거",
  ]);
});

test("기존 리포트 섹션도 그대로 그린다", () => {
  render(<ReportView state={stateWith({ verdict: "## 결론\n", market: "## 상권\n" })} />);

  expect(screen.getAllByRole("heading").map((h) => h.textContent)).toEqual(["결론", "상권"]);
});
