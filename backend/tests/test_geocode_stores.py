"""geocode_stores 캐시·범위 판정 단위 검증 (DB·API 접촉 없음)."""

from apps.store.adapter.inbound.cli.geocode_stores import (
    append_cache,
    in_daegu,
    load_cache,
    resolve_points,
    source_coordinate_is_wrong,
)


def test_load_cache_returns_empty_for_missing_file(tmp_path):
    assert load_cache(tmp_path / "none.csv") == {}


def test_append_cache_roundtrip_keeps_failures(tmp_path):
    path = tmp_path / "sgis_geocode.csv"
    append_cache(path, [("대구광역시 중구 동덕로 182", (128.60462, 35.87083))])
    append_cache(path, [("없는 주소", None)])

    # 실패는 빈 값으로 남아 재호출을 막는다 — "캐시에 없음"과 구분돼야 한다
    assert load_cache(path) == {
        "대구광역시 중구 동덕로 182": (128.60462, 35.87083),
        "없는 주소": None,
    }
    assert path.read_text(encoding="utf-8").splitlines()[0] == "address,lng,lat"


def test_in_daegu_rejects_outside_range():
    assert in_daegu(128.60462, 35.87083)
    assert not in_daegu(126.97, 37.57)  # 서울시청 — 동명 주소 오매칭 방어


def test_source_coordinate_is_wrong_detects_out_of_range():
    # 원천이 지오코딩 실패 시 채우는 서울시청 자리표시자 — 대구 범위 밖
    assert source_coordinate_is_wrong(126.977963, 37.56647, None, "27200")
    assert source_coordinate_is_wrong(None, None, None, "27200")


def test_source_coordinate_is_wrong_detects_district_mismatch():
    # 대구 안이지만 판정 행정동이 등록 구·군(27230 북구)과 다르다 — 원천 좌표 오류
    assert source_coordinate_is_wrong(128.59552, 35.87743, "2714074200", "27230")
    # 경계 밖이라 판정 자체가 안 되는 좌표도 대상
    assert source_coordinate_is_wrong(128.59552, 35.87743, None, "27230")


def test_source_coordinate_is_wrong_accepts_correct_coordinate():
    # 판정 행정동 앞 5자리가 등록 구·군과 같으면 정상 — 캐시 유무와 무관하게 건드리지 않는다
    assert not source_coordinate_is_wrong(128.59552, 35.87743, "2723052600", "27230")


class _FakeGateway:
    def __init__(self, points: dict) -> None:
        self._points = points
        self.asked: list[str] = []
        self.call_count = 0

    def geocode(self, address: str):
        self.asked.append(address)
        self.call_count += 1
        return self._points.get(address)


def test_resolve_points_calls_api_only_for_uncached(tmp_path):
    path = tmp_path / "sgis_geocode.csv"
    append_cache(path, [("이미 있는 주소", (128.6, 35.87)), ("이미 실패한 주소", None)])
    gateway = _FakeGateway({"새 주소": (128.5, 35.85)})

    cache = resolve_points(
        gateway, path, ["이미 있는 주소", "이미 실패한 주소", "새 주소", "새 주소"]
    )

    assert gateway.asked == ["새 주소"]  # 캐시 적중·중복 주소는 호출하지 않는다
    assert cache["새 주소"] == (128.5, 35.85)
    assert load_cache(path)["새 주소"] == (128.5, 35.85)


def test_resolve_points_caches_failures(tmp_path):
    path = tmp_path / "sgis_geocode.csv"
    gateway = _FakeGateway({})

    resolve_points(gateway, path, ["실패 주소"])
    resolve_points(gateway, path, ["실패 주소"])

    assert gateway.call_count == 1  # 두 번째 실행은 캐시된 실패로 재호출하지 않는다


def test_resolve_points_retry_failed_requeries_cached_failures(tmp_path):
    path = tmp_path / "sgis_geocode.csv"
    append_cache(path, [("이미 있는 주소", (128.6, 35.87)), ("이미 실패한 주소", None)])
    gateway = _FakeGateway({"이미 실패한 주소": (128.55, 35.86)})

    cache = resolve_points(gateway, path, ["이미 있는 주소", "이미 실패한 주소"], retry_failed=True)

    assert gateway.asked == ["이미 실패한 주소"]  # 성공 캐시는 그대로, 실패만 다시 묻는다
    assert cache["이미 실패한 주소"] == (128.55, 35.86)
    assert load_cache(path)["이미 실패한 주소"] == (128.55, 35.86)  # 캐시 파일도 갱신된다
