import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { ConsultationProfileForm } from "./consultation-profile-form";
import { emptyDraft, type ConsultationProfile } from "../lib/consultation-draft";

const EMPTY: ConsultationProfile = emptyDraft({ region: null, industry: null }).profile;

const renderForm = (value: ConsultationProfile = EMPTY) => {
  const onChange = vi.fn();
  render(<ConsultationProfileForm value={value} onChange={onChange} />);
  return onChange;
};

test("사업자등록 여부를 묻고, 처음에는 아무것도 고르지 않은 상태다", () => {
  renderForm();

  expect(screen.getByRole("radio", { name: "예" })).not.toBeChecked();
  expect(screen.getByRole("radio", { name: "아니오" })).not.toBeChecked();
  expect(screen.getByRole("radio", { name: "모름" })).not.toBeChecked();
});

test("'모름'은 아니오로 바꾸지 않고 미확인으로 남긴다", () => {
  const onChange = renderForm();

  fireEvent.click(screen.getByRole("radio", { name: "모름" }));

  expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ business_registered: "unknown" }));
});

test("등록 전이면 업력을 묻지 않고 개업 예정일을 묻는다", () => {
  renderForm({ ...EMPTY, business_registered: false });

  expect(screen.queryByLabelText(/업력/)).not.toBeInTheDocument();
  expect(screen.getByLabelText(/개업 예정일/)).toBeInTheDocument();
});

test("등록했으면 업력을 묻는다", () => {
  renderForm({ ...EMPTY, business_registered: true });

  expect(screen.getByLabelText(/업력/)).toBeInTheDocument();
});

test("자금 필요일과 연령을 전달한다", () => {
  const onChange = renderForm();

  fireEvent.change(screen.getByLabelText(/자금 필요일/), { target: { value: "2026-11-01" } });
  expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ funds_needed_date: "2026-11-01" }));

  fireEvent.change(screen.getByLabelText(/연령/), { target: { value: "34" } });
  expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ owner_age: 34 }));
});

test("연령을 비우면 미입력으로 남긴다 — 0살로 만들지 않는다", () => {
  const onChange = renderForm({ ...EMPTY, owner_age: 34 });

  fireEvent.change(screen.getByLabelText(/연령/), { target: { value: "" } });

  expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ owner_age: null }));
});

test("보증·정책자금 확인서 진행 상태를 전달한다", () => {
  const onChange = renderForm();

  fireEvent.change(screen.getByLabelText(/확인서/), { target: { value: "in_progress" } });

  expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ prerequisite_status: "in_progress" }));
});
