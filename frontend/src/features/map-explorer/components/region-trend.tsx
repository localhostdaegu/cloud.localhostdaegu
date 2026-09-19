"use client";

import { useQueries, useQuery } from "@tanstack/react-query";
import type { MetricKey } from "@/shared/api/types";
import { fetchMetrics, fetchShockEvents } from "../api";
import { YEARS } from "../lib/map-state";

interface RegionTrendProps {
  regionCode: string;
  industry: string;
}

const W = 272;
const H = 96;
const PAD_TOP = 14;
const BAR_GAP = 8;
/** YEARS의 마지막 해는 집계 중인 부분 연도 — 막대는 흐리게, 폐업률 선에서는 뺀다(연간 값과 비교 불가). */
const PARTIAL_YEAR = YEARS[YEARS.length - 1];

const percent = (ratio: number) => `${(ratio * 100).toFixed(1)}%`;

/** 지도(useMapData)와 같은 쿼리 키를 써서 이미 받은 연도는 다시 요청하지 않는다. */
function useYearlyValues(metric: MetricKey, regionCode: string, industry: string): (number | null)[] {
  const results = useQueries({
    queries: YEARS.map((year) => ({
      queryKey: ["metrics", metric, industry, year],
      queryFn: () => fetchMetrics(industry, metric, year),
      staleTime: Infinity,
    })),
  });
  return results.map((r) => r.data?.find((row) => row.region_code === regionCode)?.value ?? null);
}

/** 이 업종에 영향이 컸던(high) 사건만, 차트 범위 안에서 — 전부 나열하면 매년 있는 최저임금 인상이 차트를 덮는다. */
function useMajorShocks(industry: string): { year: number; name: string }[] {
  const { data } = useQuery({
    queryKey: ["shocks", industry],
    queryFn: () => fetchShockEvents(industry),
    staleTime: Infinity,
    select: (events) =>
      events
        .filter((e) => e.industry_impacts.some((i) => i.industry_id === industry && i.severity === "high"))
        .map((e) => ({ year: Number(e.start_date.slice(0, 4)), name: e.name }))
        .filter((e) => YEARS.includes(e.year)),
  });
  return data ?? [];
}

/** 선택한 동·업종의 연도별 점포 수(막대)와 폐업률(선). 값이 두 해 미만이면 추이가 아니므로 그리지 않는다. */
export function RegionTrend({ regionCode, industry }: RegionTrendProps) {
  const stores = useYearlyValues("store_count", regionCode, industry);
  const closures = useYearlyValues("closure_rate", regionCode, industry);
  const shocks = useMajorShocks(industry);
  const shockYears = new Set(shocks.map((e) => e.year));

  const known = YEARS.map((year, i) => ({ year, value: stores[i] })).filter(
    (p): p is { year: number; value: number } => p.value !== null,
  );
  if (known.length < 2) return null;

  const maxStores = Math.max(...known.map((p) => p.value), 1);
  const band = W / YEARS.length;
  const barHeight = (value: number) => (value / maxStores) * (H - PAD_TOP);

  const linePoints = YEARS.map((year, i) => ({ year, i, value: closures[i] })).filter(
    (p): p is { year: number; i: number; value: number } => p.value !== null && p.year !== PARTIAL_YEAR,
  );
  // 폐업률이 100%를 넘는 해(전년 말 점포보다 폐업이 많은 경우)는 눈금 상단에 붙여 그린다.
  const maxClosure = Math.min(1, Math.max(...linePoints.map((p) => p.value), 0.01));
  const lineY = (value: number) => H - (Math.min(value, maxClosure) / maxClosure) * (H - PAD_TOP);
  const peak = linePoints.reduce<(typeof linePoints)[number] | null>(
    (best, p) => (best === null || p.value > best.value ? p : best),
    null,
  );

  const first = known[0];
  const last = known.filter((p) => p.year !== PARTIAL_YEAR).at(-1) ?? known[known.length - 1];

  return (
    <figure className="mt-5 flex flex-col gap-2">
      <figcaption className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
        <span>연도별 추이</span>
        <span className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <span aria-hidden className="h-2 w-2 rounded-[2px] bg-[var(--brand-mint)]" />
            점포 수
          </span>
          <span className="flex items-center gap-1">
            <span aria-hidden className="h-0.5 w-3 bg-[var(--danger)]" />
            폐업률
          </span>
        </span>
      </figcaption>

      <svg
        viewBox={`0 0 ${W} ${H + 14}`}
        role="img"
        aria-label={`점포 수 ${first.year}년 ${first.value}개에서 ${last.year}년 ${last.value}개`}
        className="w-full"
      >
        {YEARS.map((year, i) => {
          const value = stores[i];
          return (
            <g key={year}>
              {value !== null && (
                <rect
                  x={i * band + BAR_GAP / 2}
                  y={H - barHeight(value)}
                  width={band - BAR_GAP}
                  height={barHeight(value)}
                  rx={2}
                  fill="var(--brand-mint)"
                  opacity={year === PARTIAL_YEAR ? 0.35 : 1}
                />
              )}
              {shockYears.has(year) && (
                <path
                  d={`M ${i * band + band / 2 - 3} 1 h 6 l -3 5 z`}
                  fill="var(--warn)"
                />
              )}
              <text x={i * band + band / 2} y={H + 11} textAnchor="middle" fontSize={9} fill="var(--text-secondary)">
                {`'${String(year).slice(2)}`}
              </text>
            </g>
          );
        })}
        {linePoints.length > 1 && (
          <polyline
            fill="none"
            stroke="var(--danger)"
            strokeWidth={1.5}
            points={linePoints.map((p) => `${p.i * band + band / 2},${lineY(p.value)}`).join(" ")}
          />
        )}
        {linePoints.map((p) => (
          <circle key={p.year} cx={p.i * band + band / 2} cy={lineY(p.value)} r={2} fill="var(--danger)" />
        ))}
      </svg>

      <p className="text-xs leading-relaxed text-[var(--text-secondary)]">
        점포 수 {first.year}년 {first.value}개 → {last.year}년 {last.value}개
        {peak && ` · 폐업률 최고 ${peak.year}년 ${percent(peak.value)}`}
        {stores[YEARS.length - 1] !== null && ` · ${PARTIAL_YEAR}년은 집계 중`}
      </p>

      {shocks.length > 0 && (
        <ul className="flex flex-col gap-1 text-[11px] leading-snug text-[var(--text-secondary)]">
          {shocks.map((e) => (
            <li key={`${e.year}-${e.name}`} className="flex gap-1.5">
              <span aria-hidden className="text-[var(--warn)]">▼</span>
              <span>
                <span className="tabular-nums text-[var(--text-primary)]">{e.year}</span> {e.name}
              </span>
            </li>
          ))}
        </ul>
      )}
    </figure>
  );
}
