import type { RiskComponents, RiskGrade } from "@/shared/api/types";

const GRADE_LABEL: Record<RiskGrade, string> = {
  red: "진입 고위험",
  yellow: "진입 주의",
  green: "진입 양호",
};

/** grade-badge.tsx의 pill 관행(border+텍스트색)을 재사용 — ok/warn/danger는 fg 대응 토큰이 없어
 *  다크 테마에서 채움 배경 위 흰 글자가 저대비가 되는 문제를 border 방식으로 피한다. */
const GRADE_STYLE: Record<RiskGrade, string> = {
  red: "border border-[var(--danger)] text-[var(--danger)]",
  yellow: "border border-[var(--warn)] text-[var(--warn)]",
  green: "border border-[var(--ok)] text-[var(--ok)]",
};

/** 컴포넌트 기여 점수의 이론적 상한 — 백엔드 risk.py 가중치(closure 0.4·density 0.4·growth 0.2)×100과 동일해야
 *  미니바 길이가 실제 기여 비중을 정확히 나타낸다. */
const COMPONENT_MAX: Record<keyof RiskComponents, number> = {
  closure: 40,
  density: 40,
  growth: 20,
};

const COMPONENT_LABEL: Record<keyof RiskComponents, string> = {
  closure: "폐업률 기여",
  density: "경쟁밀도 기여",
  growth: "신규진입 기여",
};

const COMPONENT_KEYS = Object.keys(COMPONENT_LABEL) as (keyof RiskComponents)[];

/** side-panel의 업종 랭킹 리스트(B유형) 행에도 재사용 — grade→라벨/색 매핑의 단일 원천. */
export function RiskGradeBadge({ grade }: { grade: RiskGrade }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded px-2 py-0.5 text-xs font-medium whitespace-nowrap ${GRADE_STYLE[grade]}`}
    >
      {GRADE_LABEL[grade]}
    </span>
  );
}

interface RiskCardProps {
  score: number;
  grade: RiskGrade;
  components: RiskComponents;
}

export function RiskCard({ score, grade, components }: RiskCardProps) {
  return (
    <div className="mb-5 flex flex-col gap-3 rounded-md border border-[var(--border)] bg-[var(--bg-raised)] p-4">
      <div className="flex items-center justify-between gap-3">
        <span className="text-3xl font-bold tabular-nums text-[var(--text-primary)]">{score}</span>
        <RiskGradeBadge grade={grade} />
      </div>

      <ul className="flex flex-col gap-2">
        {COMPONENT_KEYS.map((key) => (
          <li key={key} className="flex flex-col gap-1">
            <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]">
              <span>{COMPONENT_LABEL[key]}</span>
              <span className="tabular-nums">{components[key]}</span>
            </div>
            <div className="h-1.5 rounded-full bg-[var(--bg-surface)]">
              <div
                className="h-full rounded-full bg-[var(--accent)]"
                style={{ width: `${Math.min(100, Math.max(0, (components[key] / COMPONENT_MAX[key]) * 100))}%` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
