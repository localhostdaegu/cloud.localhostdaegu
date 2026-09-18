"use client";

import { useSearchParams } from "next/navigation";
import { parseFinanceParam } from "@/shared/finance-param";
import {
  loadDraft,
  selectedPlan,
  toConsultationContext,
} from "@/features/simulator/lib/consultation-draft";
import type { StartAnalysisParams } from "../hooks/use-agent-report";
import { AnalysisForm } from "./analysis-form";
import { ProgressPanel } from "./progress-panel";
import { ReportView } from "./report-view";
import { useAgentReport } from "../hooks/use-agent-report";

/** URL region·industry 프리필 → 분석 시작 → 진행 패널(좌) + 리포트(우). */
export function AnalysisPage() {
  const searchParams = useSearchParams();
  const { state, start, loading } = useAgentReport();

  // 저장된 선택안이 있으면 그것으로 상담자료를 만든다(§5-3). URL 의 finance 는 이전 링크 복원용이다.
  const draft = loadDraft();
  const plan = draft === null ? null : selectedPlan(draft);
  const finance = plan?.input ?? parseFinanceParam(searchParams.get("finance"));

  const startWithConsultation = (params: StartAnalysisParams) =>
    start(
      draft === null || plan === null
        ? params
        : { ...params, finance: plan.input, purpose: "handoff", consultation: toConsultationContext(draft) },
    );

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-1 flex-col gap-8 px-6 py-8">
      <div className="max-w-xl">
        <AnalysisForm
          initialRegion={searchParams.get("region") ?? ""}
          initialIndustry={searchParams.get("industry") ?? ""}
          finance={finance}
          onSubmit={startWithConsultation}
          disabled={loading}
        />
        {state.error && (
          <p role="alert" className="mt-3 text-sm text-[var(--danger)]">
            {state.error}
          </p>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-8 lg:flex-row lg:gap-10">
        <div className="w-full shrink-0 lg:w-72">
          <ProgressPanel state={state} />
        </div>
        <div className="min-w-0 flex-1">
          <ReportView state={state} />
        </div>
      </div>
    </div>
  );
}
