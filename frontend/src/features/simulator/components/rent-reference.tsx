"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { RentPrice } from "@/shared/api/types";
import { formatKrw } from "@/shared/format";
import { fetchLatestRents } from "../api";

const M2_PER_PYEONG = 3.3058;
const BUILDING_LABEL: Record<RentPrice["building_type"], string> = {
  small: "소규모 상가",
  medium_large: "중대형 상가",
};

const keyOf = (row: RentPrice) => `${row.region_name}|${row.building_type}`;

/** 조사 평균 임대료(천원/㎡) × 면적 → 월세 참고값(원). 만원 미만은 버린다 — 폼 입력 단위가 만원이다. */
export function estimateMonthlyRent(rentPerM2: number, pyeong: number): number {
  return Math.floor((rentPerM2 * 1000 * pyeong * M2_PER_PYEONG) / 10_000) * 10_000;
}

interface RentReferenceProps {
  onApply: (won: number) => void;
}

/** 월세를 아직 모를 때 쓰는 참고값 — 상권과 면적을 고르면 조사 평균으로 계산해 월세 칸에 넣는다.
 *  매물 시세가 아니라 표본 조사 평균이므로 넣은 뒤에도 사용자가 고칠 수 있게 입력 칸을 그대로 둔다. */
export function RentReference({ onApply }: RentReferenceProps) {
  const { data } = useQuery({ queryKey: ["rents-latest"], queryFn: fetchLatestRents, staleTime: Infinity, retry: false });
  const rows = (data ?? []).filter((row) => row.rent_per_m2 !== null);
  const [selected, setSelected] = useState("");
  const [pyeong, setPyeong] = useState(10);
  if (rows.length === 0) return null;

  const row = rows.find((r) => keyOf(r) === selected) ?? rows.find((r) => r.building_type === "small") ?? rows[0];
  const estimate = estimateMonthlyRent(row.rent_per_m2!, pyeong);
  const period = `${row.period.slice(0, 4)}년 ${row.period.slice(5)}분기`;

  return (
    <details className="rounded-md border border-[var(--border)] bg-[var(--bg-raised)] px-3 py-2 text-xs text-[var(--text-secondary)]">
      <summary className="cursor-pointer font-medium text-[var(--text-primary)]">월세를 아직 모르겠다면 — 상권 평균으로 채우기</summary>
      <div className="mt-3 flex flex-col gap-3">
        <div className="grid gap-3 sm:grid-cols-[1fr_6rem]">
          <label className="flex flex-col gap-1">
            상권
            <select
              value={keyOf(row)}
              onChange={(e) => setSelected(e.target.value)}
              className="rounded-md border border-[var(--border)] bg-[var(--bg-surface)] px-2 py-1.5 text-sm text-[var(--text-primary)]"
            >
              {rows.map((r) => (
                <option key={keyOf(r)} value={keyOf(r)}>
                  {r.region_level === 1 ? `${r.region_name} 평균` : r.region_name} · {BUILDING_LABEL[r.building_type]}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            면적(평)
            <input
              type="number"
              min={1}
              value={pyeong}
              onChange={(e) => setPyeong(Math.max(1, Number(e.target.value) || 1))}
              className="rounded-md border border-[var(--border)] bg-[var(--bg-surface)] px-2 py-1.5 text-sm tabular-nums text-[var(--text-primary)]"
            />
          </label>
        </div>
        <p className="leading-relaxed">
          ㎡당 <span className="tabular-nums">{Math.round(row.rent_per_m2! * 1000).toLocaleString("ko-KR")}원</span> ×{" "}
          {pyeong}평 ≈ <strong className="tabular-nums text-[var(--text-primary)]">월 {formatKrw(estimate)}</strong>
          {row.vacancy_rate !== null && ` · 공실률 ${row.vacancy_rate.toFixed(1)}%`}
        </p>
        <button
          type="button"
          onClick={() => onApply(estimate)}
          className="self-start rounded-md border border-[var(--accent)] px-3 py-1.5 text-xs font-semibold text-[var(--accent)] transition-colors hover:bg-[var(--bg-surface)]"
        >
          월세 칸에 넣기
        </button>
        <p className="leading-relaxed">
          한국부동산원 상업용부동산 임대동향조사 {period} 표본 평균입니다. 실제 매물 월세와 다를 수 있으니 계약 조건을
          알게 되면 고쳐 주세요.
        </p>
      </div>
    </details>
  );
}
