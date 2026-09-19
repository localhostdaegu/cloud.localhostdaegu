from dataclasses import dataclass

# 프로젝트 합의 기준 시점 — docs/problem.md §3-2
BASE_PERIOD = "202012"

# 연령대 표 (label, age_from 하한, age_from 상한 — None = 상한 없음). 5세 구간의 age_from으로 배정한다.
AGE_BANDS: tuple[tuple[str, int, int | None], ...] = (
    ("0~19세", 0, 19),
    ("20~39세", 20, 39),
    ("40~59세", 40, 59),
    ("60세 이상", 60, None),
)


@dataclass(frozen=True)
class PopulationStat:
    """행정동×연월×성별×연령구간 주민등록 인구 1행 (docs/erd.md §3, 5세 구간 long format)."""

    region_code: str
    period: str  # YYYYMM
    gender: str  # 'M'/'F'
    age_from: int  # 5세 구간 시작: 0,5,…,100
    age_to: int | None  # 구간 끝 (100세 이상 = None)
    population: int


def select_base_period(periods: list[str]) -> str:
    """비교 기준 시점 — 202012가 있으면 202012, 없으면 그 행정동의 가장 이른 시점.

    docs/problem.md §3-2: 2019-12는 행정동 140개만 적재돼 공식 합계보다 부족하므로
    143개 행정동이 모두 있는 2020-12를 프로젝트 기준점으로 합의했다.
    """
    return BASE_PERIOD if BASE_PERIOD in periods else min(periods)


def sum_by_band(stats: list[PopulationStat], period: str) -> list[int]:
    """period의 남+여 인구를 AGE_BANDS 순서대로 합산 — 구간 배정은 age_from 기준."""
    return [
        sum(
            s.population
            for s in stats
            if s.period == period and low <= s.age_from and (high is None or s.age_from <= high)
        )
        for _, low, high in AGE_BANDS
    ]
