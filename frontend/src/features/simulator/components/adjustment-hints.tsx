import type { FinanceInput } from "@/shared/api/types";
import { formatKrw } from "@/shared/format";

interface AdjustmentHintsProps {
  input: FinanceInput;
  /** 자기자본 외 조달 필요 — 0이면 줄일 이유가 없어 그리지 않는다. */
  externalFundingNeed: number;
  /** 운영준비금 개월 수(엔진 응답) — 월 비용 1원은 준비자금 reserveMonths원이다. */
  reserveMonths: number;
}

const CUT = 0.1;

/** 한 번 드는 비용은 그대로, 매달 드는 비용은 운영준비금 개월 수만큼 총 준비자금에 들어간다(problem §6-1). */
const LEVERS: { key: keyof FinanceInput; label: string; monthly: boolean }[] = [
  { key: "deposit", label: "보증금", monthly: false },
  { key: "key_money", label: "권리금", monthly: false },
  { key: "interior_cost", label: "인테리어 비용", monthly: false },
  { key: "equipment_cost", label: "설비 비용", monthly: false },
  { key: "monthly_rent", label: "월세", monthly: true },
  { key: "monthly_payroll", label: "월 인건비", monthly: true },
];

/** 조달 필요가 클 때 빚을 늘리는 것 말고 볼 수 있는 방향 — 어느 비용을 10% 줄이면 준비자금이 얼마나 줄어드는지.
 *  문제 정의 §1-3: 비용 축소·다른 점포 검토·계약 보류도 유효한 결과다. 판정이 아니라 산수만 보여준다. */
export function AdjustmentHints({ input, externalFundingNeed, reserveMonths }: AdjustmentHintsProps) {
  if (externalFundingNeed <= 0) return null;
  const hints = LEVERS.map(({ key, label, monthly }) => ({
    label,
    from: input[key],
    saving: Math.round(input[key] * CUT) * (monthly ? reserveMonths : 1),
  }))
    .filter((h) => h.saving > 0)
    .sort((a, b) => b.saving - a.saving)
    .slice(0, 3);
  if (hints.length === 0) return null;

  return (
    <section className="flex flex-col gap-2 rounded-md border border-[var(--border)] bg-[var(--bg-surface)] p-4">
      <h3 className="text-sm font-semibold text-[var(--text-primary)]">빌리기 전에 줄여 볼 수 있는 것</h3>
      <ul className="flex flex-col gap-1 text-xs text-[var(--text-secondary)]">
        {hints.map((h) => (
          <li key={h.label}>
            {h.label} {formatKrw(h.from)}을 10% 줄이면 준비자금이{" "}
            <span className="font-semibold tabular-nums text-[var(--text-primary)]">{formatKrw(h.saving)}</span> 줄어요
          </li>
        ))}
      </ul>
      <p className="text-xs leading-relaxed text-[var(--text-secondary)]">
        왼쪽 값을 바꿔 다시 계산하면 최초안과 나란히 비교됩니다. 조건이 맞지 않으면 다른 점포를 보거나 계약을 미루는
        것도 계획입니다.
      </p>
    </section>
  );
}
