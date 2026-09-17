"""외부 API 키 노출 차단 검증 — httpx 오류 메시지(전체 URL·쿼리스트링)에 키가 실려 크론 로그로 새던 문제.

게이트웨이 경계에서 상태코드·경로만 남긴 예외로 바꿔 올리는지 확인한다 (MockTransport, 네트워크 미사용).
재시도 헬퍼가 연결·읽기 오류(ConnectError·ReadError)도 재시도하는지 함께 검증.
"""

import traceback

import httpx
import pytest

from apps.funding.adapter.outbound.gateways import bizinfo_gateway, youthcenter_gateway
from apps.rent.adapter.outbound.gateways import rone_gateway
from apps.store.adapter.outbound.gateways import mois_permit_gateway
from apps.store.app.dtos.store_dto import IngestTarget

_KEY = "SECRET-KEY-DO-NOT-LOG"
_REAL_CLIENT = httpx.Client
_TARGET = IngestTarget(
    industry_id="karaoke", slug="karaoke_rooms", district_code="27110", authority_code="3410000"
)
_MOIS_EMPTY = {"response": {"body": {"items": {"item": []}, "totalCount": 0}}}


def _settings(field: str):
    return lambda: type("S", (), {field: _KEY})()


def _mock_client(handler):
    return _REAL_CLIENT(transport=httpx.MockTransport(handler))


def _patch_module_get(monkeypatch, module, handler) -> None:
    """httpx.get(url, params=, timeout=) 을 MockTransport 클라이언트로 대체 — 실제 요청 URL·예외 형식 유지."""
    monkeypatch.setattr(
        module.httpx, "get", lambda url, params=None, timeout=None: _mock_client(handler).get(url, params=params)
    )


def _patch_client(monkeypatch, module, handler) -> None:
    monkeypatch.setattr(module.httpx, "Client", lambda **kwargs: _mock_client(handler))


def _status(code: int):
    return lambda request: httpx.Response(code, request=request)


def _connect_error(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("connection refused", request=request)


def _assert_key_hidden(error: BaseException) -> None:
    logged = "".join(traceback.format_exception(error))  # 수집기 CLI 가 traceback.print_exc 로 남기는 형태
    assert _KEY not in logged
    assert "?" not in str(error)  # 쿼리스트링 통째로 제거


def test_bizinfo_http_error_hides_key(monkeypatch):
    monkeypatch.setattr(bizinfo_gateway, "get_settings", _settings("bizinfo_api_key"))
    _patch_module_get(monkeypatch, bizinfo_gateway, _status(401))

    with pytest.raises(Exception) as excinfo:
        bizinfo_gateway.BizinfoGateway().fetch_all()

    _assert_key_hidden(excinfo.value)
    assert "401" in str(excinfo.value) and "/uss/rss/bizinfoApi.do" in str(excinfo.value)


def test_youthcenter_http_error_hides_key(monkeypatch):
    monkeypatch.setattr(youthcenter_gateway, "get_settings", _settings("youthcenter_api_key"))
    monkeypatch.setattr(youthcenter_gateway.time, "sleep", lambda seconds: None)
    _patch_module_get(monkeypatch, youthcenter_gateway, _status(403))

    with pytest.raises(Exception) as excinfo:
        youthcenter_gateway.YouthcenterGateway().fetch_all()

    _assert_key_hidden(excinfo.value)
    assert "403" in str(excinfo.value) and "/go/ythip/getPlcy" in str(excinfo.value)


def test_youthcenter_request_error_hides_key(monkeypatch):
    monkeypatch.setattr(youthcenter_gateway, "get_settings", _settings("youthcenter_api_key"))
    monkeypatch.setattr(youthcenter_gateway.time, "sleep", lambda seconds: None)
    _patch_module_get(monkeypatch, youthcenter_gateway, _connect_error)

    with pytest.raises(Exception) as excinfo:
        youthcenter_gateway.YouthcenterGateway().fetch_all()

    _assert_key_hidden(excinfo.value)
    assert "ConnectError" in str(excinfo.value)


def test_mois_permit_http_error_hides_key(monkeypatch):
    monkeypatch.setattr(mois_permit_gateway, "get_settings", _settings("data_go_kr_api_key"))
    _patch_client(monkeypatch, mois_permit_gateway, _status(403))

    with pytest.raises(Exception) as excinfo:
        list(mois_permit_gateway.MoisPermitGateway().iter_stores(_TARGET, None))

    _assert_key_hidden(excinfo.value)
    assert "403" in str(excinfo.value) and "/1741000/karaoke_rooms/info" in str(excinfo.value)


def test_rone_http_error_hides_key(monkeypatch):
    monkeypatch.setattr(rone_gateway, "get_settings", _settings("rone_api_key"))
    _patch_client(monkeypatch, rone_gateway, _status(500))

    with pytest.raises(Exception) as excinfo:
        rone_gateway.RoneRentGateway().fetch_observations()

    _assert_key_hidden(excinfo.value)
    assert "500" in str(excinfo.value) and "/r-one/openapi/SttsApiTblData.do" in str(excinfo.value)


def test_mois_permit_retries_connect_error(monkeypatch):
    monkeypatch.setattr(mois_permit_gateway, "get_settings", _settings("data_go_kr_api_key"))
    monkeypatch.setattr(mois_permit_gateway.time, "sleep", lambda seconds: None)
    outcomes = [_connect_error, lambda request: httpx.Response(200, json=_MOIS_EMPTY, request=request)]
    _patch_client(monkeypatch, mois_permit_gateway, lambda request: outcomes.pop(0)(request))

    assert list(mois_permit_gateway.MoisPermitGateway().iter_stores(_TARGET, None)) == []
    assert outcomes == []


def test_youthcenter_retries_read_error(monkeypatch):
    monkeypatch.setattr(youthcenter_gateway, "get_settings", _settings("youthcenter_api_key"))
    monkeypatch.setattr(youthcenter_gateway.time, "sleep", lambda seconds: None)

    def read_error(request):
        raise httpx.ReadError("connection reset", request=request)

    ok = lambda request: httpx.Response(200, json={"result": {"youthPolicyList": []}}, request=request)  # noqa: E731
    outcomes = [read_error, ok]
    _patch_module_get(monkeypatch, youthcenter_gateway, lambda request: outcomes.pop(0)(request))

    assert youthcenter_gateway.YouthcenterGateway().fetch_all() == []
    assert outcomes == []
