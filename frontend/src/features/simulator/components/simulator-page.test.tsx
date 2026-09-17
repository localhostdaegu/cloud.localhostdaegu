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
