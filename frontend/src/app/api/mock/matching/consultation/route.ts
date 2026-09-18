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
  {
    product: {
      product_id: "dgsinbo-3",
      provider: "대구신용보증재단",
      provider_type: "guarantee",
      product_name: "유망 예비창업자 사전보증",
      target: "보증지원 예정 통지일로부터 6개월 이내 사업자등록증을 제출하고 창업할 예정인 예비창업자",
      region: "대구",
      business_age_min: 0,
      business_age_max: null,
      category: null,
      owner_age_max: null,
      loan_limit: 50_000_000,
      interest_rate: null,
      guarantee_fee: 0.8,
      url: "https://www.dgsinbo.or.kr/page/10039/10043.tc?pageDtlOrdrNo=1&importUrl=/guaranteegoods/detail.tc&gdsNo=5",
      source_url: "https://www.dgsinbo.or.kr/page/10039/10043.tc?pageDtlOrdrNo=1&importUrl=/guaranteegoods/detail.tc&gdsNo=5",
    },
    metadata: {
      bank_connection: "unverified",
      bank_connection_source_url:
        "https://www.dgsinbo.or.kr/page/10039/10043.tc?pageDtlOrdrNo=1&importUrl=/guaranteegoods/detail.tc&gdsNo=5",
      business_registration_required: false,
      prerequisites: [
        "창업교육 10시간 이상 이수 또는 컨설팅 2회·10시간 이상 이수 (최근 1년 이내)",
        "또는 최근 2년 이내 등록된 지식재산권 사업화 예정",
        "대표자 개인신용평점 NICE 755점 또는 KCB 670점 이상",
        "보증지원 예정 통지일로부터 6개월 이내 사업자등록증 제출",
      ],
      application_steps: [],
      documents: [],
      verified_at: "2026-09-18",
    },
    status: "prerequisites_needed",
    reason: "공식 원문에 취급 은행이 명시되지 않음(시중은행 등으로만 표기) — 해당 기관에 직접 확인 필요",
    unresolved_conditions: [
      "준비서류는 공식 안내에서 확인 필요",
      "신청 경로는 공식 안내에서 확인 필요",
      "적용 금리는 은행·기관 상담에서 확인",
    ],
  },
];

export async function GET() {
  return Response.json(FIXED_CANDIDATES);
}
