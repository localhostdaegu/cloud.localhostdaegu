"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchConsultationCandidates } from "../api";
import type { ConsultationCandidate, ProviderType } from "@/shared/api/types";
import { formatKrw } from "@/shared/format";

/** iM뱅크 공식 상담 안내 — 후보가 없어도 남는 일반 경로(§5-2·§10-3). */
const IMBANK_CONSULTATION_URL = "https://www.imbank.co.kr/cms/dgi/sdd_6/sdd_63/1193401_3090.html";

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

/** 검토 단계 — 승인이나 신청 완료가 아니다. */
const STATUS_LABEL: Record<ConsultationCandidate["status"], string> = {
  reviewable: "검토 가능",
  prerequisites_needed: "선행 절차 필요",
  needs_check: "확인 필요",
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
  externalFundingNeed: number;
  category?: string;
  businessRegistered?: boolean | null;
  businessAgeMonths?: number | null;
  ownerAge?: number | null;
}

function Bullets({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs font-medium text-[var(--text-primary)]">{title}</span>
      <ul className="flex flex-col gap-0.5 pl-3 text-xs text-[var(--text-secondary)]">
        {items.map((item) => (
          <li key={item} className="list-disc">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function MatchingCards({
  externalFundingNeed,
  category,
  businessRegistered,
  businessAgeMonths,
  ownerAge,
}: MatchingCardsProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["consultation", externalFundingNeed, category, businessRegistered, businessAgeMonths, ownerAge],
    queryFn: () =>
      fetchConsultationCandidates({
        externalFundingNeed,
        category,
        businessRegistered,
        businessAgeMonths,
        ownerAge,
      }),
  });

  if (isLoading) {
    return <p className="text-sm text-[var(--text-secondary)]">상품을 찾는 중…</p>;
  }

  if (isError) {
    return (
      <p role="alert" className="text-sm text-[var(--danger)]">
        상담 후보를 불러오지 못했습니다. 계산 결과와 확인 사항은 그대로 사용할 수 있어요.
      </p>
    );
  }

  // 후보가 없어도 상담 준비는 계속된다 — 조건을 바꾸라고만 하지 않는다(§3-1·§4-2).
  if (!data || data.length === 0) {
    return (
      <div className="flex flex-col gap-2 rounded-md border border-[var(--border)] bg-[var(--bg-raised)] p-4">
        <p className="text-sm font-semibold text-[var(--text-primary)]">
          iM뱅크 취급이 확인된 상품을 찾지 못했어요
        </p>
        <p className="text-xs text-[var(--text-secondary)]">
          공개 자료에서 취급·연계 근거를 확인한 상품만 후보로 보여줍니다. 확인하지 못한 상품이 있어도 상담은 가능해요.
        </p>
        <p className="text-xs text-[var(--text-secondary)]">
          상담에서 이렇게 물어보세요 — &ldquo;현재 창업 단계에서 상담 가능한 자금과 신청 시점이 어떻게 되나요?&rdquo;
        </p>
        <a
          href={IMBANK_CONSULTATION_URL}
          target="_blank"
          rel="noreferrer"
          className="w-fit text-xs text-[var(--accent)] underline decoration-[var(--border)] underline-offset-4 transition-colors hover:decoration-[var(--accent)]"
        >
          iM뱅크 공식 상담 안내 확인 →
        </a>
      </div>
    );
  }

  return (
    <ul className="grid gap-3 sm:grid-cols-2">
      {data.map(({ product, metadata, status, reason, unresolved_conditions }) => (
        <li
          key={product.product_id}
          className="flex flex-col gap-2 rounded-md border border-[var(--border)] bg-[var(--bg-raised)] p-4"
        >
          <span className="flex flex-wrap items-center gap-1.5">
            <span
              className={`inline-flex w-fit items-center rounded px-2 py-0.5 text-xs font-medium ${PROVIDER_STYLE[product.provider_type]}`}
            >
              {PROVIDER_LABEL[product.provider_type]}
            </span>
            <span className="inline-flex w-fit items-center rounded border border-[var(--border)] px-2 py-0.5 text-xs text-[var(--text-secondary)]">
              {STATUS_LABEL[status]}
            </span>
          </span>
          <span className="text-sm font-semibold text-[var(--text-primary)]">{product.product_name}</span>
          <span className="text-xs text-[var(--text-secondary)]">{product.provider}</span>
          <span className="text-xs text-[var(--text-secondary)]">
            한도 {formatLimit(product.loan_limit)} · 금리 {formatRate(product.interest_rate)}
          </span>
          <span className="text-xs text-[var(--text-primary)]">{reason}</span>

          <Bullets title="먼저 밟을 절차" items={metadata.prerequisites} />
          <Bullets title="신청 경로" items={metadata.application_steps} />
          <Bullets title="준비 서류" items={metadata.documents} />
          <Bullets title="상담에서 확인할 것" items={unresolved_conditions} />

          <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <a
              href={product.url}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-[var(--accent)] underline decoration-[var(--border)] underline-offset-4 transition-colors hover:decoration-[var(--accent)]"
            >
              공식 안내 보기
            </a>
            {metadata.verified_at && (
              <span className="text-xs text-[var(--text-secondary)]">
                {metadata.verified_at} 확인 (접수 가능 보장 아님)
              </span>
            )}
          </span>
        </li>
      ))}
    </ul>
  );
}
