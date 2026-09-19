import { afterEach, expect, test, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RentReference, estimateMonthlyRent } from "./rent-reference";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

test("천원/㎡ × 평 → 만원 단위로 내린 월세", () => {
  // 20.55천원 × 1000 × 10평 × 3.3058㎡ = 679,341원 → 67만원
  expect(estimateMonthlyRent(20.55, 10)).toBe(670_000);
});

test("상권 평균으로 계산한 값을 월세 칸에 넣는다 — 출처와 한계를 함께 밝힌다", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () =>
      new Response(
        JSON.stringify([
          { region_name: "대구", region_level: 1, building_type: "medium_large", period: "2026Q2", rent_per_m2: 21.72, vacancy_rate: 18.9 },
          { region_name: "대구", region_level: 1, building_type: "small", period: "2026Q2", rent_per_m2: 20.55, vacancy_rate: 10.8 },
          { region_name: "동성로중심", region_level: 2, building_type: "small", period: "2026Q2", rent_per_m2: null, vacancy_rate: null },
        ]),
        { status: 200 },
      ),
    ),
  );
  const onApply = vi.fn();
  render(
    <QueryClientProvider client={new QueryClient()}>
      <RentReference onApply={onApply} />
    </QueryClientProvider>,
  );

  // 기본 선택은 소규모 상가 — 예비창업자의 점포 규모에 가깝다. 값이 없는 상권은 선택지에서 뺀다.
  fireEvent.click(await screen.findByRole("button", { name: "월세 칸에 넣기" }));
  expect(onApply).toHaveBeenCalledWith(670_000);
  expect(screen.getByText(/2026년 2분기 표본 평균/)).toBeInTheDocument();
  expect(screen.queryByRole("option", { name: /동성로중심/ })).not.toBeInTheDocument();
});
