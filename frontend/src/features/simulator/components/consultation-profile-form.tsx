"use client";

import type { ConsultationProfile, PrerequisiteStatus } from "../lib/consultation-draft";

interface ConsultationProfileFormProps {
  value: ConsultationProfile;
  onChange: (next: ConsultationProfile) => void;
}

const FIELD =
  "w-full rounded-md border border-[var(--border)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]";
const LABEL = "flex flex-col gap-1.5 text-xs font-medium tracking-wide text-[var(--text-secondary)]";

/** 사업자등록 여부 3상태 — '모름'은 null 로 남긴다. 아니오로 바꾸면 신청 요건 판단이 틀어진다(§4-2). */
const REGISTERED_CHOICES: { label: string; value: boolean | "unknown" }[] = [
  { label: "예", value: true },
  { label: "아니오", value: false },
  { label: "모름", value: "unknown" },
];

const PREREQUISITE_CHOICES: { label: string; value: PrerequisiteStatus | "" }[] = [
  { label: "선택 안 함", value: "" },
  { label: "아직 시작하지 않음", value: "not_started" },
  { label: "진행 중", value: "in_progress" },
  { label: "발급 완료", value: "done" },
];

/** 창업 단계·시점 입력(§3-3). 외부 조회 없이 사용자가 직접 확인해 입력한다.
 *  모르는 값은 미입력으로 남겨 상담에서 확인할 항목이 되게 한다. */
export function ConsultationProfileForm({ value, onChange }: ConsultationProfileFormProps) {
  const set = <K extends keyof ConsultationProfile>(key: K, v: ConsultationProfile[K]) =>
    onChange({ ...value, [key]: v });

  return (
    <fieldset className="flex flex-col gap-4">
      <legend className="text-sm font-semibold text-[var(--text-primary)]">창업 단계</legend>

      <div className="flex flex-col gap-1.5">
        <span className="text-xs font-medium tracking-wide text-[var(--text-secondary)]">사업자등록을 하셨나요?</span>
        <div className="flex flex-wrap gap-4">
          {REGISTERED_CHOICES.map(({ label, value: choice }) => (
            <label key={label} className="flex items-center gap-2 text-sm text-[var(--text-primary)]">
              <input
                type="radio"
                name="business-registered"
                checked={value.business_registered === choice}
                onChange={() => set("business_registered", choice)}
                className="accent-[var(--accent)]"
              />
              {label}
            </label>
          ))}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {value.business_registered === true ? (
          <label className={LABEL}>
            업력 (개월)
            <input
              type="number"
              inputMode="numeric"
              value={value.business_age_months ?? ""}
              onChange={(e) => set("business_age_months", e.target.value === "" ? null : Number(e.target.value))}
              className={`${FIELD} tabular-nums`}
            />
          </label>
        ) : (
          <label className={LABEL}>
            개업 예정일
            <input
              type="date"
              value={value.opening_date ?? ""}
              onChange={(e) => set("opening_date", e.target.value || null)}
              className={FIELD}
            />
          </label>
        )}

        <label className={LABEL}>
          자금 필요일
          <input
            type="date"
            value={value.funds_needed_date ?? ""}
            onChange={(e) => set("funds_needed_date", e.target.value || null)}
            className={FIELD}
          />
        </label>

        <label className={LABEL}>
          연령 (선택)
          <input
            type="number"
            inputMode="numeric"
            value={value.owner_age ?? ""}
            onChange={(e) => set("owner_age", e.target.value === "" ? null : Number(e.target.value))}
            className={`${FIELD} tabular-nums`}
          />
        </label>

        <label className={LABEL}>
          보증·정책자금 확인서
          <select
            value={value.prerequisite_status ?? ""}
            onChange={(e) => set("prerequisite_status", (e.target.value || null) as PrerequisiteStatus | null)}
            className={FIELD}
          >
            {PREREQUISITE_CHOICES.map(({ label, value: v }) => (
              <option key={label} value={v}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>
    </fieldset>
  );
}
