"""CORS 허용 오리진 — 배포 시 운영 도메인을 환경변수로 추가할 수 있어야 한다.

하드코딩이면 배포한 프론트가 백엔드를 부르지 못한다(브라우저가 응답을 버린다).
"""

from core.matrix.grid_cors import allowed_origins

_LOCAL = ["http://localhost:3300", "http://127.0.0.1:3300"]


def test_local_dev_origins_are_always_allowed():
    assert set(_LOCAL) <= set(allowed_origins(""))


def test_extra_origins_come_from_settings():
    origins = allowed_origins("https://localhostdaegu.cloud")

    assert "https://localhostdaegu.cloud" in origins
    assert set(_LOCAL) <= set(origins)


def test_multiple_origins_are_comma_separated():
    origins = allowed_origins("https://localhostdaegu.cloud, https://www.localhostdaegu.cloud")

    assert "https://localhostdaegu.cloud" in origins
    assert "https://www.localhostdaegu.cloud" in origins


def test_blank_entries_are_ignored():
    """설정 실수로 빈 오리진이 들어가면 CORS 가 조용히 망가진다."""
    assert "" not in allowed_origins("https://localhostdaegu.cloud,, ")


def test_duplicates_are_removed_but_order_is_stable():
    origins = allowed_origins("http://localhost:3300, https://localhostdaegu.cloud")

    assert origins.count("http://localhost:3300") == 1
    assert origins[:2] == _LOCAL
