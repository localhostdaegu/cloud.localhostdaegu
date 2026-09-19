"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchPopulationSummary, fetchRegionalIndicators } from "../api";

const formatPeriod = (period: string) => `${period.slice(0, 4)}-${period.slice(4)}`;
const changePercent = (latest: number, base: number) => (base > 0 ? ((latest - base) / base) * 100 : null);
const signed = (pct: number) => `${pct > 0 ? "+" : ""}${pct.toFixed(1)}%`;

/** 개수 지표 — 키 → 화면 라벨. 표에 없는 키는 그리지 않는다(지하철은 아래에서 따로 그린다). */
const COUNT_LABELS: Record<string, string> = {
  traditional_market_count: "전통시장",
  baeknyeon_store_count: "백년가게",
  nadeul_store_count: "나들가게",
  onnuri_merchant_count: "온누리 가맹점",
};

const TIME_LABELS: Record<string, string> = {
  time_05_10: "05~10시",
  time_10_14: "10~14시",
  time_14_18: "14~18시",
  time_18_24: "18~24시",
};

function Population({ regionCode }: { regionCode: string }) {
  const { data } = useQuery({
    queryKey: ["population", regionCode],
    queryFn: () => fetchPopulationSummary(regionCode),
    staleTime: Infinity,
    retry: false,
  });
  if (!data) return null;

  const total = changePercent(data.latest_total, data.base_total);
  const maxBand = Math.max(...data.age_bands.map((b) => b.latest), 1);

  return (
    <section className="flex flex-col gap-2">
      <h3 className="flex items-baseline justify-between text-xs text-[var(--text-secondary)]">
        <span>주민등록 인구</span>
        <span>
          {formatPeriod(data.base_period)} → {formatPeriod(data.latest_period)}
        </span>
      </h3>
      <p className="text-sm tabular-nums text-[var(--text-primary)]">
        {data.latest_total.toLocaleString("ko-KR")}명
        {total !== null && <span className="ml-1.5 text-xs text-[var(--text-secondary)]">{signed(total)}</span>}
      </p>
      <ul className="flex flex-col gap-1.5">
        {data.age_bands.map((band) => {
          const change = changePercent(band.latest, band.base);
          return (
            <li key={band.label} className="grid grid-cols-[4.5rem_1fr_3.25rem] items-center gap-2 text-[11px]">
              <span className="text-[var(--text-secondary)]">{band.label}</span>
              <span className="h-1.5 rounded-full bg-[var(--bg-raised)]">
                <span
                  className="block h-full rounded-full bg-[var(--brand-mint)]"
                  style={{ width: `${(band.latest / maxBand) * 100}%` }}
                />
              </span>
              <span className="text-right tabular-nums text-[var(--text-secondary)]">
                {change === null ? "—" : signed(change)}
              </span>
            </li>
          );
        })}
      </ul>
      <p className="text-[11px] leading-snug text-[var(--text-secondary)]">
        사는 사람 수입니다. 실제 방문객이나 매출로 바꿔 읽지 마세요.
      </p>
    </section>
  );
}

function Indicators({ regionCode }: { regionCode: string }) {
  const { data } = useQuery({
    queryKey: ["indicators", regionCode],
    queryFn: () => fetchRegionalIndicators(regionCode),
    staleTime: Infinity,
    retry: false,
  });
  if (!data || data.length === 0) return null;

  const counts = data.filter((row) => row.breakdown === null && COUNT_LABELS[row.indicator_key] && row.value > 0);
  const hours = data.filter((row) => row.indicator_key === "subway_boarding_daily_avg" && row.breakdown !== null);
  const maxHour = Math.max(...hours.map((h) => h.value), 1);
  if (counts.length === 0 && hours.length === 0) return null;

  return (
    <section className="flex flex-col gap-3">
      {counts.length > 0 && (
        <>
          <h3 className="text-xs text-[var(--text-secondary)]">동네 특성</h3>
          <ul className="flex flex-wrap gap-1.5">
            {counts.map((row) => (
              <li
                key={row.indicator_key}
                className="rounded border border-[var(--border)] px-2 py-0.5 text-xs text-[var(--text-primary)]"
              >
                {COUNT_LABELS[row.indicator_key]}{" "}
                <span className="tabular-nums">
                  {row.value.toLocaleString("ko-KR")}
                  {row.unit}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}

      {hours.length > 0 && (
        <>
          <h3 className="flex items-baseline justify-between text-xs text-[var(--text-secondary)]">
            <span>지하철 승차 (하루 평균)</span>
            <span>{formatPeriod(hours[0].period)}</span>
          </h3>
          <ul className="flex flex-col gap-1.5">
            {hours.map((h) => (
              <li key={h.breakdown} className="grid grid-cols-[4.5rem_1fr_3.25rem] items-center gap-2 text-[11px]">
                <span className="text-[var(--text-secondary)]">{TIME_LABELS[h.breakdown!] ?? h.breakdown}</span>
                <span className="h-1.5 rounded-full bg-[var(--bg-raised)]">
                  <span
                    className="block h-full rounded-full bg-[var(--accent)]"
                    style={{ width: `${(h.value / maxHour) * 100}%` }}
                  />
                </span>
                <span className="text-right tabular-nums text-[var(--text-secondary)]">
                  {Math.round(h.value).toLocaleString("ko-KR")}명
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

/** 업종과 무관한 동네 배경 — 인구 구성 변화, 시장·가맹점, 지하철 시간대. 자료가 없는 동은 해당 블록을 그리지 않는다. */
export function RegionContext({ regionCode }: { regionCode: string }) {
  return (
    <div className="mt-5 flex flex-col gap-5 border-t border-[var(--border)] pt-5 empty:hidden">
      <Population regionCode={regionCode} />
      <Indicators regionCode={regionCode} />
    </div>
  );
}
