"use client";

import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ConsultationFinanceOutput, FinanceInput } from "@/shared/api/types";
import type { ConsultationProfile } from "../lib/consultation-draft";
import { formatKrw } from "@/shared/format";
import { FundingBar } from "./funding-bar";
import { MatchingCards } from "./matching-cards";
import { StressTable } from "./stress-table";

interface ResultViewProps {
  result: ConsultationFinanceOutput;
  /** 결론을 만든 제출값 — 미확보 희망대출을 결과와 함께 보여주기 위해 필요하다(§7-2). */
  input: FinanceInput;
  category?: string;
  /** 창업 단계 — 상담 후보 조회 조건. 미입력은 쿼리에서 생략된다(§5-2). */
  profile?: ConsultationProfile;
  /** 사용자 자치구 5자리 — 지역 한정 상품 필터. */
  districtCode?: string | null;
  /** 루프백(⑤) — "조건 바꿔보기" 링크. 시뮬레이터 폼으로 복귀. */
  backHref?: string;
  /** 상담 준비 CTA — 선택안을 실어 /analysis로 이동. 없으면 링크를 그리지 않는다. */
  analysisHref?: string;
  /** 비교 기준안(최초안)의 결과 — 있으면 주 지표 아래에 전후 차이를 표시한다. */
  compareTo?: ConsultationFinanceOutput;
}

/** 주 지표 — 진단(총 창업비용·월 고정비)이 아니라 상담 준비(자금 수요) 기준이다(전환계획 §3-2). */
const SUMMARY_ITEMS: { key: "bep_revenue" | "total_required_funds" | "external_funding_need"; label: string }[] = [
  { key: "bep_revenue", label: "손익분기 매출" },
  { key: "total_required_funds", label: "총 준비자금" },
  { key: "external_funding_need", label: "자기자본 외 조달 필요" },
];

/** 기준안 대비 차이 — 세 지표 모두 줄어드는 쪽이 부담이 작아지는 방향이다. 색과 함께 ▲▼·금액을 같이 쓴다. */
function Delta({ now, before }: { now: number; before: number }) {
  const diff = now - before;
  if (diff === 0) return <span className="text-xs text-[var(--text-secondary)]">최초안과 같음</span>;
  return (
    <span className={`text-xs tabular-nums ${diff < 0 ? "text-[var(--ok)]" : "text-[var(--danger)]"}`}>
      최초안 대비 {diff < 0 ? "▼" : "▲"} {formatKrw(Math.abs(diff))}
    </span>
  );
}

type ResultFiguresProps = Pick<ResultViewProps, "result" | "input" | "compareTo">;

