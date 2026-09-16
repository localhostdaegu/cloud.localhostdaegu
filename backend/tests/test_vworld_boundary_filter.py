"""브이월드 WFS lt_c_cademd 의 adm_cd 는 통계청 시도코드(대구=22) — 행안부 27 로 필터하면 0건 (2026-09-16 실호출)."""

from apps.master.adapter.outbound.gateways.vworld_boundary_gateway import _ADMIN_DONG_FILTER
from core.matrix.grid_region_config import KOSTAT_SIDO_PREFIX


def test_wfs_filter_uses_kostat_sido_prefix():
    assert KOSTAT_SIDO_PREFIX == "22"
    assert f"<Literal>{KOSTAT_SIDO_PREFIX}*</Literal>" in _ADMIN_DONG_FILTER
