"""거리두기 게이트웨이 파싱 검증 — ODMS_COVID_12 실응답 필드 형식 픽스처, 네트워크 미사용.

지역 필드는 data.go.kr 15098772 명세 기준(seoLvl 서울, dagLvl 대구 …).
"""

from datetime import date

from apps.shock.adapter.outbound.gateways.covid_distancing_gateway import (
    compress_to_events,
)
from apps.shock.domain.value_objects.shock_layer import Severity, ShockLayer

# 파싱에 쓰는 필드는 실제 키·형식 그대로 (단계 문자열, "null" 문자열 비고).
# 서울(seoLvl)은 대구와 다르게 움직인다 — 게이트웨이는 대구(dagLvl)만 따라야 한다.
_ITEMS = [
    {"stdDay": "2021-02-14", "dagLvl": "2.5", "seoLvl": "2.5", "socdisLvl": "5단계", "dagRmk": "null"},
    {"stdDay": "2021-02-15", "dagLvl": "2.0", "seoLvl": "2.5", "socdisLvl": "5단계", "dagRmk": "null"},
    {"stdDay": "2021-02-16", "dagLvl": "2.0", "seoLvl": "1.5", "socdisLvl": "5단계", "dagRmk": "null"},
    # 정렬 보장 없음 — 게이트웨이가 날짜순 정렬 후 압축해야 한다
    {"stdDay": "2021-02-13", "dagLvl": "2.5", "seoLvl": "2.0", "socdisLvl": "5단계", "dagRmk": "null"},
]


def test_compress_daily_rows_into_daegu_level_intervals():
    events = compress_to_events(_ITEMS)
    assert len(events) == 2
    first, second = events
    assert first.start_date == date(2021, 2, 13)
    assert first.end_date == date(2021, 2, 14)
    assert second.start_date == date(2021, 2, 15)
    assert second.end_date == date(2021, 2, 16)


def test_event_fields_are_deterministic_daegu_and_sourced():
    events = compress_to_events(_ITEMS)
    first, second = events
    assert first.event_id == "covid-distancing-daegu-20210213"  # 결정적 ID — 재적재 멱등
    assert first.layer == ShockLayer.POLICY
    assert "대구 2.5단계" in first.name
    assert "2단계" in second.name  # 2.0 → "2" 표기
    assert first.scope == "대구"
    assert "dagLvl" in (first.description or "")
    assert "15098772" in first.source
    assert first.source_url


def test_severity_mapping_follows_brainstorming_5_2():
    """노래방·PC방·헬스장·당구장 ≫ 카페·일반음식점 (brainstorming §5.2 ①계층 표)."""
    events = compress_to_events(_ITEMS)
    first, second = events
    strong = {i.industry_id: i.severity for i in first.industry_impacts}  # 2.5단계
    weak = {i.industry_id: i.severity for i in second.industry_impacts}  # 2단계
    for leisure in ("karaoke", "pc_bang", "gym", "billiard"):
        assert strong[leisure] == Severity.CRITICAL
        assert weak[leisure] == Severity.HIGH
    for dining in ("cafe", "restaurant"):
        assert strong[dining] == Severity.HIGH
        assert weak[dining] == Severity.MEDIUM


def test_empty_items_yield_no_events():
    assert compress_to_events([]) == []
