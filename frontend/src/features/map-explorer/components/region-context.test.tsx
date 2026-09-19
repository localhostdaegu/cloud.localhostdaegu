import { afterEach, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RegionContext } from "./region-context";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

const renderContext = () =>
  render(
    <QueryClientProvider client={new QueryClient()}>
      <RegionContext regionCode="2711059500" />
    </QueryClientProvider>,
  );

it("인구 변화·동네 특성·지하철 시간대를 보여 주고, 인구를 수요로 읽지 말라고 밝힌다", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/populations/")) {
        return new Response(
          JSON.stringify({
            region_code: "2711059500", latest_period: "202606", base_period: "202012",
            latest_total: 7263, base_total: 8094,
            age_bands: [{ label: "60세 이상", latest: 2209, base: 2076 }],
          }),
          { status: 200 },
        );
      }
      return new Response(
        JSON.stringify([
          { indicator_key: "traditional_market_count", breakdown: null, period: "202609", value: 8, unit: "곳" },
          { indicator_key: "nadeul_store_count", breakdown: null, period: "202609", value: 0, unit: "곳" },
          { indicator_key: "subway_boarding_daily_avg", breakdown: "time_14_18", period: "202607", value: 2213.8, unit: "명" },
        ]),
        { status: 200 },
      );
    }),
  );
  renderContext();

  expect(await screen.findByText("7,263명")).toBeInTheDocument();
  expect(screen.getByText("-10.3%")).toBeInTheDocument(); // 8,094 → 7,263
  expect(screen.getByText("+6.4%")).toBeInTheDocument(); // 60세 이상 2,076 → 2,209
  expect(screen.getByText(/방문객이나 매출로 바꿔 읽지 마세요/)).toBeInTheDocument();
  expect(await screen.findByText(/전통시장/)).toHaveTextContent("전통시장 8곳");
  expect(screen.queryByText(/나들가게/)).not.toBeInTheDocument(); // 0곳은 특성이 아니다
  expect(screen.getByText("14~18시")).toBeInTheDocument();
});

it("자료가 없는 동은 아무것도 그리지 않는다", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) =>
      String(input).includes("/populations/")
        ? new Response(JSON.stringify({ error: { code: "POPULATION_NOT_FOUND", message: "없음" } }), { status: 404 })
        : new Response("[]", { status: 200 }),
    ),
  );
  const { container } = renderContext();

  await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  expect(container.textContent).toBe("");
});
