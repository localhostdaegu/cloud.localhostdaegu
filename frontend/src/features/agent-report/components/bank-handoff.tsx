"use client";

import type { AgentState } from "../lib/agent-events";
import { canExport, toConsultationMarkdown, type ExportMeta } from "../lib/consultation-export";
import { recordConsultationDocument } from "@/features/simulator/lib/consultation-session";
import type { PlanKind } from "@/features/simulator/lib/consultation-draft";

/** 공식 경로 — 금융상품 문의와 경영컨설팅은 목적이 다르므로 나눠 안내한다(§6 T5). */
const OFFICIAL_LINKS = [
  { label: "iM뱅크 공식 상담 안내 (경영컨설팅)", url: "https://www.imbank.co.kr/cms/dgi/sdd_6/sdd_63/1193401_3090.html" },
  { label: "iM뱅크 홈페이지 (금융상품 문의)", url: "https://www.imbank.co.kr/" },
];

const BUTTON =
  "rounded-md px-4 py-2 text-sm font-semibold transition-opacity focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] disabled:pointer-events-none disabled:opacity-50";

interface BankHandoffProps {
  state: AgentState;
  meta: ExportMeta;
  /** 서버에 자료를 남길 세션 — 없으면 내려받기만 한다. */
  sessionId?: string | null;
  planKind?: PlanKind | null;
}

function download(markdown: string, meta: ExportMeta) {
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `상담준비자료_${meta.regionLabel}_${meta.industryLabel}_${meta.generatedAt}.md`;
  anchor.click();
  URL.revokeObjectURL(url);
}

/** 상담자료 저장·인쇄와 공식 상담 경로 안내(§6 T5).
 *  은행으로의 이동을 강제하지 않는다 — 보류·추가 확인을 골라도 저장은 가능하다. */
export function BankHandoff({ state, meta, sessionId, planKind }: BankHandoffProps) {
  const ready = canExport(state);

  return (
    <section className="flex flex-col gap-4 rounded-md border border-[var(--border)] bg-[var(--bg-raised)] p-4 print:hidden">
      <div className="flex flex-col gap-1">
        <h2 className="text-sm font-semibold text-[var(--text-primary)]">상담 준비자료</h2>
        <p className="text-xs text-[var(--text-secondary)]">
          플랫폼이 작성한 준비자료입니다. 저장해서 상담에 <strong>직접 지참</strong>하세요 — 링크를 눌러도 은행에
          자료가 전송되지 않습니다.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={!ready}
          onClick={() => {
            const markdown = toConsultationMarkdown(state, meta);
            download(markdown, meta);
            if (sessionId && planKind) void recordConsultationDocument(sessionId, planKind, markdown);
          }}
          className={`${BUTTON} bg-[var(--accent)] text-[var(--accent-fg)] hover:opacity-90`}
        >
          상담자료 저장 (Markdown)
        </button>
        <button
          type="button"
          disabled={!ready}
          onClick={() => window.print()}
          className={`${BUTTON} border border-[var(--border)] text-[var(--text-primary)] hover:bg-[var(--bg-surface)]`}
        >
          인쇄 · PDF로 저장
        </button>
      </div>

      {!ready && (
        <p className="text-xs text-[var(--text-secondary)]">
          상담자료가 완성되면 저장할 수 있어요. 계산이나 입력이 빠진 상태는 완성으로 표시하지 않습니다.
        </p>
      )}

      <ul className="flex flex-col gap-1">
        {OFFICIAL_LINKS.map(({ label, url }) => (
          <li key={url}>
            <a
              href={url}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-[var(--accent)] underline decoration-[var(--border)] underline-offset-4 transition-colors hover:decoration-[var(--accent)]"
            >
              {label} →
            </a>
          </li>
        ))}
      </ul>

      <p className="text-xs text-[var(--text-secondary)]">
        예비창업자 상담 가능 범위와 접수 여부는 기관에 확인해야 합니다. 이 자료는 승인·한도·금리를 보장하지 않습니다.
      </p>
    </section>
  );
}
