import type { RiskComponents, RiskGrade } from "@/shared/api/types";

/** 점수는 같은 업종·연도 안에서 동네끼리 매긴 상대 순위다 — 실패 확률이나 진입 가부 판정이 아니므로
 *  "진입 고위험/양호" 같은 절대 표현을 쓰지 않는다(OPEN-009). */
const GRADE_LABEL: Record<RiskGrade, string> = {
  red: "상대 위험 높음",
  yellow: "상대 위험 중간",
  green: "상대 위험 낮음",
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
  closure: "폐업률 순위",
  density: "점포 수 순위",
  growth: "점포 증감 순위",
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
  /** 같은 업종에서 점수가 높은 순으로 몇 번째 동인지 — 있으면 점수 아래에 풀어 쓴다. */
  rank?: { position: number; total: number };
}

export function RiskCard({ score, grade, components, rank }: RiskCardProps) {
  return (
    <div className="mb-5 flex flex-col gap-3 rounded-md border border-[var(--border)] bg-[var(--bg-raised)] p-4">
      <div className="flex items-center justify-between gap-3">
        <span className="text-3xl font-bold tabular-nums text-[var(--text-primary)]">{score}</span>
        <RiskGradeBadge grade={grade} />
      </div>
      <p className="text-[11px] leading-snug text-[var(--text-secondary)]">
        {rank && `대구 ${rank.total}개 동 가운데 ${rank.position}번째로 높아요. `}
        동네끼리 비교한 상대 점수이며 실패 확률이 아닙니다.
      </p>

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
