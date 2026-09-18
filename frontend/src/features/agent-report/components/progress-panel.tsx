import type { AgentName } from "@/shared/api/types";
import type { AgentState, AgentStatus } from "../lib/agent-events";

const AGENT_ORDER: AgentName[] = ["orchestrator", "market", "shock", "funding"];

/** 전환계획 §3-1 — 내부 에이전트·도구명이 아니라 사용자가 읽는 단계로 보여준다. */
const LABEL: Record<AgentName, string> = {
  orchestrator: "입력 확인",
  market: "지역 근거",
  shock: "관련 뉴스",
  funding: "자금 계산",
};

/** 도구 이름도 마찬가지다. 모르는 도구는 그대로 두되 새 이름을 지어내지 않는다. */
const TOOL_LABEL: Record<string, string> = {
  region_metrics: "지역 지표 조회",
  risk_score: "업종 위험도 조회",
  news_search: "관련 뉴스 검색",
  finance_simulate: "준비자금 계산",
  product_matching: "상담 후보 정리",
  funding_search: "정책자금 공고 검색",
};

const DOT: Record<AgentStatus, string> = {
  idle: "bg-[var(--border)]",
  running: "bg-[var(--warn)] animate-pulse",
  done: "bg-[var(--ok)]",
  error: "bg-[var(--danger)]",
};

/** 색상만으로 상태를 전달하지 않도록 스크린리더/텍스트 라벨을 함께 노출한다. */
const STATUS_LABEL: Record<AgentStatus, string> = {
  idle: "대기",
  running: "진행 중",
  done: "완료",
  error: "오류",
};

interface ProgressPanelProps {
  state: AgentState;
}

export function ProgressPanel({ state }: ProgressPanelProps) {
  return (
    <div className="flex flex-col" role="status" aria-live="polite">
      <h2 className="mb-1 text-xs font-semibold tracking-wide text-[var(--text-secondary)]">진행 상황</h2>
      <ol className="flex flex-col divide-y divide-[var(--border)]">
        {AGENT_ORDER.map((name) => {
          const slot = state.agents[name];
          return (
            <li key={name} className="py-3.5">
              <div className="flex items-center gap-2.5">
                <span
                  aria-hidden
                  className={`h-2 w-2 shrink-0 rounded-full transition-colors duration-300 ${DOT[slot.status]}`}
                />
                <span className="text-sm font-medium text-[var(--text-primary)]">{LABEL[name]}</span>
                <span className="ml-auto text-xs text-[var(--text-secondary)]">{STATUS_LABEL[slot.status]}</span>
              </div>
              {slot.tools.length > 0 && (
                <ul className="mt-2 ml-1 flex flex-col gap-1 border-l border-[var(--border)] pl-3.5">
                  {slot.tools.map((t, i) => (
                    <li
                      key={`${i}:${t.tool}`}
                      className={
                        i === slot.tools.length - 1
                          ? "text-xs leading-relaxed text-[var(--text-primary)]"
                          : "text-xs leading-relaxed text-[var(--text-secondary)]"
                      }
                    >
                      <span className="font-medium">{TOOL_LABEL[t.tool] ?? t.tool}</span> — {t.summary}
                    </li>
                  ))}
                </ul>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
