"""어린이집 공간조인 — 등록 구·군과 어긋난 판정 배제 검증 (순수 함수)."""

from apps.childcare.adapter.inbound.cli.childcare_collector import region_updates


def test_region_updates_reject_code_outside_registered_district():
    # 등록 구 밖 행정동으로 판정된 좌표는 좌표 오류로 보고 기입하지 않는다 (Metabole 동작구→중구 실측 전례)
    centers = [("A", "27110"), ("B", "27140"), ("C", "27110")]  # (center_id, district_code)
    codes = ["2711051700", "2711051700", None]
    assert region_updates(centers, codes) == [{"center_id": "A", "region_code": "2711051700"}]
