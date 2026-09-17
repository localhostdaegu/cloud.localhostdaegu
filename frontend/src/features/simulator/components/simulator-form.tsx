"use client";

import { useState } from "react";
import type { FinanceInput } from "@/shared/api/types";
import { manwonToWon, wonToManwon } from "../lib/money";

interface SimulatorFormProps {
  defaults: FinanceInput;
  onSubmit: (payload: FinanceInput) => void;
  submitting?: boolean;
}

const FIELD =
  "w-full rounded-md border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]";

/** 원 단위 int 필드를 만원 단위로 표시·입력받는다. 내부 state는 항상 원 단위. */
function MoneyField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (won: number) => void;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-xs font-medium tracking-wide text-[var(--text-secondary)]">
      {label}
      <div className="flex items-center gap-2">
        <input
          type="number"
          inputMode="numeric"
          value={wonToManwon(value)}
          onChange={(e) => onChange(manwonToWon(Number(e.target.value) || 0))}
          className={`${FIELD} tabular-nums`}
        />
        <span className="shrink-0 text-xs text-[var(--text-secondary)]">만원</span>
      </div>
    </label>
  );
}

function RatioField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (ratio: number) => void;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-xs font-medium tracking-wide text-[var(--text-secondary)]">
      {label}
      <div className="flex items-center gap-2">
        <input
          type="number"
          step="0.1"
          inputMode="decimal"
          value={Math.round(value * 1000) / 10}
          onChange={(e) => onChange((Number(e.target.value) || 0) / 100)}
          className={`${FIELD} tabular-nums`}
        />
        <span className="shrink-0 text-xs text-[var(--text-secondary)]">%</span>
      </div>
    </label>
  );
}

/** 프리필 확인 섹션("확인해주세요") + 상세 입력 섹션("입력해주세요") 두 개로 구성된 재무 시뮬레이션 폼. */
export function SimulatorForm({ defaults, onSubmit, submitting }: SimulatorFormProps) {
  const [values, setValues] = useState<FinanceInput>(defaults);
  // 대출금리 기본값은 최신 금리 조회 후 늦게 바뀐다 — 사용자가 아직 손대지 않았을 때만 따라간다.
  const [baseLoanRate, setBaseLoanRate] = useState(defaults.loan_rate);
  if (defaults.loan_rate !== baseLoanRate) {
    setBaseLoanRate(defaults.loan_rate);
    if (values.loan_rate === baseLoanRate) setValues((prev) => ({ ...prev, loan_rate: defaults.loan_rate }));
  }

  const set =
    <K extends keyof FinanceInput>(key: K) =>
    (v: FinanceInput[K]) =>
      setValues((prev) => ({ ...prev, [key]: v }));

  return (
    <form
      className="flex flex-col gap-8"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(values);
      }}
    >
      <fieldset className="flex flex-col gap-4">
        <legend className="text-sm font-semibold text-[var(--text-primary)]">확인해주세요</legend>
        <div className="grid gap-4 sm:grid-cols-2">
          <MoneyField label="자기자본" value={values.equity} onChange={set("equity")} />
          <RatioField label="원가율" value={values.cost_ratio} onChange={set("cost_ratio")} />
          <RatioField label="수수료율" value={values.fee_ratio} onChange={set("fee_ratio")} />
          <RatioField label="대출금리" value={values.loan_rate} onChange={set("loan_rate")} />
        </div>
      </fieldset>

      <fieldset className="flex flex-col gap-4">
        <legend className="text-sm font-semibold text-[var(--text-primary)]">입력해주세요</legend>
        <div className="grid gap-4 sm:grid-cols-2">
          <MoneyField label="보증금" value={values.deposit} onChange={set("deposit")} />
          <MoneyField label="권리금" value={values.key_money} onChange={set("key_money")} />
          <MoneyField label="인테리어 비용" value={values.interior_cost} onChange={set("interior_cost")} />
          <MoneyField label="설비 비용" value={values.equipment_cost} onChange={set("equipment_cost")} />
          <MoneyField label="월세" value={values.monthly_rent} onChange={set("monthly_rent")} />
          <MoneyField label="월 인건비" value={values.monthly_payroll} onChange={set("monthly_payroll")} />
          <MoneyField label="월 보험료" value={values.monthly_insurance} onChange={set("monthly_insurance")} />
          <MoneyField label="희망 대출금" value={values.desired_loan} onChange={set("desired_loan")} />
          <MoneyField
            label="예상 월매출"
            value={values.expected_monthly_revenue}
            onChange={set("expected_monthly_revenue")}
          />
        </div>
      </fieldset>

      <button
        type="submit"
        disabled={submitting}
        className="self-start rounded-md bg-[var(--accent)] px-5 py-2.5 text-sm font-semibold text-[var(--accent-fg)] transition-opacity hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] active:translate-y-px disabled:pointer-events-none disabled:opacity-50"
      >
        {submitting ? "계산 중…" : "시뮬레이션 실행"}
      </button>
    </form>
  );
}
