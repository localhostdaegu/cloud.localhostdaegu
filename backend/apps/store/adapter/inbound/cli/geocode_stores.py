"""주소 → 좌표 지오코딩 러너 (Driving Adapter, CLI).

- 대상: 원천에 좌표가 없는 업종(학원·부동산중개업)의 store.lat IS NULL AND address IS NOT NULL.
  --childcare 는 어린이집 원천 좌표 오류분을 SGIS 좌표로 덮어쓰고 행정동을 다시 기입한다.
  대상 판정은 캐시가 아니라 좌표 자체를 본다 — 대구 범위 밖이거나 판정 행정동이 등록 구·군과
  다르면 오류다(store의 lat IS NULL 트리거와 같은 역할). 캐시가 없어도 SGIS 호출로 복구된다
- 캐시 필수: data/cache/sgis_geocode.csv (address,lng,lat — 실패는 빈 값). 재수집이 store 업서트
  (session.merge)로 lat/lng를 None으로 되돌려도 이 CLI 재실행이 API 0회로 좌표를 복원한다.
  어린이집도 같은 원리 — 원천 오류 좌표가 다시 덮여도 캐시가 보정값을 재적용한다
- 대구 범위(grid_region_config LAT_RANGE/LNG_RANGE) 밖 좌표는 기입하지 않고 건수만 보고 —
  동명 주소가 타 시도로 매칭되는 사고 방어
- 후속: assign_regions(신규 좌표분 행정동 기입) → build_metrics

실행: python -m apps.store.adapter.inbound.cli.geocode_stores [--industry academy] [--limit N]
      python -m apps.store.adapter.inbound.cli.geocode_stores --childcare
"""

import argparse
import csv
from pathlib import Path

from sqlalchemy import select, update

from apps.childcare.adapter.inbound.cli.childcare_collector import assign_regions
from apps.childcare.adapter.outbound.orms.childcare_center_orm import ChildcareCenterOrm
from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from apps.store.adapter.outbound.gateways.sgis_geocode_gateway import SgisGeocodeGateway
from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from core.matrix.grid_geo_region_index import RegionIndex
from core.matrix.grid_oracle_database_manager import session_scope
from core.matrix.grid_region_config import LAT_RANGE, LNG_RANGE

_REPO_ROOT = Path(__file__).resolve().parents[6]
_CACHE_PATH = _REPO_ROOT / "data" / "cache" / "sgis_geocode.csv"
_UPDATE_CHUNK = 1_000
_FLUSH_EVERY = 200  # 수천 건 실행이 중단돼도 그때까지의 호출 결과는 캐시에 남는다


# ---------- 순수 함수 ----------


def load_cache(path: Path) -> dict[str, tuple[float, float] | None]:
    """주소 → (lng, lat) | None(실패 기록). 값이 None이어도 키가 있으면 재호출하지 않는다."""
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as f:
        return {
            row["address"]: (float(row["lng"]), float(row["lat"])) if row["lng"] else None
            for row in csv.DictReader(f)
        }


def append_cache(path: Path, entries: list[tuple[str, tuple[float, float] | None]]) -> None:
    if not entries:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["address", "lng", "lat"])
        for address, point in entries:
            writer.writerow([address, *(point or ("", ""))])


def in_daegu(lng: float, lat: float) -> bool:
    return LNG_RANGE[0] <= lng <= LNG_RANGE[1] and LAT_RANGE[0] <= lat <= LAT_RANGE[1]


def source_coordinate_is_wrong(
    lng: float | None, lat: float | None, located: str | None, district_code: str
) -> bool:
    """원천 좌표를 못 쓰는지 좌표만 보고 판정 — 캐시 유무와 무관해야 재수집 후에도 복구된다.

    located: 좌표를 RegionIndex로 판정한 행정동(없으면 None).
    구 밖 판정 규칙은 childcare_collector.region_updates 와 같다 (앞 5자리 = district_code).
    """
    if lng is None or lat is None:
        return True
    if not in_daegu(lng, lat):  # 서울시청 자리표시자·경산/영천 등 시도 밖
        return True
    return located is None or not located.startswith(district_code)


# ---------- 지오코딩 ----------


def resolve_points(
    gateway: SgisGeocodeGateway, cache_path: Path, addresses: list[str]
) -> dict[str, tuple[float, float] | None]:
    """캐시에 없는 주소만 SGIS에 묻고, 결과(실패 포함)를 캐시에 추가한다."""
    cache = load_cache(cache_path)
    unique = list(dict.fromkeys(addresses))  # 같은 건물 주소 중복 호출 방지
    pending: list[tuple[str, tuple[float, float] | None]] = []
    for index, address in enumerate(unique, start=1):
        if address in cache:
            continue
        cache[address] = gateway.geocode(address)
        pending.append((address, cache[address]))
        if len(pending) >= _FLUSH_EVERY:
            append_cache(cache_path, pending)
            pending = []
            print(f"  진행 {index}/{len(unique)}건 (고유 주소)", flush=True)
    append_cache(cache_path, pending)
    return cache


