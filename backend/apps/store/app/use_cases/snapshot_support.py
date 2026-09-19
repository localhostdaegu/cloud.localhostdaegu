"""스냅샷 전량 재수집 흐름의 공통 규칙 — 부동산중개업(브이월드 NED)·학원(NEIS)이 같이 쓴다.

두 원천 모두 현행 스냅샷만 주고 폐업분·좌표를 주지 않는다. 그래서
- 좌표·행정동은 기존 지오코딩·공간조인 결과를 이월하고(carry_location),
- 폐업은 "이전 스냅샷에 있었으나 이번에 없음"으로 추정해 관측일을 close_date로 기록한다(CLOSED_*).
"""

from dataclasses import replace

from apps.store.domain.entities.store_entity import Store

CLOSED_STATUS_CODE = "closed_estimated"
CLOSED_STATUS_NAME = "폐업(추정)"


def carry_location(
    store: Store, locations: dict[str, tuple[float, float, str | None]]
) -> Store:
    """원천에 좌표가 없으므로 기존 지오코딩·공간조인 결과를 이월한다 (멱등)."""
    if store.lat is not None or store.store_id not in locations:
        return store
    lat, lng, region_code = locations[store.store_id]
    return replace(store, lat=lat, lng=lng, region_code=region_code)
