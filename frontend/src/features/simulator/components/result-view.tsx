"use client";

import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { FinanceOutput } from "@/shared/api/types";
import { formatKrw } from "@/shared/format";
import { MatchingCards } from "./matching-cards";

interface ResultViewProps {
  result: FinanceOutput;
  category?: string;
  /** 루프백(⑤) — "조건 바꿔보기" 링크. 시뮬레이터 폼으로 복귀. */
  backHref?: string;
}

const SUMMARY_ITEMS: { key: "capex" | "monthly_fixed" | "bep_revenue"; label: string }[] = [
  { key: "capex", label: "총 창업비용" },
  { key: "monthly_fixed", label: "월 고정비" },
  { key: "bep_revenue", label: "손익분기 매출" },
];

/** 결론 화면(기획서 §4 ④) — 요약 스트립 → 3시나리오 카드 → Funding Gap 헤드라인 → 매칭 상품 → 루프백 링크.
 *  MatchingCards는 react-query를 쓰므로, 페이지 전역 Provider 없이도 단독 렌더될 수 있도록 자체 QueryClient를 둔다. */
export function ResultView({ result, category, backHref = "/simulate" }: ResultViewProps) {
  const [client] = useState(() => new QueryClient({ defaultOptions: { queries: { retry: false } } }));

  return (
    <div className="flex flex-col gap-8">
      <dl className="grid grid-cols-3 gap-4 rounded-md border border-[var(--border)] bg-[var(--bg-raised)] p-4">
        {SUMMARY_ITEMS.map(({ key, label }) => (
          <div key={key} className="flex flex-col gap-1">
            <dt className="text-xs text-[var(--text-secondary)]">{label}</dt>
            <dd className="text-sm font-semibold tabular-nums text-[var(--text-primary)]">{formatKrw(result[key])}</dd>
          </div>
        ))}
      </dl>

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

      <div className="flex flex-col gap-4">
        {result.funding_gap === 0 ? (
          <p className="text-sm font-semibold text-[var(--text-primary)]">자기자본으로 충분해요</p>
        ) : (
          <>
            <p className="text-sm font-semibold text-[var(--text-primary)]">
              부족한 {formatKrw(result.funding_gap)}, 이렇게 메울 수 있어요
            </p>
            <QueryClientProvider client={client}>
              <MatchingCards fundingGap={result.funding_gap} category={category} />
            </QueryClientProvider>
          </>
        )}
      </div>

      <a href={backHref} className="self-start text-sm text-[var(--accent)] underline underline-offset-4">
        조건 바꿔보기 →
      </a>
    </div>
  );
}
