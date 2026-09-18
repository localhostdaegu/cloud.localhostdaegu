"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { industryLabel } from "@/shared/industries";
import { encodeFinanceParam } from "@/shared/finance-param";
import type { FinanceInput } from "@/shared/api/types";
import { buildDefaults } from "../lib/form-defaults";
import {
  emptyDraft,
  loadDraft,
  recordCalculation,
  saveDraft,
  selectPlan,
  selectedPlan,
  withScope,
  type ConsultationDraft,
  type PlanKind,
} from "../lib/consultation-draft";
import { useLatestLoanRate } from "../hooks/use-latest-loan-rate";
import { simulateFinance } from "../api";
import { ConsultationProfileForm } from "./consultation-profile-form";
import { SimulatorForm } from "./simulator-form";
import { PlanComparison } from "./plan-comparison";
import { ResultView } from "./result-view";

/** URL district·industry·budget 프리필 → 폼 → 계산 → 최초안·현재안 비교 → 선택안 결과(§5-3). */
export function SimulatorPage() {
  const searchParams = useSearchParams();
  const industry = searchParams.get("industry");
  const district = searchParams.get("district");
  const region = searchParams.get("region");
  const loanRate = useLatestLoanRate();
  const defaults = buildDefaults({ budget: searchParams.get("budget"), industry, loanRate });

  // 행정동 10자리의 앞 5자리가 자치구 코드다 (2711059500 → 27110 중구).
  const districtCode = region ? region.slice(0, 5) : null;

  const [draft, setDraft] = useState<ConsultationDraft>(() => emptyDraft({ region, industry }));

  // 저장값 복원은 마운트 후에 한다 — 서버 렌더에는 sessionStorage 가 없다.
  // 지역·업종이 달라졌으면 비교 대상이 바뀐 것이므로 withScope 가 이전 결과를 무효화한다.
  useEffect(() => {
    const stored = loadDraft();
    if (stored) setDraft(withScope(stored, { region, industry }));
  }, [region, industry]);

  const update = (next: ConsultationDraft) => {
    saveDraft(next);
    setDraft(next);
  };

  // 제출 시점의 미입력 목록을 계산 성공까지 들고 간다 — onSuccess 는 variables 만 받는다.
  const [unconfirmed, setUnconfirmed] = useState<(keyof FinanceInput)[]>([]);

  const mutation = useMutation({
    mutationFn: simulateFinance,
    onSuccess: (result, input) => setDraft((prev) => {
      const next = recordCalculation(prev, input, result, unconfirmed);
      saveDraft(next);
      return next;
    }),
  });

  // 폼이 결과보다 앞서 있으면(제출 전 수정) 이전 입력 기준임을 알리고 새 선택을 막는다(§5-3).
  const [formValues, setFormValues] = useState<FinanceInput | null>(null);
  const plan = selectedPlan(draft);
  const stale =
    plan !== null && formValues !== null && JSON.stringify(formValues) !== JSON.stringify(plan.input);

  // 선택안의 입력만 리포트로 넘긴다 — 폼에서 고치는 중인 미제출 값은 싣지 않는다(§5-3).
  const analysisHref =
    plan && region && industry
      ? `/analysis?${new URLSearchParams({
          region,
          industry,
          ...(searchParams.get("year") ? { year: searchParams.get("year")! } : {}),
          finance: encodeFinanceParam(plan.input),
        }).toString()}`
      : undefined;

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-6 py-8">
      <header className="flex flex-col gap-1">
        <h1 className="text-lg font-semibold tracking-tight text-[var(--text-primary)]">창업자금 사전상담</h1>
        <p className="text-xs text-[var(--text-secondary)]">
          {industry ? industryLabel(industry) : "업종 미지정"}
          {district ? ` · ${district}` : ""} 기준으로 값을 채웠어요. 필요하면 수정하세요.
        </p>
      </header>

      <ConsultationProfileForm
        value={draft.profile}
        onChange={(profile) => update({ ...draft, profile })}
      />

      <SimulatorForm
        defaults={defaults}
        onSubmit={(payload, missing) => {
          setUnconfirmed(missing);
          mutation.mutate(payload);
        }}
        submitting={mutation.isPending}
        onValuesChange={useCallback((values: FinanceInput) => setFormValues(values), [])}
      />

      {mutation.isError && (
        <p role="alert" className="text-sm text-[var(--danger)]">
          {mutation.error instanceof Error ? mutation.error.message : "시뮬레이션에 실패했습니다."}
        </p>
      )}

      {stale && (
        <p role="status" className="text-sm text-[var(--warn)]">
          아래 결과는 이전 입력 기준이에요. 다시 계산하면 새 안으로 비교·선택할 수 있습니다.
        </p>
      )}

      {plan && (
        <>
          <PlanComparison
            baseline={draft.baseline}
            current={draft.current}
            selected={draft.selected}
            onSelect={(kind: PlanKind) => update(selectPlan(draft, kind))}
            changeReason={draft.change_reason}
            onChangeReason={(change_reason) => update({ ...draft, change_reason })}
            disabled={stale}
          />
          <ResultView
            result={plan.result}
            input={plan.input}
            category={industry ?? undefined}
            profile={draft.profile}
            districtCode={districtCode}
            backHref={`/simulate?${searchParams.toString()}`}
            analysisHref={analysisHref}
          />
        </>
      )}
    </div>
  );
}
