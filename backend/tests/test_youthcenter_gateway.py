"""온통청년 게이트웨이 파싱 검증 — 실응답(2026-09-16 표본, getPlcy zipCd=27110) 기반 픽스처, 네트워크 미사용."""

from datetime import date, datetime

from apps.funding.adapter.outbound.gateways.youthcenter_gateway import (
    dedup_by_program_id,
    is_startup_policy,
    to_entity,
)

# 실응답 표본 축약 — 파싱에 쓰는 필드는 실제 키·형식 그대로
_ITEM = {
    "plcyNo": "20260810005400113328",
    "plcyNm": "산림산업 창업지원_청년 산림창업가 시너지캠프",
    "plcyKywdNm": "벤처,맞춤형상담서비스",
    "plcyExplnCn": "산림분야 청년들의 창업 역량강화 및 신규시장 진입을 지원하기 위해 ‘2026년 청년 산림창업가 시너지캠프’ 개최",
    "lclsfNm": "일자리",
    "mclsfNm": "창업",
    "sprvsnInstCdNm": "산림청",
    "operInstCdNm": "한국임업진흥원",
    "aplyPrdSeCd": "0057001",
    "aplyYmd": "20260810 ~ 20260825",
    "aplyUrlAddr": "https://forms.gle/mQZEGDmkF9JUAyYS8",
    "refUrlAddr1": "https://www.kofpi.or.kr",
    "sprtTrgtMinAge": "19",
    "sprtTrgtMaxAge": "39",
    "addAplyQlfcCndCn": "",
    "frstRegDt": "2026-08-10 09:38:31",
    "lastMdfcnDt": "2026-08-11 15:44:09",
    "zipCd": "11110,27110,27140,27170,27200,27230,27260,27290,27710,27720",
}


def test_to_entity_maps_real_response_fields():
    entity = to_entity(_ITEM)
    assert entity.program_id == "20260810005400113328"
    assert entity.source == "youthcenter"
    assert entity.title == "산림산업 창업지원_청년 산림창업가 시너지캠프"
    assert entity.org == "산림청"
    assert entity.exec_org == "한국임업진흥원"
    # 신청 URL(forms.gle 등)은 여러 정책이 공유해 funding_program.url 유니크 제약과 충돌 → 온통청년 상세 페이지(정책별 고유)
    assert entity.url == "https://www.youthcenter.go.kr/youthPolicy/ythPlcyTotalSearch/ythPlcyDetail/20260810005400113328"
    assert entity.apply_period == "2026-08-10 ~ 2026-08-25"  # YYYYMMDD → ISO (bizinfo 와 동일 표기)
    assert entity.apply_begin == date(2026, 8, 10)
    assert entity.deadline == date(2026, 8, 25)
    assert entity.field_category == "일자리"
    assert entity.field_subcategory == "창업"
    assert entity.target_text == "만 19~39세"  # 연령 조건 + 추가 자격(빈 값이면 생략)
    assert entity.hashtags == "벤처,맞춤형상담서비스"
    assert entity.summary.startswith("산림분야 청년들의 창업 역량강화")
    assert entity.posted_at == datetime(2026, 8, 10, 9, 38, 31)
    assert entity.source_updated_at == datetime(2026, 8, 11, 15, 44, 9)
    assert entity.is_expired is False


def test_to_entity_always_open_and_target_text_variants():
    always = to_entity({**_ITEM, "aplyPrdSeCd": "0057002", "aplyYmd": "", "addAplyQlfcCndCn": "대구 거주"})
    assert always.apply_period == "상시"
    assert always.deadline is None and always.apply_begin is None
    assert always.target_text == "만 19~39세 · 대구 거주"
    no_age = to_entity({**_ITEM, "sprtTrgtMinAge": "0", "sprtTrgtMaxAge": "0"})  # 실응답: 연령 제한 없는 정책은 0/0
    assert no_age.target_text is None


def test_to_entity_drops_item_without_id():
    assert to_entity({**_ITEM, "plcyNo": ""}) is None


def test_is_startup_policy_filters_on_mid_category():
    assert is_startup_policy(_ITEM) is True
    assert is_startup_policy({**_ITEM, "mclsfNm": "취업"}) is False


def test_dedup_by_program_id_keeps_first_across_district_pages():
    a = to_entity(_ITEM)
    b = to_entity({**_ITEM, "sprvsnInstCdNm": "중복"})  # 다른 구 조회에서 같은 정책이 다시 옴
    c = to_entity({**_ITEM, "plcyNo": "20260101000000000001"})
    merged = dedup_by_program_id([a, b, c])
    assert [e.program_id for e in merged] == ["20260810005400113328", "20260101000000000001"]
    assert merged[0].org == "산림청"
