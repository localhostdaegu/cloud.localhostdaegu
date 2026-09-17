import { render, screen } from "@testing-library/react";
import { TopBar } from "./top-bar";

vi.mock("next/navigation", () => ({
  usePathname: () => "/analysis",
}));

it("현재 경로의 탭에 aria-current가 표시된다", () => {
  render(<TopBar />);
  expect(screen.getByRole("link", { name: "AI 분석" })).toHaveAttribute("aria-current", "page");
  expect(screen.getByRole("link", { name: "지도 탐색" })).not.toHaveAttribute("aria-current");
});

it("홈 탭이 첫 화면(채팅 진입)으로 연결된다", () => {
  render(<TopBar />);
  expect(screen.getByRole("link", { name: "홈" })).toHaveAttribute("href", "/");
  expect(screen.getByRole("link", { name: "홈" })).not.toHaveAttribute("aria-current");
});
