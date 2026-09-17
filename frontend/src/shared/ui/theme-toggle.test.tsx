import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeToggle } from "./theme-toggle";

it("클릭 시 data-theme가 light↔dark 전환된다", async () => {
  document.documentElement.dataset.theme = "light";
  render(<ThemeToggle />);
  const toggle = screen.getByRole("button", { name: "테마 전환, 현재 라이트 테마" });
  expect(toggle).toHaveAttribute("aria-pressed", "false");
  await userEvent.click(toggle);
  expect(document.documentElement.dataset.theme).toBe("dark");
  expect(toggle).toHaveAccessibleName("테마 전환, 현재 다크 테마");
  expect(toggle).toHaveAttribute("aria-pressed", "true");
  await userEvent.click(toggle);
  expect(document.documentElement.dataset.theme).toBe("light");
  expect(toggle).toHaveAccessibleName("테마 전환, 현재 라이트 테마");
  expect(toggle).toHaveAttribute("aria-pressed", "false");
});
