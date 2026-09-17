"use client";

import { useSearchParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { industryLabel } from "@/shared/industries";
import { encodeFinanceParam } from "@/shared/finance-param";
import { buildDefaults } from "../lib/form-defaults";
import { simulateFinance } from "../api";
import { SimulatorForm } from "./simulator-form";
import { ResultView } from "./result-view";

/** URL district·industry·budget 프리필 → 시뮬레이션 폼 → 결과(ResultView). */
export function SimulatorPage() {
  const searchParams = useSearchParams();
  const industry = searchParams.get("industry");
  const district = searchParams.get("district");
  const region = searchParams.get("region");
  const defaults = buildDefaults({ budget: searchParams.get("budget"), industry });

  const mutation = useMutation({ mutationFn: simulateFinance });

  // 결론을 만든 마지막 제출값(mutation.variables)을 그대로 리포트에 넘긴다 — 폼을 고친 뒤 미제출 값은 싣지 않는다.
  const analysisHref =
    mutation.variables && region && industry
      ? `/analysis?${new URLSearchParams({ region, industry, finance: encodeFinanceParam(mutation.variables) }).toString()}`
      : undefined;

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-6 py-8">
      <header className="flex flex-col gap-1">
        <h1 className="text-lg font-semibold tracking-tight text-[var(--text-primary)]">창업 재무 시뮬레이터</h1>
        <p className="text-xs text-[var(--text-secondary)]">
          {industry ? industryLabel(industry) : "업종 미지정"}
          {district ? ` · ${district}` : ""} 기준으로 값을 채웠어요. 필요하면 수정하세요.
        </p>
      </header>

      <SimulatorForm
        defaults={defaults}
        onSubmit={(payload) => mutation.mutate(payload)}
        submitting={mutation.isPending}
      />

      {mutation.isError && (
        <p role="alert" className="text-sm text-[var(--danger)]">
          {mutation.error instanceof Error ? mutation.error.message : "시뮬레이션에 실패했습니다."}
        </p>
      )}

      {mutation.data && (
        <ResultView
          result={mutation.data}
          category={industry ?? undefined}
          backHref={`/simulate?${searchParams.toString()}`}
          analysisHref={analysisHref}
        />
      )}
    </div>
  );
}
