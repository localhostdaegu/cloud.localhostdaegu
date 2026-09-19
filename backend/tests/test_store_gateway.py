"""MoisPermitGateway 파싱 단위 검증 — 원천 불량 데이터 방어."""

from datetime import date, datetime

from apps.store.adapter.outbound.gateways.mois_permit_gateway import (
    _parse_date,
    _parse_datetime,
    _to_wgs84,
)


def test_parse_date_normal_and_empty():
    assert _parse_date("2026-08-25") == date(2026, 8, 25)
    assert _parse_date("") is None
    assert _parse_date(None) is None


def test_parse_date_clamps_invalid_day():
    # 원천 실데이터에 존재 (2026-08-25 초기적재 크래시 원인): 2006-02-29
    assert _parse_date("2006-02-29") == date(2006, 2, 28)
    assert _parse_date("2021-04-31") == date(2021, 4, 30)


def test_parse_date_garbage_returns_none():
    assert _parse_date("0000-00-00") is None
    assert _parse_date("날짜아님") is None


def test_parse_datetime_clamps_invalid_day():
    assert _parse_datetime("2026-08-25 12:00:00") == datetime(2026, 8, 25, 12, 0)
    assert _parse_datetime("2006-02-29 10:30:00") == datetime(2006, 2, 28, 10, 30)


def test_to_wgs84_rejects_out_of_range():
    assert _to_wgs84(None, None) == (None, None)
    lat, lng = _to_wgs84("344556.519", "264651.134")  # 대구 중구 실좌표
    assert 35.7 < lat < 36.0 and 128.4 < lng < 128.8


def test_to_entity_keeps_road_address_with_lot_fallback():
    # 2026-09-19 실응답(중구 rest_cafes) 축약 — 좌표 없는 인허가(5,558건)를 SGIS로 지오코딩하려면 주소가 있어야 한다
    from apps.store.adapter.outbound.gateways.mois_permit_gateway import MoisPermitGateway
    from apps.store.app.dtos.store_dto import IngestTarget

    target = IngestTarget(industry_id="cafe", slug="rest_cafes", authority_code="3410000", district_code="27110")
    item = {
        "MNG_NO": "1", "BPLC_NM": "유아이유 동성로1호점", "LCPMT_YMD": "2024-01-02", "CLSBIZ_YMD": "",
        "DTL_SALS_STTS_CD": "01", "DTL_SALS_STTS_NM": "영업", "CRD_INFO_X": "", "CRD_INFO_Y": "",
        "DAT_UPDT_PNT": "2026-09-18 22:18:00",
        "ROAD_NM_ADDR": "대구광역시 중구 동성로 34-1, 1,2층 (동성로2가)",
        "LOTNO_ADDR": "대구광역시 중구 동성로2가 0067-0003 1,2층",
    }
    store = MoisPermitGateway._to_entity(item, target)
    assert store.address == "대구광역시 중구 동성로 34-1, 1,2층 (동성로2가)"
    assert (store.lat, store.lng) == (None, None)

    lot_only = MoisPermitGateway._to_entity({**item, "ROAD_NM_ADDR": ""}, target)
    assert lot_only.address == "대구광역시 중구 동성로2가 0067-0003 1,2층"
    assert MoisPermitGateway._to_entity({**item, "ROAD_NM_ADDR": "", "LOTNO_ADDR": None}, target).address is None
