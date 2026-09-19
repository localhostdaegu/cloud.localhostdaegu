import { expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import type { FinanceInput } from "@/shared/api/types";
import { AnalysisForm } from "./analysis-form";

const FINANCE = { deposit: 1, equity: 2 } as unknown as FinanceInput;

it("finance가 있으면 안내 문구를 보이고 제출 params에 포함한다", () => {
  const onSubmit = vi.fn();
  render(<AnalysisForm initialRegion="2711059500" initialIndustry="cafe" finance={FINANCE} onSubmit={onSubmit} />);

  expect(screen.getByText(/시뮬레이션 입력이 함께 전달돼요/)).toBeInTheDocument();
  // 사전상담에서 넘어온 사람에게는 목적(은행에 가져갈 자료)으로 버튼을 부른다.
  fireEvent.click(screen.getByRole("button", { name: "상담자료 만들기" }));

  expect(onSubmit).toHaveBeenCalledWith({ region: "2711059500", industry: "cafe", question: undefined, finance: FINANCE });
});

it("finance가 없으면 안내 문구 없이 기존 params만 제출한다", () => {
  const onSubmit = vi.fn();
  render(<AnalysisForm initialRegion="2711059500" initialIndustry="cafe" onSubmit={onSubmit} />);

  expect(screen.queryByText(/시뮬레이션 입력이 함께 전달돼요/)).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "분석 시작" }));

  expect(onSubmit).toHaveBeenCalledWith({ region: "2711059500", industry: "cafe", question: undefined });
});

it("행정동은 10자리 코드가 아니라 동 이름으로 고른다 — 제출값은 코드다", () => {
  const onSubmit = vi.fn();
  render(
    <AnalysisForm
      initialRegion=""
      initialIndustry="cafe"
      regions={[{ code: "2711059500", name: "대신동" }]}
      onSubmit={onSubmit}
    />,
  );

  expect(screen.queryByLabelText("지역 코드")).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("행정동"), { target: { value: "2711059500" } });
  fireEvent.click(screen.getByRole("button", { name: "분석 시작" }));

  expect(onSubmit).toHaveBeenCalledWith({ region: "2711059500", industry: "cafe", question: undefined });
});
