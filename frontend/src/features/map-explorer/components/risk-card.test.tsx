import { render, screen } from "@testing-library/react";
import { RiskCard } from "./risk-card";

test("renders score, grade label, and three components", () => {
  render(<RiskCard score={68} grade="yellow" components={{ closure: 30, density: 28, growth: 10 }} />);
  expect(screen.getByText("68")).toBeInTheDocument();
  expect(screen.getByText("상대 위험 중간")).toBeInTheDocument();   // yellow=중간, red=높음, green=낮음
  expect(screen.getByText(/폐업률/)).toBeInTheDocument();
  expect(screen.getByText(/점포 수 순위/)).toBeInTheDocument();
  expect(screen.getByText(/점포 증감/)).toBeInTheDocument();
});

test("OPEN-009 — 절대 판정 대신 동네 간 상대 순위로 풀어 쓴다", () => {
  render(
    <RiskCard score={83.1} grade="red" components={{ closure: 38, density: 25, growth: 19 }} rank={{ position: 3, total: 141 }} />,
  );
  expect(screen.getByText(/대구 141개 동 가운데 3번째로 높아요/)).toBeInTheDocument();
  expect(screen.getByText(/실패 확률이 아닙니다/)).toBeInTheDocument();
  expect(screen.queryByText(/진입/)).not.toBeInTheDocument();
});
