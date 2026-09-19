"""NeisAcademyGateway 파싱 단위 검증 — acaInsTiInfo(D10) 실응답 픽스처 기반 (2026-09-19)."""

from datetime import date, datetime

from apps.store.adapter.outbound.gateways.neis_academy_gateway import (
    NeisAcademyGateway,
    _build_courses,
    _parse_fee_items,
)

_DISTRICTS = {"중구": "27110", "달서구": "27290"}

# 2026-09-19 실응답 1행(달서구 교습소) 축약 — 수집 대상 필드만
_ITEM = {
    "ATPT_OFCDC_SC_CODE": "D10",
    "ADMST_ZONE_NM": "달서구",
    "ACA_INSTI_SC_NM": "교습소",
    "ACA_ASNUM": "3500016815",
    "ACA_NM": "루티수학교습소",
    "ESTBL_YMD": "20250514",
    "REG_YMD": "20250514",
    "REG_STTUS_NM": "개원",
    "REALM_SC_NM": "입시.검정 및 보습",
    "LE_ORD_NM": "보통교과",
    "LE_CRSE_LIST_NM": "수학(초5, 초6)",
    "LE_CRSE_NM": "보습",
    "PSNBY_THCC_CNTNT": "수학(초5, 초6):240000, 수학:300000",
    "FA_RDNMA": "대구광역시 달서구 와룡로 70",
    "LOAD_DTM": "20250928",
}


def test_parse_fee_items_keeps_commas_inside_parentheses():
    # 실응답 "수학(초5, 초6):240000, 수학:300000" — 괄호 안 쉼표로 쪼개면 금액이 None으로 유실된다
    assert _parse_fee_items("수학(초5, 초6):240000, 수학:300000, 상담 후 결정") == [
        ("수학(초5, 초6)", 240000),
        ("수학", 300000),
        ("상담 후 결정", None),
    ]
    assert _parse_fee_items("") == []


def test_build_courses_prefers_fee_items_over_curriculum():
    courses = _build_courses("academy:neis:1", _ITEM)
    assert [(c.course_name, c.tuition_fee) for c in courses] == [
        ("수학(초5, 초6)", 240000),
        ("수학", 300000),
    ]
    assert courses[0].course_id == "academy:neis:1:1"


def test_build_courses_falls_back_to_curriculum_list():
    courses = _build_courses("academy:neis:1", {**_ITEM, "PSNBY_THCC_CNTNT": ""})
    assert [(c.course_name, c.tuition_fee) for c in courses] == [("수학(초5, 초6)", None)]


def test_to_record_maps_store_fields_and_subcategory():
    record = NeisAcademyGateway(district_codes=_DISTRICTS)._to_record(_ITEM)
    store = record.store
    assert store.store_id == "academy:neis:3500016815"
    assert store.industry_id == "academy"
    assert store.district_code == "27290"
    assert store.subcategory_id == "academy_exam"  # 입시.검정 및 보습 → dict 디스패치
    assert (store.status_code, store.status_name) == ("open", "개원")
    assert store.open_date == date(2025, 5, 14)
    assert (store.lat, store.lng) == (None, None)  # 원천 좌표 없음 — 지오코딩 후속
    assert store.source_updated_at == datetime(2025, 9, 28)
    assert store.address == "대구광역시 달서구 와룡로 70"  # 지오코딩 입력 — 도로명(FA_RDNMA)


def test_to_record_empty_district_parsed_from_road_address():
    record = NeisAcademyGateway(district_codes=_DISTRICTS)._to_record(
        {**_ITEM, "ADMST_ZONE_NM": "", "FA_RDNMA": "대구광역시 중구 국채보상로 1"}
    )
    assert record.store.district_code == "27110"


def test_to_record_gunwi_skipped_and_counted():
    # 군위군은 district 마스터에 없다 — 버리고 건수 보고 (2026-09-19 사용자 결정, 타 업종과 동일 범위)
    gateway = NeisAcademyGateway(district_codes=_DISTRICTS)
    assert gateway._to_record({**_ITEM, "ADMST_ZONE_NM": "군위군"}) is None
    assert gateway.skipped_districts == {"군위군": 1}
