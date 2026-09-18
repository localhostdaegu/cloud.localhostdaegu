import { afterEach, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SimulatorPage } from "./simulator-page";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("industry=cafe&budget=50000000"),
}));

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <SimulatorPage />
    </QueryClientProvider>,
  );
}

const loanRateInput = () => screen.getByLabelText(/대출금리/);

const LATEST_SME = { rate_type: "loan_sme", period: "202607", value_percent: 4.22, value_ratio: 0.0422 };

it("최신 중소기업대출 금리(ECOS)가 오면 대출금리 기본값을 그 값으로 채운다", async () => {
  const fetchMock = vi.fn(async () => new Response(JSON.stringify(LATEST_SME), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);

  renderPage();

  expect(loanRateInput()).toHaveValue(4.5); // 로딩 중에는 고정 기본값으로 폼이 바로 뜬다
  await waitFor(() => expect(loanRateInput()).toHaveValue(4.2)); // 0.0422 → 4.2% 표시
  expect(String(fetchMock.mock.calls[0][0])).toContain("/shocks/rates/latest?rate_type=loan_sme");
});

it("금리 조회가 실패하면 4.5% 기본값을 유지하고 폼은 계속 쓸 수 있다", async () => {
  const fetchMock = vi.fn(
    async () =>
      new Response(JSON.stringify({ error: { code: "RATE_NOT_FOUND", message: "없음" } }), { status: 404 }),
  );
  vi.stubGlobal("fetch", fetchMock);

  renderPage();

  await waitFor(() => expect(fetchMock).toHaveBeenCalled());
  await new Promise((resolve) => setTimeout(resolve, 0));
  expect(loanRateInput()).toHaveValue(4.5);
  expect(screen.getByRole("button", { name: "시뮬레이션 실행" })).toBeEnabled();
});

it("사용자가 먼저 고친 대출금리는 늦게 도착한 최신 금리로 덮어쓰지 않는다", async () => {
  let respond: (response: Response) => void = () => {};
  vi.stubGlobal(
    "fetch",
    vi.fn(() => new Promise<Response>((resolve) => (respond = resolve))),
  );

  renderPage();
  fireEvent.change(loanRateInput(), { target: { value: "6" } });
  respond(new Response(JSON.stringify(LATEST_SME), { status: 200 }));

  await new Promise((resolve) => setTimeout(resolve, 20));
  expect(loanRateInput()).toHaveValue(6);
});

// --- 전환계획 T2: 계산안 보관·비교·선택 -------------------------------------

const OUTPUT_BASELINE = {
  capex: 50_000_000, monthly_fixed: 3_000_000, bep_revenue: 7_500_000, funding_gap: 8_000_000,
  reserve_months: 6, operating_reserve: 18_000_000,
  total_required_funds: 68_000_000, external_funding_need: 8_000_000,
  scenarios: [], stress: [],
};
const OUTPUT_REVISED = {
  ...OUTPUT_BASELINE,
  monthly_fixed: 2_000_000, bep_revenue: 5_000_000, funding_gap: 2_000_000,
  operating_reserve: 12_000_000, total_required_funds: 62_000_000, external_funding_need: 2_000_000,
};

/** 금리 조회는 404, /finance/simulate 는 호출 순서대로 응답한다. */
function stubSimulate(...outputs: object[]) {
  let call = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string | URL) => {
      if (String(url).includes("/finance/simulate")) {
        return new Response(JSON.stringify(outputs[Math.min(call++, outputs.length - 1)]), { status: 200 });
      }
      if (String(url).includes("/matching")) return new Response("[]", { status: 200 });
      return new Response(JSON.stringify({ error: { code: "RATE_NOT_FOUND", message: "없음" } }), { status: 404 });
    }),
  );
}

const runSimulation = async () => {
  fireEvent.click(screen.getByRole("button", { name: "시뮬레이션 실행" }));
  await waitFor(() => expect(screen.getByText("자기자본 외 조달 필요")).toBeInTheDocument());
};

const setRent = (manwon: string) =>
  fireEvent.change(screen.getByLabelText(/월세/), { target: { value: manwon } });

it("첫 계산이 최초안으로 저장된다", async () => {
  sessionStorage.clear();
  stubSimulate(OUTPUT_BASELINE);
  renderPage();

  await runSimulation();

  const draft = JSON.parse(sessionStorage.getItem("localhostdaegu.consultation.v1")!);
  expect(draft.selected).toBe("baseline");
  expect(draft.baseline.result.external_funding_need).toBe(8_000_000);
  expect(draft.current).toBeNull();
});

it("두 번째 계산에서 비교표가 뜨고 현재안이 선택된다", async () => {
  sessionStorage.clear();
  stubSimulate(OUTPUT_BASELINE, OUTPUT_REVISED);
  renderPage();

  await runSimulation();
  setRent("100");
  fireEvent.click(screen.getByRole("button", { name: "시뮬레이션 실행" }));
  await waitFor(() => expect(screen.getByRole("radio", { name: /현재안/ })).toBeChecked());

  expect(screen.getByText(/월세 0원 → 100만원/)).toBeInTheDocument();
});

it("최초안을 다시 고르면 결과 화면이 최초안 수치로 돌아간다", async () => {
  sessionStorage.clear();
  stubSimulate(OUTPUT_BASELINE, OUTPUT_REVISED);
  renderPage();

  await runSimulation();
  setRent("100");
  fireEvent.click(screen.getByRole("button", { name: "시뮬레이션 실행" }));
  await waitFor(() => expect(screen.getByRole("radio", { name: /현재안/ })).toBeChecked());

  fireEvent.click(screen.getByRole("radio", { name: /최초안/ }));

  // 결과 화면 고유 문구로 확인한다 — 비교 카드에도 같은 금액이 있다.
  await waitFor(() =>
    expect(screen.getByText(/자기자본 외 800만원을 상담에서 확인해야 해요/)).toBeInTheDocument(),
  );
  expect(JSON.parse(sessionStorage.getItem("localhostdaegu.consultation.v1")!).selected).toBe("baseline");
});

it("새로고침해도 저장된 선택안으로 결과를 복원한다", async () => {
  sessionStorage.clear();
  stubSimulate(OUTPUT_BASELINE);
  const { unmount } = renderPage();
  await runSimulation();
  unmount();

  renderPage();

  await waitFor(() => expect(screen.getByText("800만원")).toBeInTheDocument());
});
