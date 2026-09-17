import { afterEach, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MatchingCards } from "./matching-cards";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

it("빈 배열 응답이면 '조건에 맞는 상품을 찾지 못했어요' 문구를 보여준다", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify([]), { status: 200 })),
  );

  renderWithClient(<MatchingCards fundingGap={20_000_000} category="cafe" />);

  await waitFor(() => expect(screen.getByText(/조건에 맞는 상품을 찾지 못했어요/)).toBeInTheDocument());
});

it("category 미지정이어도 요청 URL에 category 파라미터가 항상 포함된다 (백엔드 필수 파라미터)", async () => {
  const fetchMock = vi.fn(async () => new Response(JSON.stringify([]), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);

  renderWithClient(<MatchingCards fundingGap={20_000_000} />);

  await waitFor(() => expect(fetchMock).toHaveBeenCalled());
  const requestedUrl = String(fetchMock.mock.calls[0][0]);
  expect(requestedUrl).toContain("category=");
});

function product(overrides: Record<string, unknown>) {
  return {
    product_id: "dgsinbo-1",
    provider: "대구신용보증재단",
    provider_type: "guarantee",
    product_name: "대구형 창업·성장 플러스 특별보증",
    target: "",
    region: "대구광역시",
    business_age_min: 0,
    business_age_max: null,
    category: null,
    owner_age_max: null,
    loan_limit: 100_000_000,
    interest_rate: 2.5,
    guarantee_fee: 0.9,
    url: "https://example.com",
    source_url: "https://example.com",
    ...overrides,
  };
}

it("금리가 null이면 '은행별 상이'로 표시하고 카드 어디에도 'null'이 찍히지 않는다", async () => {
  const body = [product({ interest_rate: null, guarantee_fee: null, loan_limit: null })];
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(body), { status: 200 })));

  const { container } = renderWithClient(<MatchingCards fundingGap={20_000_000} category="cafe" />);

  await waitFor(() => expect(screen.getByText(/은행별 상이/)).toBeInTheDocument());
  expect(screen.getByText(/한도 미정/)).toBeInTheDocument();
  expect(container.textContent).not.toMatch(/null/);
});

it("금리 수치가 있으면 '금리 N%'로 표시한다", async () => {
  const body = [product({ interest_rate: 2.5 })];
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(body), { status: 200 })));

  renderWithClient(<MatchingCards fundingGap={20_000_000} category="cafe" />);

  await waitFor(() => expect(screen.getByText(/금리 2\.5%/)).toBeInTheDocument());
});
