"""나이스(NEIS) 교육정보 개방포털 학원교습소정보(acaInsTiInfo) Driven Adapter.

- 엔드포인트: open.neis.go.kr/hub/acaInsTiInfo?KEY=&Type=json&ATPT_OFCDC_SC_CODE=D10&pIndex=&pSize=
  (2026-09-19 실호출 검증 — 대구교육청 D10 8,016건, 1회 1,000건 × 9페이지)
- 서울 OA-20528(neisAcademyInfo)의 원본 — 필드명만 다르고 구조는 같아 파싱 보조 함수는 서울 게이트웨이를 재사용
- 키 없이는 1회 5건으로 잘린다(NEIS 정책) — NEIS_API_KEY 필수. 인증 실패는 acaInsTiInfo 없이 RESULT만 온다
- 좌표 없음: lat/lng NULL 적재 → 지오코딩 후속 대상. 구·군은 ADMST_ZONE_NM ↔ district.name 매핑,
  군위군은 district 마스터에 없어 skipped_districts로 버린다(인허가·편의점·부동산·어린이집과 동일 범위)
- 현행 스냅샷만 제공 → 매 실행 전량 수집, LOAD_DTM을 source_updated_at으로 보존
"""

import time
from collections.abc import Iterator
from datetime import date, datetime

import httpx

from apps.store.adapter.outbound.gateways.seoul_academy_gateway import (
    _FIELD_SUBCATEGORIES,
    _STATUS_CODES,
    _parse_ymd,
)
from apps.store.app.dtos.academy_course_dto import AcademyRecord
from apps.store.app.ports.output.academy_course_port import AcademyGatewayPort
from apps.store.domain.entities.academy_course_entity import AcademyCourse
from apps.store.domain.entities.store_entity import Store
from core.matrix.grid_http_error_translator import translate_http_errors
from core.matrix.grid_keymaker_secret_manager import get_settings
from core.matrix.grid_region_config import REGION_NAME

_BASE_URL = "https://open.neis.go.kr/hub/acaInsTiInfo"
_SERVICE = "acaInsTiInfo"
_ATPT_OFCDC_SC_CODE = "D10"  # 대구광역시교육청
_PAGE_SIZE = 1000  # 인증키 사용 시 최대값 (2026-09-19 실측)
_INDUSTRY_ID = "academy"


def _split_top_level(text: str) -> list[str]:
    """괄호 밖 쉼표로만 분리 — NEIS 과정명은 "수학(초5, 초6)"처럼 괄호 안에 쉼표를 품는다 (2026-09-19 실측)."""
    chunks: list[str] = []
    depth = 0
    current: list[str] = []
    for char in text:
        if char in "([":
            depth += 1
        elif char in ")]":
            depth = max(depth - 1, 0)
        if char == "," and depth == 0:
            chunks.append("".join(current))
            current = []
        else:
            current.append(char)
    chunks.append("".join(current))
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _parse_fee_items(text: str) -> list[tuple[str, int | None]]:
    """수강료 내용(PSNBY_THCC_CNTNT) → [(항목명, 금액)] — "초등영어:150000, 수학(초5, 초6):240000" 형식.

    금액이 숫자가 아니면 항목 전체를 이름으로 보존하고 금액은 None (서울 게이트웨이와 같은 규칙).
    """
    items: list[tuple[str, int | None]] = []
    for chunk in _split_top_level(text):
        name, _, amount = chunk.rpartition(":")
        amount = amount.strip().replace(",", "")
        if name.strip() and amount.isdigit():
            items.append((name.strip(), int(amount)))
        else:
            items.append((chunk, None))
    return items


def _build_courses(store_id: str, item: dict) -> list[AcademyCourse]:
    """수강료 공개 항목(PSNBY_THCC_CNTNT) 우선, 없으면 교습과정 목록(LE_CRSE_LIST_NM → LE_CRSE_NM) — 원문 보존."""
    pairs = _parse_fee_items(item.get("PSNBY_THCC_CNTNT") or "")
    if not pairs:
        names = _split_top_level(item.get("LE_CRSE_LIST_NM") or "")
        if not names and (item.get("LE_CRSE_NM") or "").strip():
            names = [item["LE_CRSE_NM"].strip()]
        pairs = [(name, None) for name in dict.fromkeys(names)]  # 순서 유지 중복 제거
    return [
        AcademyCourse(
            course_id=f"{store_id}:{index}",
            store_id=store_id,
            course_name=name,
            tuition_fee=fee,
        )
        for index, (name, fee) in enumerate(pairs, start=1)
    ]


