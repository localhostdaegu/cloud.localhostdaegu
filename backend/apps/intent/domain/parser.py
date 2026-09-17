import re
from dataclasses import dataclass, field
from apps.intent.domain.landmarks import LANDMARKS, INDUSTRY_SYNONYMS

_AMOUNT = re.compile(r"(\d+(?:\.\d+)?)\s*(억|천만|천|만)")    # 단위 없는 맨숫자(2층 등)는 금액 아님
_SCALE = {"억": 100_000_000, "천만": 10_000_000, "천": 10_000_000, "만": 10_000}

@dataclass(frozen=True)
class Intent:
    intent_type: str
    district_code: str | None = None
    region_name: str | None = None
    industry_id: str | None = None
    budget_krw: int | None = None
    missing: list[str] = field(default_factory=list)

def _parse_budget(text: str) -> int | None:
    """단위 붙은 첫 금액부터, 공백만 사이에 두고 이어지는 더 작은 단위를 합산 (1억 5천만 → 1.5억)."""
    cleaned = text.replace(",", "")
    total, prev_end, prev_scale = None, 0, 0
    for m in _AMOUNT.finditer(cleaned):
        scale = _SCALE[m.group(2)]
        if total is not None and (cleaned[prev_end:m.start()].strip() or scale >= prev_scale):
            break
        total = (total or 0) + int(float(m.group(1)) * scale)
        prev_end, prev_scale = m.end(), scale
    return total

def _longest_first(names: dict) -> list:
    """부분 문자열 오매칭 방지 — '달서구'가 '서구'보다 먼저 검사되도록 긴 이름 우선."""
    return sorted(names.items(), key=lambda item: len(item[0]), reverse=True)

def parse_intent(text: str, dongs: dict[str, str], gus: dict[str, str]) -> Intent:
    district, region_name = None, None
    for name, (dong, code) in _longest_first(LANDMARKS):       # 랜드마크 우선
        if name in text: district, region_name = code, dong; break
    if district is None:
        for dong, code in _longest_first(dongs):
            if dong in text: district, region_name = code, dong; break
    if district is None:
        for gu, code in _longest_first(gus):
            if gu in text: district = code; break
    industry = next((slug for word, slug in INDUSTRY_SYNONYMS.items() if word in text), None)
    budget = _parse_budget(text)

    missing = [k for k, v in (("region", district), ("industry", industry), ("budget", budget)) if v is None]
    if district and industry: itype = "A"
    elif district: itype = "B"
    else: itype = "C"
    return Intent(itype, district, region_name, industry, budget, missing)
