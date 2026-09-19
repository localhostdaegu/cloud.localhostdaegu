import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ChatLanding } from "./chat-landing";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

const result = {
  intent_type: "A", district_code: "27110", industry_id: "cafe",
  budget_krw: 50000000, missing: [], region_name: "중구",
};

function mount() {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  render(<QueryClientProvider client={client}><ChatLanding /></QueryClientProvider>);
  return userEvent.setup();
}

beforeEach(() => push.mockClear());
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it("예시를 입력하고 포커스를 돌려주어 Tab으로 제출할 수 있다", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(result))));
  const user = mount();
  expect(screen.getByRole("textbox")).toHaveAccessibleName("생각 중인 동네나 업종을 알려주세요");
  await user.click(screen.getByRole("button", { name: "서문시장 근처 카페, 예산 5천" }));
  expect(screen.getByRole("textbox")).toHaveValue("서문시장 근처 카페, 예산 5천");
  expect(screen.getByRole("textbox")).toHaveFocus();
  await user.tab();
  expect(screen.getByRole("button", { name: "찾아보기" })).toHaveFocus();
  await user.keyboard("{Enter}");
  await waitFor(() => expect(push).toHaveBeenCalledWith("/map?district=27110&industry=cafe&budget=50000000"));
});

it("빈 입력은 제출하지 않고 검색 중 중복 제출도 차단한다", async () => {
  const fetchMock = vi.fn(() => new Promise<Response>(() => {}));
  vi.stubGlobal("fetch", fetchMock);
  const user = mount();
  const input = screen.getByRole("textbox");
  expect(screen.getByRole("button", { name: "찾아보기" })).toBeDisabled();
  await user.type(input, "   ");
  fireEvent.submit(input.closest("form")!);
  expect(fetchMock).not.toHaveBeenCalled();
  await user.type(input, "카페   ");
  await user.click(screen.getByRole("button", { name: "찾아보기" }));
  expect(await screen.findByRole("button", { name: "찾는 중…" })).toBeDisabled();
  fireEvent.submit(input.closest("form")!);
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/intent"), expect.objectContaining({ body: '{"text":"카페"}' }));
});

it.each([
  ["카페", "/map?district=27110&industry=cafe&budget=50000000"],
  ["잘 몰라요 — 업종별 위험도 먼저 보기", "/map?district=27110&budget=50000000"],
])("업종이 없으면 선택을 기다리고 '%s' 경로로 이동한다", async (choice, url) => {
  const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ...result, industry_id: null, missing: ["industry"] })));
  vi.stubGlobal("fetch", fetchMock);
  const user = mount();
  await user.type(screen.getByRole("textbox"), "중구 예산 5천");
  await user.click(screen.getByRole("button", { name: "찾아보기" }));
  await screen.findByText("어떤 업종을 찾으세요?");
  expect(push).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: choice, exact: true }));
  expect(push).toHaveBeenCalledWith(url);
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it("동네를 못 알아들으면 말없이 지도로 보내지 않고 구·군을 되묻는다", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ ...result, district_code: null, industry_id: null, budget_krw: 30_000_000, missing: ["region", "industry"] }))));
  const user = mount();
  await user.type(screen.getByRole("textbox"), "예산 3천으로 뭐 하지?");
  await user.click(screen.getByRole("button", { name: "찾아보기" }));

  expect(await screen.findByText(/말씀하신 곳을 찾지 못했어요/)).toBeInTheDocument();
  expect(push).not.toHaveBeenCalled();

  // 구·군을 고르면 업종 되물음으로 이어지고, 말한 예산은 끝까지 따라간다.
  await user.click(screen.getByRole("button", { name: "수성구" }));
  await user.click(await screen.findByRole("button", { name: "편의점 (담배소매인 기준)" })); // 등록 업종 11종이 모두 칩에 있다 — 편의점 라벨은 담배소매인 대용임을 밝힌다
  expect(push).toHaveBeenCalledWith("/map?district=27260&industry=convenience_store&budget=30000000");
});

it("동네를 아직 못 정했으면 대구 전체 지도로 갈 수 있다", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ ...result, district_code: null, industry_id: null, budget_krw: null, missing: ["region", "industry"] }))));
  const user = mount();
  await user.type(screen.getByRole("textbox"), "뭐 하지?");
  await user.click(screen.getByRole("button", { name: "찾아보기" }));
  await user.click(await screen.findByRole("button", { name: /아직 몰라요/ }));
  expect(push).toHaveBeenCalledWith("/map");
});

it("오류를 표시하고 입력을 보존해 재시도할 수 있다", async () => {
  vi.stubGlobal("fetch", vi.fn()
    .mockResolvedValueOnce(new Response("{}", { status: 500 }))
    .mockResolvedValueOnce(new Response(JSON.stringify(result))));
  const user = mount();
  await user.type(screen.getByRole("textbox"), "중구 카페");
  await user.click(screen.getByRole("button", { name: "찾아보기" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("다시 시도");
  expect(screen.getByRole("textbox")).toHaveValue("중구 카페");
  await user.click(screen.getByRole("button", { name: "찾아보기" }));
  await waitFor(() => expect(push).toHaveBeenCalledWith("/map?district=27110&industry=cafe&budget=50000000"));
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

it("세 단계 안내가 상담 준비까지 이어진다 — 지표 확인에서 끝나지 않는다", () => {
  mount();

  const steps = screen.getByRole("list", { name: /세 단계/ });
  expect(steps).toHaveTextContent(/자금/);
  expect(steps).toHaveTextContent(/상담/);
});