/** 숫자와 그래프 — 요약 스트립 → 자금 구성 막대 → 3시나리오(손익분기선) → 금리 스트레스. */
export function ResultFigures({ result, input, compareTo }: ResultFiguresProps) {
  const chartMax = Math.max(result.bep_revenue, ...result.scenarios.map((s) => s.monthly_revenue), 1);
  const baseScenario = result.scenarios.find((s) => s.name === "기준");

  return (
    <div className="flex flex-col gap-6">
      <dl className="grid grid-cols-3 gap-4 rounded-md border border-[var(--border)] bg-[var(--bg-raised)] p-4">
        {SUMMARY_ITEMS.map(({ key, label }) => (
          <div key={key} className="flex flex-col gap-1">
            <dt className="text-xs text-[var(--text-secondary)]">{label}</dt>
            <dd className="text-xl font-semibold tracking-tight tabular-nums text-[var(--text-primary)]">
              {formatKrw(result[key])}
            </dd>
            {compareTo && <Delta now={result[key]} before={compareTo[key]} />}
          </div>
        ))}
      </dl>

      <FundingBar
        total={result.total_required_funds}
        equity={input.equity}
        desiredLoan={input.desired_loan}
        gap={result.funding_gap}
      />

      <div className="flex flex-col gap-2">
        {result.scenarios.length > 0 && (
          <p className="text-xs text-[var(--text-secondary)]" aria-hidden>
            시나리오별 월매출 · 점선은 손익분기 {formatKrw(result.bep_revenue)}
          </p>
        )}
        {result.scenarios.length > 0 && (
          <div className="relative grid h-24 grid-cols-3 items-end gap-4 border-b border-[var(--border)]" aria-hidden>
            {result.scenarios.map((scenario) => (
              <div
                key={scenario.name}
                className={`mx-auto w-1/2 rounded-t ${scenario.operating_profit < 0 ? "bg-[var(--danger)]" : "bg-[var(--accent)]"}`}
                style={{ height: `${(scenario.monthly_revenue / chartMax) * 100}%` }}
              />
            ))}
            <div
              className="absolute inset-x-0 border-t border-dashed border-[var(--text-secondary)]"
              style={{ bottom: `${(result.bep_revenue / chartMax) * 100}%` }}
            />
          </div>
        )}
        <div className="grid gap-4 sm:grid-cols-3">
          {result.scenarios.map((scenario) => {
            const isLoss = scenario.operating_profit < 0;
            return (
              <div
                key={scenario.name}
                className="flex flex-col gap-2 rounded-md border border-[var(--border)] bg-[var(--bg-surface)] p-4"
              >
                <h3 className="text-sm font-semibold text-[var(--text-primary)]">{scenario.name}</h3>
                <p className="text-xs text-[var(--text-secondary)]">월매출 {formatKrw(scenario.monthly_revenue)}</p>
                <p
                  className={`text-sm font-semibold tabular-nums ${isLoss ? "text-[var(--danger)]" : "text-[var(--text-primary)]"}`}
                >
                  영업이익 {formatKrw(scenario.operating_profit)}
                </p>
                <p className="text-xs text-[var(--text-secondary)]">
                  {scenario.payback_months != null
                    ? `회수 ${scenario.payback_months}개월`
                    : scenario.runway_months != null
                      ? `런웨이 ${scenario.runway_months}개월`
                      : "—"}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {input.desired_loan > 0 && baseScenario && (
        <StressTable
          stress={result.stress}
          baseFixed={result.monthly_fixed}
          baseProfit={baseScenario.operating_profit}
        />
      )}
    </div>
  );
}

type ResultNextStepsProps = Omit<ResultViewProps, "compareTo">;

/** 자금 구성 설명 → 상담 후보 → 루프백·상담 준비.
 *  MatchingCards는 react-query를 쓰므로, 페이지 전역 Provider 없이도 단독 렌더될 수 있도록 자체 QueryClient를 둔다. */
export function ResultNextSteps({
  result,
  input,
  category,
  profile,
  districtCode,
  backHref = "/simulate",
  analysisHref,
}: ResultNextStepsProps) {
  const [client] = useState(() => new QueryClient({ defaultOptions: { queries: { retry: false } } }));
  const needsFunding = result.external_funding_need > 0;

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-4">
        <p className="text-xs text-[var(--text-secondary)]">
          초기 투자비 {formatKrw(result.capex)} + 운영준비금 {result.reserve_months}개월치{" "}
          {formatKrw(result.operating_reserve)}
        </p>

        {needsFunding ? (
          <>
            <p className="text-sm font-semibold text-[var(--text-primary)]">
              자기자본 외 {formatKrw(result.external_funding_need)}을 상담에서 확인해야 해요
            </p>
            {input.desired_loan > 0 && (
              <p className="text-xs text-[var(--text-secondary)]">
                미확보 희망대출 {formatKrw(input.desired_loan)} — 아직 빌리지 않은 돈이에요. 반영 후 남는 부족액은{" "}
                {formatKrw(result.funding_gap)}입니다.
              </p>
            )}
            <QueryClientProvider client={client}>
              <MatchingCards
                externalFundingNeed={result.external_funding_need}
                category={category}
                businessRegistered={profile?.business_registered === "unknown" ? null : profile?.business_registered}
                businessAgeMonths={profile?.business_age_months}
                ownerAge={profile?.owner_age}
                districtCode={districtCode}
              />
            </QueryClientProvider>
          </>
        ) : (
          <p className="text-sm font-semibold text-[var(--text-primary)]">
            이 가정에서는 계산상 추가 조달 필요 없음 — 계획을 저장하고 필요할 때 상담하세요
          </p>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <a href={backHref} className="text-sm text-[var(--accent)] underline underline-offset-4">
          조건 바꿔보기 →
        </a>
        {analysisHref && (
          <a href={analysisHref} className="text-sm font-semibold text-[var(--accent)] underline underline-offset-4">
            이 안으로 상담 준비 →
          </a>
        )}
      </div>
    </div>
  );
}

/** 결론 화면 전체 — 숫자·그래프 다음에 상담 후보와 다음 행동이 온다. */
export function ResultView({ compareTo, ...props }: ResultViewProps) {
  return (
    <div className="flex flex-col gap-8">
      <ResultFigures result={props.result} input={props.input} compareTo={compareTo} />
      <ResultNextSteps {...props} />
    </div>
  );
}
