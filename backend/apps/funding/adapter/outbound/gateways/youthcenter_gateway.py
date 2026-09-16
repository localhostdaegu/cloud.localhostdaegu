"""온통청년(youthcenter.go.kr) 청년정책 Open API Driven Adapter — 대구 청년 창업 정책.

docs/apilist.md §5 (2026-09-16 실호출 확정):
- 엔드포인트 youthcenter.go.kr/go/ythip/getPlcy, 키 apiKeyNm, rtnType=json, 페이징 pageNum/pageSize(100)
- 지역 필터 zipCd = 행안부 시군구 5자리 **단일값** (콤마 다중 미지원) → 대구 8구·군을 순회하고 plcyNo 로 중복 제거
- 전국 정책도 zipCd 에 대구 구·군이 들어 있어 함께 수신됨 (대구 창업자에게 적용 가능하므로 유지)
- 중분류(mclsfNm) "창업" 만 취함 — 기획서 §5.3 "청년(예비·초기창업)" 조건. 서버측 mclsfNm 필터가 동작해(63건)
  구·군당 1페이지로 끝남 — 짧은 시간에 수십 회 호출하면 403(버스트 제한) 이 나므로 구·군 사이에 잠깐 쉰다
"""

import time
from datetime import date, datetime

import httpx

from apps.funding.adapter.outbound.gateways.bizinfo_gateway import parse_period
from apps.funding.app.ports.output.funding_program_port import FundingSearchGatewayPort
from apps.funding.domain.entities.funding_program_entity import FundingProgram
from core.matrix.grid_keymaker_secret_manager import get_settings
from core.matrix.grid_region_config import DISTRICTS

_ENDPOINT = "https://www.youthcenter.go.kr/go/ythip/getPlcy"
# 정책별 고유 상세 페이지 (2026-09-16 확인, 200). 신청 URL(aplyUrlAddr)은 여러 정책이 공유해 url 유니크 제약과 충돌하므로 쓰지 않는다
_DETAIL_URL = "https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch/ythPlcyDetail/"
_PAGE_SIZE = 100
_STARTUP_MID_CATEGORY = "창업"
_PAUSE_BETWEEN_DISTRICTS_SECONDS = 1.0
_ALWAYS_OPEN = "상시"


def is_startup_policy(item: dict) -> bool:
    return (item.get("mclsfNm") or "").strip() == _STARTUP_MID_CATEGORY


def _iso_period(raw: str | None) -> str:
    """'20260810 ~ 20260825' → '2026-08-10 ~ 2026-08-25'. 빈 값(aplyPrdSeCd 상시)은 '상시'."""
    raw = (raw or "").strip()
    if not raw:
        return _ALWAYS_OPEN
    parts = []
    for token in raw.split("~"):
        token = token.strip()
        parts.append(f"{token[:4]}-{token[4:6]}-{token[6:8]}" if len(token) == 8 and token.isdigit() else token)
    return " ~ ".join(parts)


def _target_text(item: dict) -> str | None:
    parts = []
    lo, hi = (item.get("sprtTrgtMinAge") or "").strip(), (item.get("sprtTrgtMaxAge") or "").strip()
    if (lo and lo != "0") or (hi and hi != "0"):  # 0/0 = 연령 제한 없음 (실응답)
        parts.append(f"만 {lo}~{hi}세")
    extra = (item.get("addAplyQlfcCndCn") or "").strip()
    if extra:
        parts.append(extra)
    return " · ".join(parts) or None


def _url(item: dict) -> str:
    return f"{_DETAIL_URL}{item['plcyNo'].strip()}"


def _parse_dt(raw: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat(raw) if raw else None
    except ValueError:
        return None


def to_entity(item: dict) -> FundingProgram | None:
    program_id = (item.get("plcyNo") or "").strip()
    if not program_id:
        return None
    apply_period = _iso_period(item.get("aplyYmd"))
    apply_begin, deadline = parse_period(apply_period)
    return FundingProgram(
        program_id=program_id,
        source="youthcenter",
        title=(item.get("plcyNm") or "").strip(),
        org=(item.get("sprvsnInstCdNm") or "").strip(),
        url=_url(item),
        apply_period=apply_period,
        exec_org=(item.get("operInstCdNm") or "").strip() or None,
        field_category=(item.get("lclsfNm") or "").strip() or None,
        field_subcategory=(item.get("mclsfNm") or "").strip() or None,
        target_text=_target_text(item),
        hashtags=(item.get("plcyKywdNm") or "").strip() or None,
        apply_begin=apply_begin,
        deadline=deadline,
        summary=(item.get("plcyExplnCn") or "").strip() or None,
        posted_at=_parse_dt(item.get("frstRegDt")),
        source_updated_at=_parse_dt(item.get("lastMdfcnDt")),
    )


def dedup_by_program_id(programs: list[FundingProgram]) -> list[FundingProgram]:
    seen: set[str] = set()
    unique = []
    for program in programs:
        if program.program_id not in seen:
            seen.add(program.program_id)
            unique.append(program)
    return unique


class YouthcenterGateway(FundingSearchGatewayPort):
    def __init__(self, district_codes: tuple[str, ...] = tuple(DISTRICTS)) -> None:
        self._district_codes = district_codes

    def _fetch_district(self, zip_code: str) -> list[dict]:
        items: list[dict] = []
        page = 1
        while True:
            response = httpx.get(
                _ENDPOINT,
                params={
                    "apiKeyNm": get_settings().youthcenter_api_key,
                    "rtnType": "json",
                    "pageNum": page,
                    "pageSize": _PAGE_SIZE,
                    "zipCd": zip_code,
                    "mclsfNm": _STARTUP_MID_CATEGORY,
                },
                timeout=60,
            )
            response.raise_for_status()
            batch = response.json()["result"].get("youthPolicyList") or []
            items.extend(batch)
            if len(batch) < _PAGE_SIZE:
                return items
            page += 1

    def fetch_all(self) -> list[FundingProgram]:
        programs = []
        for index, zip_code in enumerate(self._district_codes):
            if index:
                time.sleep(_PAUSE_BETWEEN_DISTRICTS_SECONDS)
            for item in self._fetch_district(zip_code):
                if not is_startup_policy(item):
                    continue
                entity = to_entity(item)
                if entity is not None:
                    programs.append(entity)
        return dedup_by_program_id(programs)
