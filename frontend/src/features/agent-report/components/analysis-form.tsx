"use client";

import { useState } from "react";
import { INDUSTRIES, industryLabel } from "@/shared/industries";
import type { RegionName } from "@/shared/api/use-region-names";
import type { FinanceInput } from "@/shared/api/types";
import type { StartAnalysisParams } from "../hooks/use-agent-report";

interface AnalysisFormProps {
  initialRegion: string;
  initialIndustry: string;
  /** 행정동 선택지 — 화면에는 10자리 코드 대신 동 이름을 보여준다. 제출값은 그대로 코드다. */
  regions?: RegionName[];
  finance?: FinanceInput;
  onSubmit: (params: StartAnalysisParams) => void;
  disabled?: boolean;
}

const FIELD =
  "rounded-md border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]";

export function AnalysisForm({ initialRegion, initialIndustry, regions = [], finance, onSubmit, disabled }: AnalysisFormProps) {
  const [region, setRegion] = useState(initialRegion);
  const [industry, setIndustry] = useState(initialIndustry);
  const [question, setQuestion] = useState("");

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({ region, industry, question: question.trim() || undefined, ...(finance ? { finance } : {}) });
      }}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="flex flex-col gap-1.5 text-xs font-medium tracking-wide text-[var(--text-secondary)]">
          행정동
          <select value={region} onChange={(e) => setRegion(e.target.value)} className={FIELD}>
            <option value="">동을 선택하세요</option>
            {/* 목록을 받기 전이거나 목록에 없는 딥링크 값도 선택 상태로 남긴다. */}
            {region && !regions.some((r) => r.code === region) && <option value={region}>지도에서 선택한 동</option>}
            {regions.map((r) => (
              <option key={r.code} value={r.code}>
                {r.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1.5 text-xs font-medium tracking-wide text-[var(--text-secondary)]">
          업종
          <select value={industry} onChange={(e) => setIndustry(e.target.value)} className={FIELD}>
            <option value="">업종을 선택하세요</option>
            {industry && !(INDUSTRIES as readonly string[]).includes(industry) && (
              <option value={industry}>{industryLabel(industry)}</option>
            )}
            {INDUSTRIES.map((id) => (
              <option key={id} value={id}>
                {industryLabel(id)}
              </option>
            ))}
          </select>
        </label>
      </div>
      {finance && (
        <p className="rounded-md border border-[var(--border)] bg-[var(--bg-raised)] px-3 py-2 text-xs text-[var(--text-secondary)]">
          시뮬레이션 입력이 함께 전달돼요 — 리포트에 재무 시뮬레이션 계산표가 추가됩니다.
        </p>
      )}
      <label className="flex flex-col gap-1.5 text-xs font-medium tracking-wide text-[var(--text-secondary)]">
        추가 질문 (선택)
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={3}
          placeholder="예: 원두 가격이 오르면 손익분기점이 어떻게 달라지나요?"
          className={`${FIELD} resize-y placeholder:text-[var(--text-secondary)]`}
        />
      </label>
      <button
        type="submit"
        disabled={disabled || !region || !industry}
        className="self-start rounded-md bg-[var(--accent)] px-5 py-2.5 text-sm font-semibold text-[var(--accent-fg)] transition-opacity hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] active:translate-y-px disabled:pointer-events-none disabled:opacity-50"
      >
        {/* 사전상담에서 넘어온 사람의 목적은 분석이 아니라 은행에 가져갈 자료다. */}
        {finance ? (disabled ? "만드는 중…" : "상담자료 만들기") : disabled ? "분석 중…" : "분석 시작"}
      </button>
    </form>
  );
}
