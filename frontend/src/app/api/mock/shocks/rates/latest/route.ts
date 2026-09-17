import type { LatestRate } from "@/shared/api/types";

/** 백엔드 계약(GET /shocks/rates/latest) 형태의 고정 응답.
 *  값은 개발 DB의 ECOS 121Y006 중소기업대출(loan_sme) 2026-07 적재값 4.22%에 맞춘 화면 개발용 fixture. */
const FIXED_RATE: LatestRate = {
  rate_type: "loan_sme",
  period: "202607",
  value_percent: 4.22,
  value_ratio: 0.0422,
};

export async function GET() {
  return Response.json(FIXED_RATE);
}
