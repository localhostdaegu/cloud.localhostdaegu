"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchMatching } from "../api";
import type { ProviderType } from "@/shared/api/types";
import { formatKrw } from "@/shared/format";

/** grade-badge.tsx·risk-card.tsx의 pill 관행(border+텍스트색)을 재사용. */
const PROVIDER_LABEL: Record<ProviderType, string> = {
  guarantee: "보증",
  bank: "은행",
  policy: "정책",
};

const PROVIDER_STYLE: Record<ProviderType, string> = {
  guarantee: "border border-[var(--info)] text-[var(--info)]",
  bank: "border border-[var(--ok)] text-[var(--ok)]",
  policy: "border border-[var(--violet)] text-[var(--violet)]",
};

/** 수기 상품 JSON은 공시 수치가 없으면 null — 임의 수치를 만들지 않고 문구로 대신한다. */
function formatLimit(won: number | null): string {
  return won === null ? "미정" : formatKrw(won);
}

/** 보증상품·변동금리는 취급은행이 금리를 정하므로 null. */
function formatRate(rate: number | null): string {
  return rate === null ? "은행별 상이" : `${rate}%`;
}

interface MatchingCardsProps {
  fundingGap: number;
  category?: string;
}

export function MatchingCards({ fundingGap, category }: MatchingCardsProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["matching", fundingGap, category],
    queryFn: () => fetchMatching(fundingGap, category),
  });

  if (isLoading) {
    return <p className="text-sm text-[var(--text-secondary)]">상품을 찾는 중…</p>;
  }

  if (isError) {
    return (
      <p role="alert" className="text-sm text-[var(--danger)]">
        매칭 상품을 불러오지 못했습니다.
      </p>
    );
  }

  if (!data || data.length === 0) {
    return (
      <p className="text-sm text-[var(--text-secondary)]">
        조건에 맞는 상품을 찾지 못했어요 — 조건을 바꿔보세요
      </p>
    );
  }

  return (
    <ul className="grid gap-3 sm:grid-cols-3">
      {data.map((product) => (
        <li
          key={product.product_id}
          className="flex flex-col gap-2 rounded-md border border-[var(--border)] bg-[var(--bg-raised)] p-4"
        >
          <span
            className={`inline-flex w-fit items-center rounded px-2 py-0.5 text-xs font-medium ${PROVIDER_STYLE[product.provider_type]}`}
          >
            {PROVIDER_LABEL[product.provider_type]}
          </span>
          <span className="text-sm font-semibold text-[var(--text-primary)]">{product.product_name}</span>
          <span className="text-xs text-[var(--text-secondary)]">{product.provider}</span>
          <span className="text-xs text-[var(--text-secondary)]">
            한도 {formatLimit(product.loan_limit)} · 금리 {formatRate(product.interest_rate)}
          </span>
          <a
            href={product.url}
            target="_blank"
            rel="noreferrer"
            className="text-xs text-[var(--accent)] underline decoration-[var(--border)] underline-offset-4 transition-colors hover:decoration-[var(--accent)]"
          >
            상세 보기
          </a>
        </li>
      ))}
    </ul>
  );
}
