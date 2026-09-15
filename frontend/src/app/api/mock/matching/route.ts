import type { MatchingProduct } from "@/shared/api/types";

/** 백엔드 계약(GET /matching) 형태의 고정 응답 — 보증·은행·정책 각 1개.
 *  백엔드가 이미 필터·정렬(보증→은행→정책)해 반환하므로, mock은 요청 파라미터를 검증하지 않는다. */
const FIXED_PRODUCTS: MatchingProduct[] = [
  {
    product_id: "dgsinbo-1",
    provider: "대구신용보증재단",
    provider_type: "guarantee",
    product_name: "소상공인 창업자금 보증",
    target: "예비창업자·소상공인",
    region: "대구",
    business_age_min: 0,
    business_age_max: null,
    category: null,
    owner_age_max: null,
    loan_limit: 50_000_000,
    interest_rate: 3.5,
    guarantee_fee: 0.5,
    url: "https://www.dgsinbo.co.kr",
    source_url: "https://www.dgsinbo.co.kr",
  },
  {
    product_id: "imbank-1",
    provider: "iM뱅크",
    provider_type: "bank",
    product_name: "iM 소상공인 창업대출",
    target: "소상공인",
    region: "대구",
    business_age_min: 0,
    business_age_max: null,
    category: null,
    owner_age_max: null,
    loan_limit: 30_000_000,
    interest_rate: 4.8,
    guarantee_fee: 0,
    url: "https://www.imbank.co.kr",
    source_url: "https://www.imbank.co.kr",
  },
  {
    product_id: "youth-1",
    provider: "대구시",
    provider_type: "policy",
    product_name: "대구 청년 창업자금",
    target: "만 39세 이하 청년",
    region: "대구",
    business_age_min: 0,
    business_age_max: 12,
    category: null,
    owner_age_max: 39,
    loan_limit: 20_000_000,
    interest_rate: 2.0,
    guarantee_fee: 0,
    url: "https://www.daegu.go.kr",
    source_url: "https://www.daegu.go.kr",
  },
];

export async function GET() {
  return Response.json(FIXED_PRODUCTS);
}
