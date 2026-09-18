"use client";

import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ConsultationFinanceOutput, FinanceInput } from "@/shared/api/types";
import { formatKrw } from "@/shared/format";
import { MatchingCards } from "./matching-cards";

interface ResultViewProps {
  result: ConsultationFinanceOutput;
  /** 결론을 만든 제출값 — 미확보 희망대출을 결과와 함께 보여주기 위해 필요하다(§7-2). */
  input: FinanceInput;
  category?: string;
  /** 루프백(⑤) — "조건 바꿔보기" 링크. 시뮬레이터 폼으로 복귀. */
  backHref?: string;
  /** 상담 준비 CTA — 선택안을 실어 /analysis로 이동. 없으면 링크를 그리지 않는다. */
  analysisHref?: string;
}

/** 주 지표 — 진단(총 창업비용·월 고정비)이 아니라 상담 준비(자금 수요) 기준이다(전환계획 §3-2). */
const SUMMARY_ITEMS: { key: "bep_revenue" | "total_required_funds" | "external_funding_need"; label: string }[] = [
  { key: "bep_revenue", label: "손익분기 매출" },
  { key: "total_required_funds", label: "총 준비자금" },
  { key: "external_funding_need", label: "자기자본 외 조달 필요" },
];

/** 결론 화면 — 요약 스트립 → 3시나리오 → 자금 구성 → 상담 후보 → 루프백·상담 준비.
 *  MatchingCards는 react-query를 쓰므로, 페이지 전역 Provider 없이도 단독 렌더될 수 있도록 자체 QueryClient를 둔다. */
export function ResultView({ result, input, category, backHref = "/simulate", analysisHref }: ResultViewProps) {
  const [client] = useState(() => new QueryClient({ defaultOptions: { queries: { retry: false } } }));
  const needsFunding = result.external_funding_need > 0;

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
            {/* 백엔드 파라미터 이름은 funding_gap 이지만, 상담 주제가 되는 금액은 조달 필요액이다.
                이름 통일은 T4 범위 — 여기서는 보내는 값만 맞춘다. */}
            <QueryClientProvider client={client}>
              <MatchingCards fundingGap={result.external_funding_need} category={category} />
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
