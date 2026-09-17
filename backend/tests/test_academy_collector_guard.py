"""academy collector 가드 — 원천이 서울 열린데이터 전용이라 대구 구성에서는 수집 없이 중단 (DB·네트워크 미사용)."""

import pytest

from apps.store.adapter.inbound.cli import academy_collector


def test_academy_collector_exits_without_daegu_source(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("서울 학원 게이트웨이가 호출되면 안 됨 — 동명 구(중구 등)로 대구 코드에 매핑됨")

    monkeypatch.setattr(academy_collector, "SeoulAcademyGateway", fail_if_called)
    monkeypatch.setattr(academy_collector, "session_scope", fail_if_called)

    with pytest.raises(SystemExit) as excinfo:
        academy_collector.main()

    assert excinfo.value.code != 0
    assert "대구" in str(excinfo.value.code)
