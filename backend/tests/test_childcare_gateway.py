"""ChildcarePortalGateway XML 파싱 단위 검증 — 픽스처 기반 (실호출 없음)."""

from datetime import date

import pytest

from apps.childcare.adapter.outbound.gateways.childcare_portal_gateway import (
    ChildcarePortalGateway,
)

_DISTRICT_CODE = "27110"  # 중구 — arcode = district_code (5자리)

# 2026-09-19 실응답(대구 중구 40건) 1건 축약 사본 — 수집 대상 외 필드는 일부만 남김
_ITEM = """<item><sidoname>대구광역시</sidoname><sigunname>중구</sigunname>
<stcode>27110000070</stcode><crname>경북대학교병원어린이집</crname><crtypename>직장</crtypename>
<crstatusname>정상</crstatusname><zipcode>41944</zipcode>
<craddr>대구광역시 중구 국채보상로140길 24-7(동인동 2가)</craddr>
<crtelno>053-200-5390</crtelno><chcrtescnt>12</chcrtescnt><crcapat>49</crcapat>
<crchcnt>44</crchcnt><la>35.86769811459113</la><lo>128.60582712244448</lo><crcnfmdt>2001-03-02</crcnfmdt>
<crpausebegindt></crpausebegindt><crpauseenddt></crpauseenddt><crabldt></crabldt>
<datastdrdt>2026-09-19</datastdrdt><crspec></crspec>
<CLASS_CNT_TOT>6</CLASS_CNT_TOT><CHILD_CNT_TOT>44</CHILD_CNT_TOT><EW_CNT_TOT>3</EW_CNT_TOT></item>"""


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


def _gateway_with_body(monkeypatch, body: str) -> tuple[ChildcarePortalGateway, list[dict]]:
    calls: list[dict] = []

    def fake_get(client, url, params):
        calls.append(params)
        return _FakeResponse(body)

    monkeypatch.setattr(ChildcarePortalGateway, "_get_with_retry", staticmethod(fake_get))
    monkeypatch.setenv("CHILDCARE_API_KEY", "test-key")
    return ChildcarePortalGateway(), calls


def test_to_entity_maps_real_fields(monkeypatch):
    gateway, calls = _gateway_with_body(monkeypatch, f"<response>{_ITEM}</response>")
    (center,) = gateway.fetch_centers(_DISTRICT_CODE)

    assert center.center_id == "27110000070"
    assert center.name == "경북대학교병원어린이집"
    assert center.type_name == "직장"
    assert center.status_name == "정상"
    assert center.district_code == _DISTRICT_CODE
    assert center.address == "대구광역시 중구 국채보상로140길 24-7(동인동 2가)"
    assert center.zipcode == "41944"
    assert center.tel == "053-200-5390"
    assert center.lat == pytest.approx(35.86769811459113)
    assert center.lng == pytest.approx(128.60582712244448)
    assert center.approved_on == date(2001, 3, 2)
    assert (center.paused_from, center.paused_until, center.abolished_on) == (None, None, None)

    stat = center.stat
    assert stat.base_date == date(2026, 9, 19)
    assert (stat.capacity, stat.child_count, stat.waiting_count) == (49, 44, 3)
    assert (stat.class_count, stat.staff_count) == (6, 12)

    assert calls[0]["arcode"] == _DISTRICT_CODE
    assert gateway.call_count == 1


def test_blank_waiting_and_coords_preserved_as_none(monkeypatch):
    # 원천은 대기 공란이 흔하고 "0" 표기가 없다 — 0으로 추정하지 않는다
    item = (
        _ITEM.replace("<EW_CNT_TOT>3</EW_CNT_TOT>", "<EW_CNT_TOT></EW_CNT_TOT>")
        .replace("<la>35.86769811459113</la>", "<la></la>")
        .replace("<lo>128.60582712244448</lo>", "<lo></lo>")
    )
    gateway, _ = _gateway_with_body(monkeypatch, f"<response>{item}</response>")
    (center,) = gateway.fetch_centers(_DISTRICT_CODE)
    assert center.stat.waiting_count is None
    assert center.lat is None and center.lng is None


def test_blank_status_preserved_as_none(monkeypatch):
    item = _ITEM.replace("<crstatusname>정상</crstatusname>", "<crstatusname></crstatusname>")
    gateway, _ = _gateway_with_body(monkeypatch, f"<response>{item}</response>")
    (center,) = gateway.fetch_centers(_DISTRICT_CODE)
    assert center.status_name is None


def test_error_body_raises(monkeypatch):
    # 인증 실패도 HTTP 200 + errcode 본문으로 온다
    body = "<response><errmsg>인증키가 유효하지 않습니다.</errmsg><errcode>INFO-100</errcode></response>"
    gateway, _ = _gateway_with_body(monkeypatch, body)
    with pytest.raises(RuntimeError, match="INFO-100"):
        gateway.fetch_centers(_DISTRICT_CODE)