class NeisAcademyGateway(AcademyGatewayPort):
    def __init__(self, district_codes: dict[str, str]) -> None:
        self._district_codes = district_codes  # 구·군명(ADMST_ZONE_NM) → district_code
        self.call_count = 0  # 호출량 규율 — CLI가 로그로 보고
        self.skipped_districts: dict[str, int] = {}  # 구 미매칭으로 버린 행

    def iter_academies(self) -> Iterator[AcademyRecord]:
        params = {
            "KEY": get_settings().neis_api_key,
            "Type": "json",
            "ATPT_OFCDC_SC_CODE": _ATPT_OFCDC_SC_CODE,
            "pSize": _PAGE_SIZE,
        }
        page = 1
        with httpx.Client(timeout=httpx.Timeout(60, connect=10)) as client:
            while True:
                response = self._get_with_retry(client, _BASE_URL, {**params, "pIndex": page})
                self.call_count += 1
                payload = response.json().get(_SERVICE)
                if payload is None:  # 인증 실패·요청 오류는 서비스 키 없이 RESULT만 옴
                    raise RuntimeError(f"neis academy API 오류: {response.text[:300]}")
                head, body = payload[0]["head"], payload[1]
                for item in body.get("row") or []:
                    record = self._to_record(item)
                    if record is not None:
                        yield record
                if page * _PAGE_SIZE >= int(head[0]["list_total_count"]):
                    return
                page += 1

    @staticmethod
    def _get_with_retry(
        client: httpx.Client, url: str, params: dict, attempts: int = 3
    ) -> httpx.Response:
        """타임아웃·5xx는 지수 백오프 재시도, 4xx는 즉시 전파 (MOIS 게이트웨이 전례).
        전파 오류는 KEY 쿼리가 빠진 메시지로 번역한다."""
        with translate_http_errors():
            for attempt in range(attempts):
                try:
                    response = client.get(url, params=params)
                    response.raise_for_status()
                    return response
                except httpx.HTTPStatusError as error:
                    if error.response.status_code < 500 or attempt == attempts - 1:
                        raise
                except httpx.TimeoutException:
                    if attempt == attempts - 1:
                        raise
                time.sleep(2**attempt)
        raise RuntimeError("unreachable")

    def _to_record(self, item: dict) -> AcademyRecord | None:
        district_name = (item.get("ADMST_ZONE_NM") or "").strip()
        if not district_name:  # 구·군명 공란 방어 — 도로명주소 두 번째 어절 (서울 전례)
            parts = (item.get("FA_RDNMA") or "").split()
            if len(parts) >= 2 and parts[0].startswith(REGION_NAME):
                district_name = parts[1]
        district_code = self._district_codes.get(district_name)
        if district_code is None:  # 구 매칭 불가(군위군 등) — 버리고 건수 보고
            self.skipped_districts[district_name] = self.skipped_districts.get(district_name, 0) + 1
            return None
        store_id = f"{_INDUSTRY_ID}:neis:{item['ACA_ASNUM']}"  # 학원지정번호
        status_name = (item.get("REG_STTUS_NM") or "").strip()
        load_date = _parse_ymd(item.get("LOAD_DTM")) or date.today()
        store = Store(
            store_id=store_id,
            name=(item.get("ACA_NM") or "").strip(),
            industry_id=_INDUSTRY_ID,
            district_code=district_code,
            open_date=_parse_ymd(item.get("ESTBL_YMD")) or _parse_ymd(item.get("REG_YMD")),
            close_date=None,  # 원천에 폐원일자 필드 없음 — 상태는 status로 보존
            status_code=_STATUS_CODES.get(status_name, status_name),
            status_name=status_name,
            address=(item.get("FA_RDNMA") or "").strip() or None,  # 도로명 — SGIS 지오코딩 입력
            lat=None,  # 원천에 좌표 없음 — 지오코딩 후속 대상
            lng=None,
            source_updated_at=datetime(load_date.year, load_date.month, load_date.day),
            subcategory_id=_FIELD_SUBCATEGORIES.get((item.get("REALM_SC_NM") or "").strip()),
        )
        return AcademyRecord(store=store, courses=_build_courses(store_id, item))
