"""SgisGeocodeGateway 토큰·좌표변환 단위 검증 — 픽스처 기반 (실호출 없음)."""

import pytest

from apps.store.adapter.outbound.gateways.sgis_geocode_gateway import SgisGeocodeGateway

# 2026-09-19 실응답 축약 — 인증 토큰 4시간(accessTimeout: epoch ms)
_AUTH = {
    "errCd": 0,
    "errMsg": "Success",
    "result": {"accessToken": "test-token", "accessTimeout": "99999999999999"},
}
# "대구광역시 달서구 와룡로 70" 실응답 축약 — x,y 는 EPSG:5179(UTM-K) 문자열
_GEOCODE = {
    "errCd": 0,
    "errMsg": "Success",
    "result": {
        "returncount": "1",
        "totalcount": "1",
        "resultdata": [
            {
                "x": "1093700.96325037",
                "y": "1760716.28320312",
                "sido_nm": "대구광역시",
                "sgg_nm": "달서구",
                "adm_nm": "본리동",
                "road_nm": "와룡로",
            }
        ],
    },
}
# 무결과·주소 형식 불가는 result 없이 errCd 로만 온다 (2026-09-19 실측)
_NO_RESULT = {"errCd": -100, "errMsg": "검색결과가 존재하지 않습니다.", "id": "API_0702"}
_BAD_ADDRESS = {"errCd": -200, "errMsg": "검색할 주소를 확인해주세요", "id": "API_0702"}
_ERROR = {"errCd": -401, "errMsg": "인증 실패", "id": "API_0702"}


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.text = str(payload)

    def json(self) -> dict:
        return self._payload


def _gateway(monkeypatch, payloads: list[dict]) -> tuple[SgisGeocodeGateway, list[dict]]:
    calls: list[dict] = []

    def fake_get(client, url, params):
        calls.append({"url": url, **params})
        return _FakeResponse(payloads[len(calls) - 1])

    monkeypatch.setattr(SgisGeocodeGateway, "_get_with_retry", staticmethod(fake_get))
    monkeypatch.setenv("SGIS_SERVICE_ID", "test-id")
    monkeypatch.setenv("SGIS_SECURITY_KEY", "test-secret")
    return SgisGeocodeGateway(), calls


def test_geocode_converts_utmk_to_wgs84(monkeypatch):
    gateway, calls = _gateway(monkeypatch, [_AUTH, _GEOCODE])

    lng, lat = gateway.geocode("대구광역시 달서구 와룡로 70")

    assert (round(lng, 5), round(lat, 5)) == (128.53752, 35.83849)
    assert calls[0]["url"].endswith("/auth/authentication.json")
    assert calls[1]["accessToken"] == "test-token"
    assert gateway.call_count == 2  # 인증 1 + 지오코딩 1


def test_token_is_reused_until_timeout(monkeypatch):
    gateway, calls = _gateway(monkeypatch, [_AUTH, _GEOCODE, _GEOCODE])

    gateway.geocode("대구광역시 달서구 와룡로 70")
    gateway.geocode("대구광역시 중구 국채보상로 1")

    assert sum(1 for c in calls if "authentication" in c["url"]) == 1
    assert gateway.call_count == 3


@pytest.mark.parametrize("payload", [_NO_RESULT, _BAD_ADDRESS])
def test_geocode_returns_none_when_no_result(monkeypatch, payload):
    # 주소 자체의 실패는 예외가 아니다 — CLI가 실패로 캐시해 재호출을 막는다
    gateway, _ = _gateway(monkeypatch, [_AUTH, payload])

    assert gateway.geocode("대구광역시 없는구 없는로 999") is None


def test_unexpected_error_code_raises(monkeypatch):
    gateway, _ = _gateway(monkeypatch, [_ERROR])

    with pytest.raises(RuntimeError, match="SGIS"):
        gateway.geocode("대구광역시 달서구 와룡로 70")


def test_geocode_normalizes_address(monkeypatch):
    # 괄호 동명·'지하'는 지오코더 입력에서 제거 (load_open_data.normalize_address 재사용)
    gateway, calls = _gateway(monkeypatch, [_AUTH, _GEOCODE])

    gateway.geocode("대구광역시 중구 중앙대로 지하 403 (성내동)")

    assert calls[1]["address"] == "대구광역시 중구 중앙대로 403"


_NO_RESULT = {"errCd": -100, "errMsg": "검색결과가 존재하지 않습니다."}


def test_address_variants_progressively_simplify_lot_number():
    # 2026-09-19 실측: SGIS는 부번이 붙은 지번("송현동 554-2")을 못 찾고 본번("송현동 554")은 찾는다.
    # 인허가 지번은 "0067-0003"처럼 0이 앞에 붙고 층·호가 뒤에 붙는다.
    from apps.store.adapter.outbound.gateways.sgis_geocode_gateway import address_variants

    assert address_variants("대구광역시 중구 동성로2가 0067-0003 1,2층") == [
        "대구광역시 중구 동성로2가 0067-0003 1,2층",
        "대구광역시 중구 동성로2가 67-3",
        "대구광역시 중구 동성로2가 67",
    ]
    assert address_variants("대구광역시 달서구 송현동 554-2") == [
        "대구광역시 달서구 송현동 554-2",
        "대구광역시 달서구 송현동 554",
    ]
    # 도로명·본번만 있는 주소는 더 줄일 게 없다 — 중복 없이 1개
    assert address_variants("대구광역시 달서구 와룡로 70") == ["대구광역리 달서구 와룡로 70".replace("광역리", "광역시")]


def test_geocode_falls_back_through_variants_and_stops_at_first_hit(monkeypatch):
    gateway, calls = _gateway(monkeypatch, [_AUTH, _NO_RESULT, _GEOCODE, _NO_RESULT])

    point = gateway.geocode("대구광역시 달서구 송현동 554-2 2층")

    assert point is not None
    assert [c["address"] for c in calls[1:]] == ["대구광역시 달서구 송현동 554-2 2층", "대구광역시 달서구 송현동 554-2"]


def test_geocode_returns_none_when_every_variant_misses(monkeypatch):
    gateway, calls = _gateway(monkeypatch, [_AUTH, _NO_RESULT, _NO_RESULT, _NO_RESULT])
    assert gateway.geocode("대구광역시 달서구 송현동 554-2 2층") is None
    assert len(calls) == 4  # 인증 1 + 변형 3
