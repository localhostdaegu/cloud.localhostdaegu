"""온통청년(youthcenter.go.kr) 청년정책 Open API Driven Adapter — 대구 청년 창업 정책.

docs/apilist.md §5 (2026-09-16 실호출 확정, 2026-09-17 조회 방식 변경):
- 엔드포인트 youthcenter.go.kr/go/ythip/getPlcy, 키 apiKeyNm, rtnType=json, 페이징 pageNum/pageSize
- 중분류(mclsfNm) "창업" 만 취함 — 기획서 §5.3 "청년(예비·초기창업)" 조건. 서버측 필터 동작
- zipCd 없이 전국 1회 조회(pageSize 500 허용, 전국 창업 340건) 후 항목 zipCd 에 대구 구·군 코드가 있으면 취한다.
  구·군별 8회 조회는 결과가 전부 같은 63건이었고(현재 대구 구 전용 정책 없음), 호출마다 400·403·500 간헐 오류를 만난다.
  전국에는 단일 구·군 전용 정책이 105건 있어 대표 구 1회 조회는 누락 위험 → 클라이언트 필터가 서버 필터와 63건 일치(실측)
- 군위군(27720, 2023 대구 편입)은 전역 DISTRICTS 에서 제외돼 있으나 정책 대상 지역으로는 포함
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
_PAGE_SIZE = 500
_STARTUP_MID_CATEGORY = "창업"
_ATTEMPTS = 4
_ALWAYS_OPEN = "상시"
_GUNWI_ZIP_CODE = "27720"
_DAEGU_ZIP_CODES = frozenset(DISTRICTS) | {_GUNWI_ZIP_CODE}


def is_startup_policy(item: dict) -> bool:
    return (item.get("mclsfNm") or "").strip() == _STARTUP_MID_CATEGORY


def is_daegu_policy(item: dict) -> bool:
    return not _DAEGU_ZIP_CODES.isdisjoint((item.get("zipCd") or "").split(","))


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


class YouthcenterGateway(FundingSearchGatewayPort):
    @staticmethod
    def _get_with_retry(params: dict) -> httpx.Response:
        """타임아웃·HTTP 오류는 지수 백오프 재시도. MOIS·MOLIT 전례와 달리 4xx 도 재시도 —
        유효 키로도 400·403·500 이 간헐 반환되고 재호출하면 200 (2026-09-17 실측)."""
        for attempt in range(_ATTEMPTS):
            try:
                response = httpx.get(_ENDPOINT, params=params, timeout=60)
                response.raise_for_status()
                return response
            except (httpx.HTTPStatusError, httpx.TimeoutException):
                if attempt == _ATTEMPTS - 1:
                    raise
            time.sleep(2**attempt)
        raise RuntimeError("unreachable")

    def _fetch_nationwide(self) -> list[dict]:
        items: list[dict] = []
        page = 1
        while True:
            response = self._get_with_retry(
                {
                    "apiKeyNm": get_settings().youthcenter_api_key,
                    "rtnType": "json",
                    "pageNum": page,
                    "pageSize": _PAGE_SIZE,
                    "mclsfNm": _STARTUP_MID_CATEGORY,
                }
            )
            batch = response.json()["result"].get("youthPolicyList") or []
            items.extend(batch)
            if len(batch) < _PAGE_SIZE:
                return items
            page += 1

    def fetch_all(self) -> list[FundingProgram]:
        programs = []
        for item in self._fetch_nationwide():
            if not (is_startup_policy(item) and is_daegu_policy(item)):
                continue
            entity = to_entity(item)
            if entity is not None:
                programs.append(entity)
        return programs
