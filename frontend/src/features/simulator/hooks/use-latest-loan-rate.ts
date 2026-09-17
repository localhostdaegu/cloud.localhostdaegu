import { useQuery } from "@tanstack/react-query";
import { fetchLatestRate } from "../api";

/** 소상공인 차주에 가장 가까운 ECOS 계열 — 예금은행 중소기업대출 가중평균 금리(신규취급액). */
const LOAN_RATE_TYPE = "loan_sme";

/** 최신 대출금리(비율). 로딩 중·실패 시 undefined — 호출부가 고정 기본값으로 폴백하고 폼을 막지 않는다. */
export function useLatestLoanRate(): number | undefined {
  const { data } = useQuery({
    queryKey: ["rates", "latest", LOAN_RATE_TYPE],
    queryFn: () => fetchLatestRate(LOAN_RATE_TYPE),
  });
  return data?.value_ratio;
}
