"""시드 파일 검증 — 출처 필수·계층 유효·업종 연결 무결성·대구 타임라인 실값 (네트워크·DB 미사용)."""

from datetime import date

from apps.shock.adapter.outbound.gateways.shock_seed_gateway import ShockSeedGateway
from apps.shock.domain.value_objects.shock_layer import ShockLayer

# master 시드와 동일한 업종 11종 (apps/master seed_master)
_INDUSTRY_IDS = {
    "restaurant", "cafe", "convenience_store", "hair_salon", "karaoke", "pc_bang",
    "gym", "billiard", "real_estate", "academy", "childcare",
}


def _events():
    return ShockSeedGateway().fetch_events()


def test_every_seed_row_has_source_url_and_valid_layer():
    events = _events()
    assert events
    for event in events:
        assert event.source  # 출처 명시 — 과업 요구사항
        assert (event.source_url or "").startswith("http")  # 행마다 확인 가능한 출처 URL
        assert event.layer in ShockLayer
        for impact in event.industry_impacts:
            assert impact.industry_id in _INDUSTRY_IDS  # 조인 무결성 (industry FK 대상)


def test_seed_has_no_seoul_metropolitan_rows():
    """서비스 지역은 대구 — 서울·수도권 단계 행을 싣지 않는다."""
    for event in _events():
        assert event.scope in {"전국", "대구"}, event.event_id
        assert "seoul" not in event.event_id


def test_seed_marks_daegu_outbreak_and_special_disaster_zone():
    by_id = {e.event_id: e for e in _events()}
    outbreak = by_id["daegu-outbreak-20200218"]
    assert outbreak.start_date == date(2020, 2, 18)  # 대구 첫 확진(31번 환자)
    assert outbreak.end_date == date(2020, 4, 9)  # 2020-04-10 신규 확진 0명(52일 만) 전날
    assert outbreak.layer == ShockLayer.REGIONAL
    assert outbreak.scope == "대구"
    disaster_zone = by_id["daegu-special-disaster-zone-20200315"]
    assert disaster_zone.start_date == date(2020, 3, 15)
    assert disaster_zone.scope == "대구"


def test_seed_covers_pre_api_distancing_gap_for_daegu():
    """API 커버리지(2020-12-08~) 이전 대구 적용 거리두기 구간을 공백 없이 보충한다."""
    pre_api = sorted(
        (
            e for e in _events()
            if e.event_id.startswith("covid-distancing-") and e.start_date < date(2020, 12, 8)
        ),
        key=lambda e: e.start_date,
    )
    assert pre_api[0].start_date == date(2020, 3, 22)  # 강력한 사회적 거리두기 시작
    for prev, nxt in zip(pre_api, pre_api[1:]):
        assert prev.end_date is not None
        assert (nxt.start_date - prev.end_date).days == 1
    assert pre_api[-1].end_date == date(2020, 12, 7)  # API 시작 전날까지
    levels = {e.start_date: e.name for e in pre_api}
    assert "2단계" in levels[date(2020, 8, 23)]  # 전국 2단계 확대(비수도권 포함)
    assert "1단계" in levels[date(2020, 10, 12)]
    assert "1.5단계" in levels[date(2020, 12, 1)]  # 대구·경북 1.5단계 격상


def test_distancing_rows_include_restaurant_impact():
    """일반음식점은 매장 취식·영업시간 제한의 직접 대상 — 거리두기 행마다 영향 업종에 포함."""
    distancing = [e for e in _events() if e.event_id.startswith(("covid-distancing-", "covid-reopening-"))]
    assert distancing
    for event in distancing:
        assert "restaurant" in {i.industry_id for i in event.industry_impacts}, event.event_id


def test_minimum_wage_rows_2019_to_2026_with_real_amounts():
    by_id = {e.event_id: e for e in _events()}
    for year in range(2019, 2027):
        assert f"min-wage-{year}" in by_id
    assert "8,350" in by_id["min-wage-2019"].name
    assert "10,320" in by_id["min-wage-2026"].name
    assert by_id["min-wage-2026"].start_date == date(2026, 1, 1)


def test_relief_fund_rows_carry_distortion_warning():
    """지원금 왜곡 주의(§5.2 ⚠️)를 description에 담아 후속 분석이 참조한다."""
    events = [e for e in _events() if "지원금" in e.name or "손실보상" in e.name]
    assert events
    for event in events:
        assert "지연" in (event.description or "")
        assert len(event.industry_impacts) == len(_INDUSTRY_IDS)  # 전 업종 연결
