from dataclasses import dataclass

_W_CLOSURE, _W_DENSITY, _W_GROWTH = 0.4, 0.4, 0.2


@dataclass(frozen=True)
class RiskScore:
    score: float
    grade: str
    components: dict[str, float]


def risk_score(closure_pct: float, density_pct: float, growth_pct: float) -> RiskScore:
    c = round(closure_pct * _W_CLOSURE * 100, 1)
    d = round(density_pct * _W_DENSITY * 100, 1)
    g = round(growth_pct * _W_GROWTH * 100, 1)
    total = round(c + d + g, 1)
    grade = "red" if total >= 70 else ("yellow" if total >= 40 else "green")
    return RiskScore(total, grade, {"closure": c, "density": d, "growth": g})


def percentile_rank(value: float, values: list[float]) -> float:
    """values 중 value의 백분위(0~1). 동순위는 중간값(mid-rank) 처리, N=1이면 0.5."""
    n = len(values)
    if n == 0:
        return 0.5
    less = sum(1 for v in values if v < value)
    equal = sum(1 for v in values if v == value)
    return (less + equal / 2) / n
