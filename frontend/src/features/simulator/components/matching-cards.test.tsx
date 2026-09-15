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
