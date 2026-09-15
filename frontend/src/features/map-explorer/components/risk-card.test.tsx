import { render, screen } from "@testing-library/react";
import { RiskCard } from "./risk-card";

test("renders score, grade label, and three components", () => {
  render(<RiskCard score={68} grade="yellow" components={{ closure: 30, density: 28, growth: 10 }} />);
  expect(screen.getByText("68")).toBeInTheDocument();
  expect(screen.getByText("진입 주의")).toBeInTheDocument();   // yellow=주의, red=고위험, green=양호
  expect(screen.getByText(/폐업률/)).toBeInTheDocument();
  expect(screen.getByText(/경쟁밀도/)).toBeInTheDocument();
  expect(screen.getByText(/신규진입/)).toBeInTheDocument();
});
