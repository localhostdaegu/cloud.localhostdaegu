import type { FinanceStress } from "@/shared/api/types";
import { formatKrw } from "@/shared/format";

interface StressTableProps {
  stress: FinanceStress[];
  baseFixed: number;
  baseProfit: number;
}

/** 금리 +1%p·+2%p일 때의 월 고정비·기준 시나리오 손익 — 이자 변화만 반영한 계산이다(problem §9-2). */
export function StressTable({ stress, baseFixed, baseProfit }: StressTableProps) {
  if (stress.length === 0) return null;
  const rows = [
    { label: "현재 금리", fixed: baseFixed, profit: baseProfit },
    ...stress.map((s) => ({
      label: `+${Math.round(s.rate_delta * 100)}%p`,
      fixed: s.monthly_fixed,
      profit: s.base_operating_profit,
    })),
  ];
  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-xs text-[var(--text-secondary)]">금리가 오르면 (희망대출 이자만 반영)</h3>
      <table className="w-full text-xs tabular-nums">
        <thead>
          <tr className="text-left text-[var(--text-secondary)]">
            <th className="py-1 font-normal">금리</th>
            <th className="py-1 text-right font-normal">월 고정비</th>
            <th className="py-1 text-right font-normal">기준 영업이익</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label} className="border-t border-[var(--border)] text-[var(--text-primary)]">
              <td className="py-1.5">{row.label}</td>
              <td className="py-1.5 text-right">{formatKrw(row.fixed)}</td>
              <td className={`py-1.5 text-right ${row.profit < 0 ? "text-[var(--danger)]" : ""}`}>
                {formatKrw(row.profit)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
