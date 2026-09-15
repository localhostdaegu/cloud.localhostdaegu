"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { INDUSTRY_LABELS } from "@/shared/daegu";
import { parseIntent, type ParseIntentResult } from "../api";
import { intentToUrl } from "../lib/intent-url";

const EXAMPLE_CHIPS = ["서문시장 근처 카페, 예산 5천", "동성로에 미용실", "예산 5천이면 뭐 하지?"];

const CHIP =
  "rounded-full border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-1.5 text-sm text-[var(--text-secondary)] transition-colors hover:border-[var(--accent)] hover:text-[var(--text-primary)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]";

export function ChatLanding() {
  const router = useRouter();
  const [text, setText] = useState("");
  // industry가 missing인데 district는 확정된 응답 — 업종 칩으로 되물어 재제출 없이 바로 라우팅한다.
  const [awaitingIndustry, setAwaitingIndustry] = useState<ParseIntentResult | null>(null);

  const mutation = useMutation({
    mutationFn: parseIntent,
    onSuccess: (result) => {
      if (result.missing.includes("industry") && result.district_code) {
        setAwaitingIndustry(result);
        return;
      }
      router.push(intentToUrl(result));
    },
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || mutation.isPending) return;
    setAwaitingIndustry(null);
    mutation.mutate(trimmed);
  }

  function handlePickIndustry(slug: string) {
    if (!awaitingIndustry) return;
    router.push(intentToUrl({ ...awaitingIndustry, industry_slug: slug }));
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6 px-5 py-10">
      <h1 className="text-2xl font-semibold tracking-tight text-[var(--text-primary)]">무엇을 알아볼까요?</h1>

      <form onSubmit={handleSubmit} className="flex w-full max-w-xl flex-col items-center gap-3">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="예: 서문시장 근처 카페, 예산 5천"
          className="w-full rounded-md border border-[var(--border)] bg-[var(--bg-surface)] px-4 py-3 text-base text-[var(--text-primary)] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
        />
        <button
          type="submit"
          disabled={!text.trim() || mutation.isPending}
          className="rounded-md bg-[var(--accent)] px-5 py-2.5 text-sm font-semibold text-[var(--accent-fg)] transition-opacity hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)] active:translate-y-px disabled:pointer-events-none disabled:opacity-50"
        >
          {mutation.isPending ? "찾는 중…" : "찾아보기"}
        </button>
      </form>

      <div className="flex flex-wrap justify-center gap-2">
        {EXAMPLE_CHIPS.map((chip) => (
          <button key={chip} type="button" onClick={() => setText(chip)} className={CHIP}>
            {chip}
          </button>
        ))}
      </div>

      {mutation.isError && (
        <p role="alert" className="text-sm text-[var(--danger)]">
          요청을 처리하지 못했습니다. 다시 시도해 주세요.
        </p>
      )}

      {awaitingIndustry && (
        <div className="flex flex-col items-center gap-2">
          <span className="text-sm text-[var(--text-secondary)]">어떤 업종을 찾으세요?</span>
          <div className="flex flex-wrap justify-center gap-2">
            {Object.entries(INDUSTRY_LABELS).map(([slug, label]) => (
              <button key={slug} type="button" onClick={() => handlePickIndustry(slug)} className={CHIP}>
                {label}
              </button>
            ))}
          </div>
        </div>
      )}

      <Link
        href="/map"
        className="text-sm text-[var(--text-secondary)] transition-colors hover:text-[var(--accent)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
      >
        지도에서 직접 둘러보기 →
      </Link>
    </div>
  );
}
