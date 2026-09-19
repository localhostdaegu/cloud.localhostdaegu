import { afterEach, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RegionTrend } from "./region-trend";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

const REGION = "2711059500";

it("연도별 점포 수와 폐업률 최고 해를 문장으로도 알려 준다 — 집계 중인 해는 폐업률에서 뺀다", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes("/shocks")) {
        return new Response(
          JSON.stringify([
            { event_id: "a", layer: "regional", name: "대구 첫 확진", start_date: "2020-02-18", end_date: null, scope: "대구", source_url: null, industry_impacts: [{ industry_id: "cafe", severity: "high" }] },
            { event_id: "b", layer: "policy", name: "최저임금 인상", start_date: "2021-01-01", end_date: null, scope: "전국", source_url: null, industry_impacts: [{ industry_id: "cafe", severity: "medium" }] },
          ]),
          { status: 200 },
        );
      }
      const params = new URL(String(input), "http://x").searchParams;
      const year = Number(params.get("year"));
      const value = params.get("metric") === "store_count" ? 50 + (year - 2019) : year === 2026 ? 0.9 : (year - 2019) / 20;
      return new Response(JSON.stringify([{ region_code: REGION, value }]), { status: 200 });
    }),
  );
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <RegionTrend regionCode={REGION} industry="cafe" />
    </QueryClientProvider>,
  );

  expect(await screen.findByText(/점포 수 2019년 50개 → 2025년 56개 · 폐업률 최고 2025년 30.0% · 2026년은 집계 중/)).toBeInTheDocument();
  // 영향이 컸던(high) 사건만 짚는다 — 매년 있는 medium 사건은 차트를 덮지 않게 뺀다.
  expect(await screen.findByText("대구 첫 확진")).toBeInTheDocument();
  expect(screen.queryByText("최저임금 인상")).not.toBeInTheDocument();
});
