import { render, screen } from "@testing-library/react";
import { TopBar } from "./top-bar";

vi.mock("next/navigation", () => ({
  usePathname: () => "/analysis",
}));

it("현재 경로의 탭에 aria-current가 표시된다", () => {
  render(<TopBar />);
  expect(screen.getByRole("navigation", { name: "주요 메뉴" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "AI 분석" })).toHaveAttribute("aria-current", "page");
  expect(screen.getByRole("link", { name: "지도 탐색" })).not.toHaveAttribute("aria-current");
});

it("BI 로고가 홈 버튼으로 첫 화면(채팅 진입)에 연결된다", () => {
  const { container } = render(<TopBar />);
  const home = screen.getByRole("link", { name: "홈" });
  expect(home).toHaveAttribute("href", "/");
  expect(home).not.toHaveAttribute("aria-current");
  // 라이트·다크 테마별 로고 2종 (data-theme 로 하나만 표시)
  const logos = [...home.querySelectorAll("img")].map((img) => img.getAttribute("src"));
  expect(logos.some((src) => src?.includes("logo-light"))).toBe(true);
  expect(logos.some((src) => src?.includes("logo-dark"))).toBe(true);
  expect(container.textContent).not.toContain("localhostdaegu");
});
