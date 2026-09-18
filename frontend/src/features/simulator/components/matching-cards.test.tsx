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

const CANDIDATE = {
  product: {
    product_id: "imbank-1",
    provider: "iM뱅크",
    provider_type: "bank",
    product_name: "소상공인시장진흥공단 정책자금 (운전자금)",
    loan_limit: 100_000_000,
    interest_rate: null,
    url: "https://www.imbank.co.kr/example",
  },
  metadata: {
    bank_connection: "direct",
    bank_connection_source_url: "https://www.imbank.co.kr/example",
    business_registration_required: null,
    prerequisites: ["소진공 정책자금 지원대상 확인서 발급"],
    application_steps: ["은행 영업점에 확인서 제출"],
    documents: [],
    verified_at: "2026-09-18",
  },
  status: "prerequisites_needed",
  reason: "iM뱅크 직접 취급으로 확인됨",
  unresolved_conditions: ["준비서류는 공식 안내에서 확인 필요"],
};

const stub = (body: unknown) =>
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(body), { status: 200 })));

it("후보가 없으면 일반 상담 경로와 질문을 남긴다 — 조건만 바꾸라고 하지 않는다", async () => {
  stub([]);

  renderWithClient(<MatchingCards externalFundingNeed={20_000_000} category="cafe" />);

  await waitFor(() =>
    expect(screen.getByText(/iM뱅크 취급이 확인된 상품을 찾지 못했어요/)).toBeInTheDocument(),
  );
  expect(screen.getByRole("link", { name: /iM뱅크 공식 상담 안내/ })).toBeInTheDocument();
  expect(screen.getByText(/현재 창업 단계에서 상담 가능한 자금/)).toBeInTheDocument();
});

it("후보의 연결 근거·선행 절차·미확인 조건을 함께 보여준다", async () => {
  stub([CANDIDATE]);

  renderWithClient(<MatchingCards externalFundingNeed={20_000_000} category="cafe" />);

  await waitFor(() => expect(screen.getByText(/소상공인시장진흥공단 정책자금/)).toBeInTheDocument());
  expect(screen.getByText("iM뱅크 직접 취급으로 확인됨")).toBeInTheDocument();
  expect(screen.getByText(/소진공 정책자금 지원대상 확인서 발급/)).toBeInTheDocument();
  expect(screen.getByText(/은행 영업점에 확인서 제출/)).toBeInTheDocument();
  expect(screen.getByText(/준비서류는 공식 안내에서 확인 필요/)).toBeInTheDocument();
  expect(screen.getByText(/2026-09-18 확인/)).toBeInTheDocument();
});

it("선행 절차가 남은 후보임을 표시한다 — 신청 완료처럼 보이지 않게", async () => {
  stub([CANDIDATE]);

  renderWithClient(<MatchingCards externalFundingNeed={20_000_000} category="cafe" />);

  await waitFor(() => expect(screen.getByText("선행 절차 필요")).toBeInTheDocument());
});

it("상담 정보를 쿼리에 실어 보내고, 미입력 값은 생략한다", async () => {
  const fetchMock = vi.fn(async () => new Response("[]", { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);

  renderWithClient(
    <MatchingCards externalFundingNeed={2_000_000} category="cafe" businessRegistered={false} ownerAge={null} />,
  );

  await waitFor(() => expect(fetchMock).toHaveBeenCalled());
  const url = String(fetchMock.mock.calls[0][0]);
  expect(url).toContain("/matching/consultation?");
  expect(url).toContain("external_funding_need=2000000");
  expect(url).toContain("business_registered=false");
  expect(url).not.toContain("owner_age");
});

it("조회 실패는 계산 실패와 구분해 알린다", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => new Response("{}", { status: 500 })));

  renderWithClient(<MatchingCards externalFundingNeed={20_000_000} category="cafe" />);

  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/상담 후보를 불러오지 못했습니다/));
});

const REFERENCE = {
  ...CANDIDATE,
  product: { ...CANDIDATE.product, product_id: "dgsinbo-3", provider: "대구신용보증재단", provider_type: "guarantee", product_name: "유망 예비창업자 사전보증" },
  metadata: { ...CANDIDATE.metadata, bank_connection: "unverified" },
  reason: "iM뱅크 취급 여부가 공식 원문에서 확인되지 않음 — 해당 기관에 직접 확인 필요",
};

it("참고자료까지 함께 요청한다 — 근거 미확인 상품도 사용자에게 보인다", async () => {
  const fetchMock = vi.fn(async () => new Response("[]", { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);

  renderWithClient(<MatchingCards externalFundingNeed={2_000_000} category="cafe" />);

  await waitFor(() => expect(fetchMock).toHaveBeenCalled());
  expect(String(fetchMock.mock.calls[0][0])).toContain("include_unverified=true");
});

it("iM뱅크 상담 후보와 관련 기관 참고자료를 나눠 보여준다", async () => {
  stub([CANDIDATE, REFERENCE]);

  renderWithClient(<MatchingCards externalFundingNeed={2_000_000} category="cafe" />);

  await waitFor(() => expect(screen.getByText(/iM뱅크에서 상담할 상품/)).toBeInTheDocument());
  expect(screen.getByText(/차선 후보/)).toBeInTheDocument();
  expect(screen.getByText("유망 예비창업자 사전보증")).toBeInTheDocument();
});

it("참고자료만 있으면 iM뱅크 후보가 없다는 것도 함께 알린다", async () => {
  stub([REFERENCE]);

  renderWithClient(<MatchingCards externalFundingNeed={2_000_000} category="cafe" />);

  await waitFor(() => expect(screen.getByText(/차선 후보/)).toBeInTheDocument());
  expect(screen.getByText(/iM뱅크 취급이 확인된 상품은 없어요/)).toBeInTheDocument();
  expect(screen.queryByText(/iM뱅크에서 상담할 상품/)).not.toBeInTheDocument();
});

it("참고자료는 상담 후보가 아님을 카드에 밝힌다", async () => {
  stub([REFERENCE]);

  renderWithClient(<MatchingCards externalFundingNeed={2_000_000} category="cafe" />);

  await waitFor(() => expect(screen.getByText("근거 미확인")).toBeInTheDocument());
});
