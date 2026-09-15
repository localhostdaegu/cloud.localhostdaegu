import { afterEach, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SidePanel } from "./side-panel";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

const REGION = "2711051000";

it("B유형(industryParam=null): 업종별 랭킹이 렌더되고, 행 클릭 시 onSelectIndustry가 해당 industry_id로 호출된다", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/metrics/risk") && url.includes("region_code=")) {
        return new Response(
          JSON.stringify([
            { industry_id: "gym", score: 71.3, grade: "red", components: { closure: 37.5, density: 33.7, growth: 0.1 } },
            { industry_id: "cafe", score: 45.8, grade: "yellow", components: { closure: 13.1, density: 30.3, growth: 2.4 } },
          ]),
          { status: 200 },
        );
      }
      throw new Error(`unexpected fetch: ${url}`);
    }),
  );

  const onSelectIndustry = vi.fn();
  renderWithClient(
    <SidePanel regionCode={REGION} industry="cafe" industryParam={null} onSelectIndustry={onSelectIndustry} />,
  );

  const gymRow = await screen.findByRole("button", { name: /헬스장/ });
  expect(screen.getByRole("button", { name: /카페/ })).toBeInTheDocument();

  gymRow.click();

  expect(onSelectIndustry).toHaveBeenCalledWith("gym");
});

it("404(RISK_NOT_FOUND): 에러 배너가 아니라 '이 조합의 진단 데이터가 아직 없어요' 문구가 렌더된다", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/regions/") && url.includes("/summary")) {
        return new Response(
          JSON.stringify({ region_code: REGION, name: "성내1동", industry_id: "cafe", cards: [] }),
          { status: 200 },
        );
      }
      if (url.includes("/metrics/risk") && url.includes("industry=")) {
        return new Response(
          JSON.stringify({ error: { code: "RISK_NOT_FOUND", message: `위험도 데이터 없음: region=${REGION}, industry=cafe` } }),
          { status: 404 },
        );
      }
      throw new Error(`unexpected fetch: ${url}`);
    }),
  );

  renderWithClient(
    <SidePanel regionCode={REGION} industry="cafe" industryParam="cafe" onSelectIndustry={vi.fn()} />,
  );

  await waitFor(() => expect(screen.getByText("이 조합의 진단 데이터가 아직 없어요")).toBeInTheDocument());
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});
