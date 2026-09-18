"use client";

import type { FinanceInput } from "@/shared/api/types";
import { formatKrw } from "@/shared/format";
import type { PlanKind, PlanSnapshot } from "../lib/consultation-draft";

interface PlanComparisonProps {
  baseline: PlanSnapshot | null;
  current: PlanSnapshot | null;
  selected: PlanKind | null;
  onSelect: (kind: PlanKind) => void;
  changeReason: string;
  onChangeReason: (reason: string) => void;
}

const MONEY_LABELS: Partial<Record<keyof FinanceInput, string>> = {
  deposit: "보증금",
  key_money: "권리금",
  interior_cost: "인테리어 비용",
  equipment_cost: "설비 비용",
  monthly_rent: "월세",
  monthly_payroll: "월 인건비",
  monthly_insurance: "월 보험료",
  equity: "자기자본",
  desired_loan: "희망 대출금",
  expected_monthly_revenue: "예상 월매출",
};
const RATIO_LABELS: Partial<Record<keyof FinanceInput, string>> = {
  cost_ratio: "원가율",
  fee_ratio: "수수료율",
  loan_rate: "대출금리",
};

const percent = (ratio: number) => `${Math.round(ratio * 1000) / 10}%`;

/** 최초안 대비 바뀐 입력만 추린다 — 바뀌지 않은 조건을 변경점처럼 보여주지 않는다(§7-1). */
function changedConditions(baseline: FinanceInput, current: FinanceInput): string[] {
  const lines: string[] = [];
  for (const [key, label] of Object.entries(MONEY_LABELS) as [keyof FinanceInput, string][]) {
    if (baseline[key] !== current[key]) {
      lines.push(`${label} ${formatKrw(baseline[key])} → ${formatKrw(current[key])}`);
    }
  }
  for (const [key, label] of Object.entries(RATIO_LABELS) as [keyof FinanceInput, string][]) {
    if (baseline[key] !== current[key]) {
      lines.push(`${label} ${percent(baseline[key])} → ${percent(current[key])}`);
    }
  }
  return lines;
}

function PlanCard({
  kind,
  label,
  plan,
  checked,
  onSelect,
}: {
  kind: PlanKind;
  label: string;
  plan: PlanSnapshot;
  checked: boolean;
  onSelect: (kind: PlanKind) => void;
}) {
  return (
    <label
      className={`flex cursor-pointer flex-col gap-2 rounded-md border p-4 ${
        checked ? "border-[var(--accent)] bg-[var(--bg-raised)]" : "border-[var(--border)] bg-[var(--bg-surface)]"
      }`}
    >
      <span className="flex items-center gap-2 text-sm font-semibold text-[var(--text-primary)]">
        <input
          type="radio"
          name="consultation-plan"
          checked={checked}
          onChange={() => onSelect(kind)}
          className="accent-[var(--accent)]"
        />
        {label}
      </span>
      <span className="text-xs text-[var(--text-secondary)]">손익분기 매출 {formatKrw(plan.result.bep_revenue)}</span>
      <span className="text-xs text-[var(--text-secondary)]">총 준비자금 {formatKrw(plan.result.total_required_funds)}</span>
      <span className="text-xs text-[var(--text-secondary)]">자기자본 외 조달 필요</span>
      <span className="text-sm font-semibold tabular-nums text-[var(--text-primary)]">
        {formatKrw(plan.result.external_funding_need)}
      </span>
    </label>
  );
}

/** 최초안·현재안 비교와 선택(§5-3). 현재안이 없으면 비교할 대상이 없으므로 그리지 않는다. */
export function PlanComparison({
  baseline,
  current,
  selected,
  onSelect,
  changeReason,
  onChangeReason,
}: PlanComparisonProps) {
  if (baseline === null || current === null) return null;

  const changes = changedConditions(baseline.input, current.input);

  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-sm font-semibold text-[var(--text-primary)]">상담할 안 선택</h2>
      <div className="grid gap-4 sm:grid-cols-2">
        <PlanCard kind="baseline" label="최초안" plan={baseline} checked={selected === "baseline"} onSelect={onSelect} />
        <PlanCard kind="current" label="현재안" plan={current} checked={selected === "current"} onSelect={onSelect} />
      </div>
      <ul className="flex flex-col gap-1 text-xs text-[var(--text-secondary)]">
        {changes.length === 0 ? (
          <li>바뀐 조건 없음</li>
        ) : (
          changes.map((line) => <li key={line}>{line}</li>)
        )}
      </ul>

      <label className="flex flex-col gap-1.5 text-xs font-medium tracking-wide text-[var(--text-secondary)]">
        변경 이유 (상담자료에 그대로 실립니다)
        <textarea
          value={changeReason}
          onChange={(e) => onChangeReason(e.target.value)}
          rows={2}
          placeholder="예: 월세가 낮은 자리로 바꿨습니다"
          className="w-full rounded-md border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
        />
      </label>
    </section>
  );
}
