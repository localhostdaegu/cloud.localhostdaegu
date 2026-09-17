import { expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import type { FinanceInput } from "@/shared/api/types";
import { AnalysisForm } from "./analysis-form";

const FINANCE = { deposit: 1, equity: 2 } as unknown as FinanceInput;

it("finance가 있으면 안내 문구를 보이고 제출 params에 포함한다", () => {
  const onSubmit = vi.fn();
  render(<AnalysisForm initialRegion="2711059500" initialIndustry="cafe" finance={FINANCE} onSubmit={onSubmit} />);

  expect(screen.getByText(/시뮬레이션 입력이 함께 전달돼요/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "분석 시작" }));

  expect(onSubmit).toHaveBeenCalledWith({ region: "2711059500", industry: "cafe", question: undefined, finance: FINANCE });
});

it("finance가 없으면 안내 문구 없이 기존 params만 제출한다", () => {
  const onSubmit = vi.fn();
  render(<AnalysisForm initialRegion="2711059500" initialIndustry="cafe" onSubmit={onSubmit} />);

  expect(screen.queryByText(/시뮬레이션 입력이 함께 전달돼요/)).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "분석 시작" }));

  expect(onSubmit).toHaveBeenCalledWith({ region: "2711059500", industry: "cafe", question: undefined });
});
