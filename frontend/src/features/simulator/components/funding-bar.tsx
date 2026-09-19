import { formatKrw } from "@/shared/format";

interface FundingBarProps {
  total: number;
  equity: number;
  desiredLoan: number;
  gap: number;
}

/** 총 준비자금을 무엇으로 채우는지 한 줄로 보여준다 — 자기자본 · 희망대출(미확보) · 남는 부족액.
 *  희망대출은 아직 빌리지 않은 돈이므로 확보 자금과 같은 색으로 칠하지 않는다(§7-2). */
export function FundingBar({ total, equity, desiredLoan, gap }: FundingBarProps) {
  if (total <= 0) return null;
  const equityUsed = Math.min(equity, total);
  const loanUsed = Math.min(desiredLoan, total - equityUsed);
  const segments = [
    { key: "equity", label: "자기자본", amount: equityUsed, color: "var(--accent)" },
    { key: "loan", label: "희망대출(미확보)", amount: loanUsed, color: "var(--brand-mint)" },
    { key: "gap", label: "남는 부족액", amount: gap, color: "var(--danger)" },
  ].filter((s) => s.amount > 0);

  return (
    <figure className="flex flex-col gap-2">
      <figcaption className="flex items-baseline justify-between gap-3 text-xs text-[var(--text-secondary)]">
        <span>자금 구성</span>
        <span className="tabular-nums">총 준비자금 {formatKrw(total)}</span>
      </figcaption>
      <div
        role="img"
        aria-label={segments.map((s) => `${s.label} ${formatKrw(s.amount)}`).join(", ")}
        className="flex h-3 overflow-hidden rounded-full bg-[var(--bg-raised)]"
      >
        {segments.map((s) => (
          <span key={s.key} style={{ width: `${(s.amount / total) * 100}%`, backgroundColor: s.color }} />
        ))}
      </div>
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-[var(--text-secondary)]">
        {segments.map((s) => (
          <li key={s.key} className="flex items-center gap-1.5">
            <span aria-hidden className="size-2 rounded-full" style={{ backgroundColor: s.color }} />
            {s.label} <span className="tabular-nums text-[var(--text-primary)]">{formatKrw(s.amount)}</span>
          </li>
        ))}
      </ul>
    </figure>
  );
}
