"""공개 데이터 6종 → regional_indicator 로더 — 순수 함수(이름 정규화·집계·시간대) 검증."""

from apps.indicator.adapter.inbound.cli.load_open_data import (
    HOUR_BANDS,
    count_by_region,
    match_market_region,
    normalize_address,
    normalize_market_name,
    normalize_station_name,
    sum_hour_bands,
)


def test_count_by_region_ignores_unlocated_points():
    assert count_by_region(["A", "B", None, "A"]) == {"A": 2, "B": 1}


def test_station_name_normalization_strips_line_suffix_and_parentheses():
    assert normalize_station_name("대곡(정부대구청사)") == "대곡"
    assert normalize_station_name("명덕1") == "명덕"
    assert normalize_station_name("반월당2") == "반월당"
    assert normalize_station_name("동대구역") == "동대구역"
    assert normalize_station_name("설화명곡") == "설화명곡"
    assert normalize_station_name("대공원") == "수성알파시티"  # 승하차 파일의 옛 역명
    assert normalize_station_name("어린이회관") == "어린이세상"


def test_address_normalization_removes_underground_marker_and_fixes_typo():
    assert normalize_address("대구광역시 수성구 달구벌대로 지하 2672") == "대구광역시 수성구 달구벌대로 2672"
    assert normalize_address("대구광역시 동구 안심로 지하 363(신서동)") == "대구광역시 동구 안심로 363"
    assert normalize_address("대구광역시 수성구 달구벌대호 지하2950") == "대구광역시 수성구 달구벌대로 2950"


def test_market_name_normalization_and_prefix_match():
    markets = {"서문시장": "R1", "칠성시장": "R2", "팔달신시장": "R3"}
    assert normalize_market_name("서문시장 제1지구1층(직물시장)") == "서문시장제1지구1층직물시장"
    assert match_market_region("서문시장2지구 종합상가", markets) == "R1"
    assert match_market_region("팔달신시장", markets) == "R3"
    assert match_market_region("메트로센터(반월당지하쇼핑)", markets) is None


def test_sum_hour_bands_groups_hour_columns():
    row = {f"{h:02d}시-{h+1:02d}시": str(h) for h in range(5, 24)}
    bands = sum_hour_bands(row)
    assert set(bands) == set(HOUR_BANDS)
    assert bands["time_05_10"] == 5 + 6 + 7 + 8 + 9
    assert bands["time_18_24"] == 18 + 19 + 20 + 21 + 22 + 23
