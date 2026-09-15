"use client";

import { useSearchParams } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { industryLabel } from "@/shared/industries";
import { buildDefaults } from "../lib/form-defaults";
import { simulateFinance } from "../api";
import { SimulatorForm } from "./simulator-form";

/** URL district·industry·budget 프리필 → 시뮬레이션 폼 → 결과.
 *  결과 UI는 임시 JSON 요약(Task 6의 ResultView가 이 자리를 교체한다). */
export function SimulatorPage() {
  const searchParams = useSearchParams();
  const industry = searchParams.get("industry");
  const district = searchParams.get("district");
  const defaults = buildDefaults({ budget: searchParams.get("budget"), industry });

  const mutation = useMutation({ mutationFn: simulateFinance });

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
        <pre className="overflow-x-auto rounded-md border border-[var(--border)] bg-[var(--bg-surface)] p-4 text-xs text-[var(--text-primary)]">
          {JSON.stringify(mutation.data, null, 2)}
        </pre>
      )}
    </div>
  );
}
