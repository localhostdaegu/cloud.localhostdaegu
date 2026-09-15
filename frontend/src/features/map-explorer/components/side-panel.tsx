"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/client";
import { GradeBadge } from "@/shared/ui/grade-badge";
import { industryLabel } from "@/shared/industries";
import { fetchIndustryRiskRanking, fetchRegionSummary, fetchRiskScore } from "../api";
import { RiskCard, RiskGradeBadge } from "./risk-card";

interface SidePanelProps {
  regionCode: string | null;
  industry: string;
  /** URL에 industry 파라미터가 실제로 있었는지. map-state.parseMapState는 미지정 시 항상 기본값(cafe)으로
   *  채워 "없음"을 표현할 수 없으므로, 원본 파라미터를 별도로 받아 B유형(업종 랭킹) 여부를 가른다. */
  industryParam: string | null;
  onSelectIndustry: (industryId: string) => void;
}

function SkeletonRows() {
  return (
    <div className="flex flex-col gap-4" aria-hidden>
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="flex flex-col gap-2">
          <div className="h-3 w-14 rounded bg-[var(--bg-raised)]" />
          <div className="h-4 w-28 rounded bg-[var(--bg-raised)]" />
        </div>
      ))}
    </div>
  );
}

export function SidePanel({ regionCode, industry, industryParam, onSelectIndustry }: SidePanelProps) {
  const isRanking = !!regionCode && industryParam === null;

  const summary = useQuery({
    queryKey: ["region-summary", regionCode, industry],
    queryFn: () => fetchRegionSummary(regionCode!, industry),
    enabled: !!regionCode && !isRanking,
  });

  // 404(RISK_NOT_FOUND)는 정상 케이스(이 조합의 위험도 데이터 없음) — region summary와 달리 에러 배너로 취급하지 않는다.
  const risk = useQuery({
    queryKey: ["risk-score", regionCode, industry],
    queryFn: () => fetchRiskScore(regionCode!, industry),
    enabled: !!regionCode && !isRanking,
  });
  const riskNotFound = risk.isError && risk.error instanceof ApiError && risk.error.code === "RISK_NOT_FOUND";

  const ranking = useQuery({
    queryKey: ["risk-ranking", regionCode],
    queryFn: () => fetchIndustryRiskRanking(regionCode!),
    enabled: isRanking,
  });

  const label = industryLabel(industry);

  return (
    <aside className="flex w-80 shrink-0 flex-col overflow-y-auto border-l border-[var(--border)] bg-[var(--bg-surface)] p-5">
      {!regionCode && (
        <div className="my-auto flex flex-col items-center gap-2 px-4 text-center">
          <span className="text-sm font-medium text-[var(--text-primary)]">선택된 행정동 없음</span>
          <span className="text-sm leading-relaxed text-[var(--text-secondary)]">
            지도에서 행정동을 클릭하면 {label} 지표와 신호가 여기에 표시됩니다.
          </span>
        </div>
      )}

      {isRanking && ranking.isPending && (
        <div role="status" aria-label="불러오는 중">
          <div className="mb-5 h-5 w-24 rounded bg-[var(--bg-raised)]" aria-hidden />
          <SkeletonRows />
        </div>
      )}

      {isRanking && ranking.isError && (
        <div role="alert" className="my-auto flex flex-col items-center gap-2 px-4 text-center">
          <span className="text-sm font-medium text-[var(--danger)]">데이터 없음</span>
          <span className="text-sm leading-relaxed text-[var(--text-secondary)]">
            <span className="tabular-nums">{regionCode}</span> 행정동의 업종별 위험도를 불러오지 못했습니다.
          </span>
        </div>
      )}

      {isRanking && ranking.data && (
        <>
          <header className="flex flex-col gap-0.5">
            <h2 className="text-lg font-semibold tracking-tight text-[var(--text-primary)]">업종별 위험도</h2>
            <p className="text-xs text-[var(--text-secondary)]">
              <span className="tabular-nums">{regionCode}</span> · 업종을 선택하면 상세 진단이 표시됩니다.
            </p>
          </header>

          {ranking.data.length === 0 ? (
            <p className="mt-5 text-sm leading-relaxed text-[var(--text-secondary)]">
              이 행정동의 위험도 데이터가 아직 없어요.
            </p>
          ) : (
            <ul className="mt-5 flex flex-col divide-y divide-[var(--border)] border-y border-[var(--border)]">
              {ranking.data.map((row) => (
                <li key={row.industry_id}>
                  <button
                    type="button"
                    onClick={() => onSelectIndustry(row.industry_id)}
                    className="flex w-full items-center justify-between gap-3 py-3 text-left transition-colors hover:bg-[var(--bg-raised)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                  >
                    <div className="flex min-w-0 flex-col gap-0.5">
                      <span className="text-sm font-medium text-[var(--text-primary)]">
                        {industryLabel(row.industry_id)}
                      </span>
                      <span className="text-xs tabular-nums text-[var(--text-secondary)]">{row.score}점</span>
                    </div>
                    <RiskGradeBadge grade={row.grade} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      {!isRanking && regionCode && summary.isPending && (
        <div role="status" aria-label="불러오는 중">
          <div className="mb-5 h-5 w-24 rounded bg-[var(--bg-raised)]" aria-hidden />
          <SkeletonRows />
        </div>
      )}

      {!isRanking && regionCode && summary.isError && (
        <div role="alert" className="my-auto flex flex-col items-center gap-2 px-4 text-center">
          <span className="text-sm font-medium text-[var(--danger)]">데이터 없음</span>
          <span className="text-sm leading-relaxed text-[var(--text-secondary)]">
            <span className="tabular-nums">{regionCode}</span> 행정동의 {label} 지표를 불러오지 못했습니다.
          </span>
        </div>
      )}

      {!isRanking && regionCode && summary.data && (
        <>
          <header className="flex flex-col gap-0.5">
            <h2 className="text-lg font-semibold tracking-tight text-[var(--text-primary)]">
              {summary.data.name}
            </h2>
            <p className="text-xs text-[var(--text-secondary)]">
              <span className="tabular-nums">{summary.data.region_code}</span> · {label}
            </p>
          </header>

          <div className="mt-5">
            {risk.data && <RiskCard score={risk.data.score} grade={risk.data.grade} components={risk.data.components} />}
            {riskNotFound && (
              <p className="mb-5 text-sm leading-relaxed text-[var(--text-secondary)]">
                이 조합의 진단 데이터가 아직 없어요
              </p>
            )}
          </div>

          <ul className="flex flex-col divide-y divide-[var(--border)] border-y border-[var(--border)]">
            {summary.data.cards.map((card) => (
              <li key={card.label} className="flex items-start justify-between gap-3 py-3">
                <div className="flex min-w-0 flex-col gap-0.5">
                  <span className="text-xs text-[var(--text-secondary)]">{card.label}</span>
                  <span className="text-sm leading-snug tabular-nums text-[var(--text-primary)]">
                    {card.value}
                  </span>
                </div>
                <GradeBadge grade={card.grade} />
              </li>
            ))}
          </ul>

          <Link
            href={`/analysis?region=${regionCode}&industry=${industry}`}
            className="mt-6 rounded-md bg-[var(--accent)] px-3 py-2.5 text-center text-sm font-semibold text-[var(--accent-fg)] transition-opacity hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] active:translate-y-px"
          >
            AI 분석 →
          </Link>
        </>
      )}
    </aside>
  );
}