def _apply(rows: list, cache: dict[str, tuple[float, float] | None], id_field: str) -> tuple[list, int, int]:
    """(id, address) 행 → UPDATE 값 목록. 실패·대구 범위 밖은 기입하지 않는다."""
    updates, failed, out_of_range = [], 0, 0
    for row in rows:
        point = cache.get(row.address)
        if point is None:
            failed += 1
        elif not in_daegu(*point):
            out_of_range += 1
        else:
            updates.append({id_field: getattr(row, id_field), "lng": point[0], "lat": point[1]})
    return updates, failed, out_of_range


def _flush(session, orm, updates: list[dict]) -> None:
    for start in range(0, len(updates), _UPDATE_CHUNK):
        session.execute(update(orm), updates[start : start + _UPDATE_CHUNK])


def geocode_stores(gateway: SgisGeocodeGateway, industry: str | None, limit: int | None) -> None:
    with session_scope() as session:
        statement = (
            select(StoreOrm.store_id, StoreOrm.address)
            .where(StoreOrm.lat.is_(None), StoreOrm.address.is_not(None))
            .order_by(StoreOrm.store_id)
        )
        if industry:
            statement = statement.where(StoreOrm.industry_id == industry)
        if limit:
            statement = statement.limit(limit)
        rows = session.execute(statement).all()
        print(f"store 지오코딩 대상: {len(rows)}건", flush=True)
        if not rows:
            return

        cache = resolve_points(gateway, _CACHE_PATH, [r.address for r in rows])
        updates, failed, out_of_range = _apply(rows, cache, "store_id")
        _flush(session, StoreOrm, updates)
        print(
            f"store 좌표 기입: {len(updates)}건 / 실패: {failed}건 /"
            f" 대구 범위 밖(미기입): {out_of_range}건 (SGIS {gateway.call_count}회 호출)",
            flush=True,
        )


def _locate_all(session, rows: list) -> dict[str, str | None]:
    """center_id → 현재 좌표가 떨어지는 행정동 (좌표 없는 행은 제외)."""
    refs = session.execute(
        select(RegionOrm.region_code, RegionOrm.geometry_ref).where(
            RegionOrm.geometry_ref.is_not(None)
        )
    ).all()
    placed = [r for r in rows if r.lat is not None and r.lng is not None]
    index = RegionIndex.from_refs(_REPO_ROOT, [tuple(r) for r in refs])
    codes = index.locate_many([r.lng for r in placed], [r.lat for r in placed])
    return {r.center_id: code for r, code in zip(placed, codes)}


def geocode_childcare(gateway: SgisGeocodeGateway, limit: int | None) -> None:
    """원천 좌표가 틀린 시설을 다시 지오코딩한다 — 판정은 좌표 자체로만 하므로 캐시가 없어도 복구된다."""
    with session_scope() as session:
        rows = session.execute(
            select(
                ChildcareCenterOrm.center_id,
                ChildcareCenterOrm.address,
                ChildcareCenterOrm.region_code,
                ChildcareCenterOrm.district_code,
                ChildcareCenterOrm.lng,
                ChildcareCenterOrm.lat,
            ).order_by(ChildcareCenterOrm.center_id)
        ).all()
        located = _locate_all(session, rows)
        targets = [
            r
            for r in rows
            if r.region_code is None
            or source_coordinate_is_wrong(
                r.lng, r.lat, located.get(r.center_id), r.district_code
            )
        ]
        if limit:
            targets = targets[:limit]
        print(f"childcare 지오코딩 대상: {len(targets)}건", flush=True)
        if not targets:
            return

        cache = resolve_points(gateway, _CACHE_PATH, [r.address for r in targets])
        updates, failed, out_of_range = _apply(targets, cache, "center_id")
        _flush(session, ChildcareCenterOrm, updates)
        print(
            f"childcare 좌표 기입: {len(updates)}건 / 실패: {failed}건 /"
            f" 대구 범위 밖(미기입): {out_of_range}건 (SGIS {gateway.call_count}회 호출)",
            flush=True,
        )
    assign_regions()


def main() -> None:
    parser = argparse.ArgumentParser(description="주소 → SGIS 좌표 (캐시 우선)")
    parser.add_argument("--industry", help="업종 한정 (예: academy, real_estate)")
    parser.add_argument("--limit", type=int, help="대상 건수 상한 — 소량 검증용")
    parser.add_argument(
        "--childcare", action="store_true", help="store 대신 어린이집 원천 좌표 오류분 보정"
    )
    args = parser.parse_args()

    gateway = SgisGeocodeGateway()
    if args.childcare:
        geocode_childcare(gateway, args.limit)
    else:
        geocode_stores(gateway, args.industry, args.limit)


if __name__ == "__main__":
    main()
