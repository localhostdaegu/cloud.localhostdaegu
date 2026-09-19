"use client";

import { useEffect, useState } from "react";
import type { FinanceInput } from "@/shared/api/types";
import { manwonToWon, wonToManwon } from "../lib/money";

/** 미입력 판정 대상 — 금액 필드만. 비율은 업종 벤치마크·ECOS 조회라는 출처가 있어 제외한다. */
const AMOUNT_FIELDS = [
  "deposit", "key_money", "interior_cost", "equipment_cost",
  "monthly_rent", "monthly_payroll", "monthly_insurance",
  "equity", "desired_loan", "expected_monthly_revenue",
] as const;

interface SimulatorFormProps {
  defaults: FinanceInput;
  /** unconfirmed: 사용자가 한 번도 손대지 않았는데 0인 금액 — 유효한 0원과 구분한다(§5-3). */
  onSubmit: (payload: FinanceInput, unconfirmed: (keyof FinanceInput)[]) => void;
  submitting?: boolean;
  /** 미제출 수정 감지용 — 제출 전 값이 결과와 어긋나는지 페이지가 판단한다(§5-3). */
  onValuesChange?: (values: FinanceInput) => void;
  /** 월세 참고값 도우미 — 고른 값을 월세 칸에 넣는 함수를 받아 그린다. 폼은 자료 조회를 모른다. */
  rentHelper?: (applyRent: (won: number) => void) => React.ReactNode;
}

const FIELD =
  "w-full rounded-md border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]";

/** 원 단위 int 필드를 만원 단위로 표시·입력받는다. 내부 state는 항상 원 단위.
 *
 *  손대지 않은 0은 **빈 칸**으로 보여준다(§5-3 "빈 값과 0을 구별한다").
 *  0을 미리 채워 두면 사용자가 0을 확인할 방법이 없고, 미입력이 유효한 0원처럼 보인다.
 */
function MoneyField({
  label,
  value,
  touched,
  onChange,
}: {
  label: string;
  value: number;
  touched: boolean;
  onChange: (won: number) => void;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-xs font-medium tracking-wide text-[var(--text-secondary)]">
      {label}
      <div className="flex items-center gap-2">
        <input
          type="number"
          inputMode="numeric"
          value={touched || value !== 0 ? wonToManwon(value) : ""}
          placeholder="미입력"
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
export function SimulatorForm({ defaults, onSubmit, submitting, onValuesChange, rentHelper }: SimulatorFormProps) {
  const [values, setValues] = useState<FinanceInput>(defaults);
  const [touched, setTouched] = useState<Set<keyof FinanceInput>>(() => new Set());
  // 대출금리 기본값은 최신 금리 조회 후 늦게 바뀐다 — 사용자가 아직 손대지 않았을 때만 따라간다.
  const [baseLoanRate, setBaseLoanRate] = useState(defaults.loan_rate);
  if (defaults.loan_rate !== baseLoanRate) {
    setBaseLoanRate(defaults.loan_rate);
    if (values.loan_rate === baseLoanRate) setValues((prev) => ({ ...prev, loan_rate: defaults.loan_rate }));
  }

  useEffect(() => onValuesChange?.(values), [values, onValuesChange]);

  const set =
    <K extends keyof FinanceInput>(key: K) =>
    (v: FinanceInput[K]) => {
      setTouched((prev) => new Set(prev).add(key));
      setValues((prev) => ({ ...prev, [key]: v }));
    };

  return (
    <form
      className="flex flex-col gap-8"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(
          values,
          AMOUNT_FIELDS.filter((field) => values[field] === 0 && !touched.has(field)),
        );
      }}
    >
      <fieldset className="flex flex-col gap-4">
        <legend className="text-sm font-semibold text-[var(--text-primary)]">확인해주세요</legend>
        <div className="grid gap-4 sm:grid-cols-2">
          <MoneyField
            label="자기자본"
            value={values.equity}
            touched={touched.has("equity")}
            onChange={set("equity")}
          />
          <RatioField label="원가율" value={values.cost_ratio} onChange={set("cost_ratio")} />
          <RatioField label="수수료율" value={values.fee_ratio} onChange={set("fee_ratio")} />
          <RatioField label="대출금리" value={values.loan_rate} onChange={set("loan_rate")} />
        </div>
      </fieldset>

      <fieldset className="flex flex-col gap-4">
        <legend className="text-sm font-semibold text-[var(--text-primary)]">입력해주세요</legend>
        <div className="grid gap-4 sm:grid-cols-2">
          <MoneyField
            label="보증금"
            value={values.deposit}
            touched={touched.has("deposit")}
            onChange={set("deposit")}
          />
          <MoneyField
            label="권리금"
            value={values.key_money}
            touched={touched.has("key_money")}
            onChange={set("key_money")}
          />
          <MoneyField
            label="인테리어 비용"
            value={values.interior_cost}
            touched={touched.has("interior_cost")}
            onChange={set("interior_cost")}
          />
          <MoneyField
            label="설비 비용"
            value={values.equipment_cost}
            touched={touched.has("equipment_cost")}
            onChange={set("equipment_cost")}
          />
          <MoneyField
            label="월세"
            value={values.monthly_rent}
            touched={touched.has("monthly_rent")}
            onChange={set("monthly_rent")}
          />
          <MoneyField
            label="월 인건비"
            value={values.monthly_payroll}
            touched={touched.has("monthly_payroll")}
            onChange={set("monthly_payroll")}
          />
          <MoneyField
            label="월 보험료"
            value={values.monthly_insurance}
            touched={touched.has("monthly_insurance")}
            onChange={set("monthly_insurance")}
          />
          <MoneyField
            label="희망 대출금"
            value={values.desired_loan}
            touched={touched.has("desired_loan")}
            onChange={set("desired_loan")}
          />
          <MoneyField
            label="예상 월매출"
            value={values.expected_monthly_revenue}
            touched={touched.has("expected_monthly_revenue")}
            onChange={set("expected_monthly_revenue")}
          />
        </div>
        {rentHelper?.(set("monthly_rent"))}
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
