import re
from dataclasses import dataclass, field
from apps.intent.domain.landmarks import LANDMARKS, INDUSTRY_SYNONYMS

_BUDGET = re.compile(r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(억|천만|천|만)?\s*원?")

@dataclass(frozen=True)
class Intent:
    intent_type: str
    district_code: str | None = None
    region_name: str | None = None
    industry_slug: str | None = None
    budget_krw: int | None = None
    missing: list[str] = field(default_factory=list)

def _parse_budget(text: str) -> int | None:
    m = _BUDGET.search(text.replace(",", ""))
    if not m: return None
    num, unit = float(m.group(1)), m.group(2)
    scale = {"억": 100_000_000, "천만": 10_000_000, "천": 10_000_000, "만": 10_000}.get(unit)
    if scale is None: return None                      # 단위 없는 맨숫자는 무시 (오탐 방지)
    return int(num * scale)

def parse_intent(text: str, dongs: dict[str, str], gus: dict[str, str]) -> Intent:
    district, region_name = None, None
    for name, (dong, code) in LANDMARKS.items():       # 랜드마크 우선
        if name in text: district, region_name = code, dong; break
    if district is None:
        for dong, code in dongs.items():
            if dong in text: district, region_name = code, dong; break
    if district is None:
        for gu, code in gus.items():
            if gu in text: district = code; break
    industry = next((slug for word, slug in INDUSTRY_SYNONYMS.items() if word in text), None)
    budget = _parse_budget(text)

    missing = [k for k, v in (("region", district), ("industry", industry), ("budget", budget)) if v is None]
    if district and industry: itype = "A"
    elif district: itype = "B"
    else: itype = "C"
    return Intent(itype, district, region_name, industry, budget, missing)
