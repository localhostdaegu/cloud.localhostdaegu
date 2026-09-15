import { afterEach, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MapPage } from "./map-page";

const replace = vi.fn();

// C1 회귀 방지: district만 있고 industry가 없는 URL(채팅 랜딩 → B유형 진입 상태)을 고정해,
// region 선택이 router.replace에 어떤 쿼리를 넘기는지를 검증한다.
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn() }),
  useSearchParams: () => new URLSearchParams("district=27110"),
}));

// maplibre-gl 렌더링은 jsdom 대상이 아니므로 onSelectRegion 트리거만 남기고 걷어낸다.
vi.mock("./map-view", () => ({
  MapView: ({ onSelectRegion }: { onSelectRegion: (code: string) => void }) => (
    <button type="button" onClick={() => onSelectRegion("1168051500")}>
      select-region
    </button>
  ),
}));

afterEach(() => {
  vi.restoreAllMocks();
});

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

it("C1: district만 있는 상태(industry 없음)에서 region을 선택해도 router.replace 쿼리에 industry가 주입되지 않는다", () => {
  renderWithClient(<MapPage />);

  screen.getByRole("button", { name: "select-region" }).click();

  expect(replace).toHaveBeenCalledTimes(1);
  const [url] = replace.mock.calls[0] as [string];
  expect(url).not.toMatch(/industry=/);
  expect(url).toMatch(/district=27110/);
  expect(url).toMatch(/region=1168051500/);
});
