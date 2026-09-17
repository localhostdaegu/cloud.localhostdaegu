"""온통청년 게이트웨이 파싱 검증 — 실응답(2026-09-16 표본, getPlcy zipCd=27110) 기반 픽스처, 네트워크 미사용."""

from datetime import date, datetime

import httpx

from apps.funding.adapter.outbound.gateways.youthcenter_gateway import (
    is_daegu_policy,
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


def test_is_daegu_policy_matches_any_daegu_zip_including_gunwi():
    assert is_daegu_policy(_ITEM) is True  # 전국 정책 (zipCd 에 대구 구·군 포함)
    assert is_daegu_policy({**_ITEM, "zipCd": "27260"}) is True  # 수성구 전용
    assert is_daegu_policy({**_ITEM, "zipCd": "27720"}) is True  # 군위군 전용 (2023 대구 편입)
    assert is_daegu_policy({**_ITEM, "zipCd": "11110,11140"}) is False  # 타 지역 전용
    assert is_daegu_policy({**_ITEM, "zipCd": ""}) is False


def test_fetch_all_single_nationwide_call_filters_daegu(monkeypatch):
    """zipCd 없이 전국 1회 조회(pageSize 500) → 대구 구·군 코드 포함 항목만. 2026-09-17 실측: 전국 340 → 대구 63(서버 필터와 일치)."""
    from apps.funding.adapter.outbound.gateways import youthcenter_gateway as module

    daegu_only = {**_ITEM, "plcyNo": "20260101000000000001", "zipCd": "27290"}
    seoul_only = {**_ITEM, "plcyNo": "20260101000000000002", "zipCd": "11110"}
    calls = []

    def fake_get(params):
        calls.append(params)
        return httpx.Response(200, json={"result": {"youthPolicyList": [_ITEM, daegu_only, seoul_only]}})

    monkeypatch.setattr(module.YouthcenterGateway, "_get_with_retry", staticmethod(fake_get))
    monkeypatch.setattr(module, "get_settings", lambda: type("S", (), {"youthcenter_api_key": "k"})())

    programs = module.YouthcenterGateway().fetch_all()

    assert [p.program_id for p in programs] == ["20260810005400113328", "20260101000000000001"]
    assert len(calls) == 1
    assert "zipCd" not in calls[0] and calls[0]["pageSize"] == 500 and calls[0]["mclsfNm"] == "창업"


def test_fetch_retries_transient_http_errors(monkeypatch):
    """실운영 2026-09-17: 유효 키인데도 400(27140)·500(27230)·403(버스트)이 간헐 반환, 재호출 시 200 → 4xx 포함 재시도."""
    from apps.funding.adapter.outbound.gateways import youthcenter_gateway as module

    request = httpx.Request("GET", module._ENDPOINT)
    ok = httpx.Response(200, json={"result": {"youthPolicyList": [_ITEM]}}, request=request)
    responses = [httpx.Response(400, request=request), httpx.Response(500, request=request), ok]
    monkeypatch.setattr(module.httpx, "get", lambda *args, **kwargs: responses.pop(0))
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(module, "get_settings", lambda: type("S", (), {"youthcenter_api_key": "k"})())

    assert [p.program_id for p in module.YouthcenterGateway().fetch_all()] == ["20260810005400113328"]
    assert responses == []
