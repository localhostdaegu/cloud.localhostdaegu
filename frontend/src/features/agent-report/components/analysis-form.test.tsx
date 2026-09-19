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

it("추가 질문 placeholder와 예시 칩은 고른 업종을 따라 바뀐다", () => {
  render(<AnalysisForm initialRegion="2711059500" initialIndustry="cafe" onSubmit={vi.fn()} />);

  const textarea = screen.getByLabelText(/추가 질문/) as HTMLTextAreaElement;
  expect(textarea.placeholder).toMatch(/카페/);
  expect(screen.getAllByRole("button", { name: /예시 질문:/ })).toHaveLength(3);

  fireEvent.change(screen.getByLabelText("업종"), { target: { value: "academy" } });

  expect(textarea.placeholder).toMatch(/학령인구/);
  expect(screen.getByRole("button", { name: /예시 질문:.*정책자금/ })).toBeInTheDocument();
});

it("예시 칩을 누르면 입력칸이 그 문구로 채워지고 제출값에 실린다", () => {
  const onSubmit = vi.fn();
  render(<AnalysisForm initialRegion="2711059500" initialIndustry="karaoke" onSubmit={onSubmit} />);

  const chip = screen.getAllByRole("button", { name: /예시 질문:/ })[0];
  const text = chip.textContent ?? "";
  fireEvent.click(chip);

  expect((screen.getByLabelText(/추가 질문/) as HTMLTextAreaElement).value).toBe(text);
  fireEvent.click(screen.getByRole("button", { name: "분석 시작" }));
  expect(onSubmit).toHaveBeenCalledWith({ region: "2711059500", industry: "karaoke", question: text });
});

it("업종을 바꿔도 이미 적은 질문은 지우지 않는다", () => {
  render(<AnalysisForm initialRegion="2711059500" initialIndustry="cafe" onSubmit={vi.fn()} />);
  const textarea = screen.getByLabelText(/추가 질문/) as HTMLTextAreaElement;
  fireEvent.change(textarea, { target: { value: "직접 쓴 질문" } });
  fireEvent.change(screen.getByLabelText("업종"), { target: { value: "gym" } });
  expect(textarea.value).toBe("직접 쓴 질문");
});
