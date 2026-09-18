import type { ConsultationCandidate } from "@/shared/api/types";

/** 백엔드 계약(GET /matching/consultation) 형태의 고정 응답.
 *  값은 data/manual/imbank_products.json 의 실제 대조 결과와 같다
 *  (docs/research/finance-products/2026-09-18-consultation-sources.md). */
const FIXED_CANDIDATES: ConsultationCandidate[] = [
  {
    product: {
      product_id: "imbank-1",
      provider: "iM뱅크",
      provider_type: "bank",
      product_name: "소상공인시장진흥공단 정책자금 (운전자금)",
      target: "소상공인시장진흥공단에서 자금 추천을 받은 개인기업·법인",
      region: "전국 (iM뱅크 영업점 취급)",
      business_age_min: 0,
      business_age_max: null,
      category: null,
      owner_age_max: null,
      loan_limit: 100_000_000,
      interest_rate: null,
      guarantee_fee: null,
      url: "https://www.imbank.co.kr/cms/fnm/loan/product/giup/01/sda_41216/1221451_5612.html",
      source_url: "https://www.imbank.co.kr/cms/fnm/loan/product/giup/01/sda_41216/1221451_5612.html",
    },
    metadata: {
      bank_connection: "direct",
      bank_connection_source_url:
        "https://www.imbank.co.kr/cms/fnm/loan/product/giup/01/sda_41216/1221451_5612.html",
      business_registration_required: null,
      prerequisites: [
        "소상공인시장진흥공단(지역센터 포함)에 신청 후 '정책자금 지원대상 확인서' 발급",
        "신용보증기관 연계 시 보증서 발급",
      ],
      application_steps: ["은행 영업점에 정책자금 지원대상 확인서 제출"],
      documents: [],
      verified_at: "2026-09-18",
    },
    status: "needs_check",
    reason: "iM뱅크 직접 취급으로 확인됨",
    unresolved_conditions: [
      "사업자등록 필요 여부가 공식 안내에서 확인되지 않음",
      "준비서류는 공식 안내에서 확인 필요",
      "적용 금리는 은행·기관 상담에서 확인",
    ],
  },
];

export async function GET() {
  return Response.json(FIXED_CANDIDATES);
}
