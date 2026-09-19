"""점포 행정동 공간조인 러너 (Driving Adapter, CLI).

- 입력: region.geometry_ref의 경계 GeoJSON(v0.6.0 적재) × store.lat/lng
- 판정: core RegionIndex(shapely STRtree 포함 + 최근접 스냅) — 여러 BC가 같은 판정을 공유한다
- 멱등: 기본은 region_code IS NULL 행만 채움. --full 은 전체 재판정 (경계 갱신 시)
- 일일 증분(store-collector 크론) 후속 실행을 전제로 설계

실행: python -m apps.store.adapter.inbound.cli.assign_regions [--full]
"""

import argparse
from pathlib import Path

from sqlalchemy import select, update

from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from apps.store.adapter.outbound.orms.store_orm import StoreOrm
from core.matrix.grid_geo_region_index import RegionIndex
from core.matrix.grid_oracle_database_manager import session_scope

_REPO_ROOT = Path(__file__).resolve().parents[6]
_UPDATE_CHUNK = 10_000


def assign_all(full: bool = False) -> None:
    with session_scope() as session:
        refs = session.execute(
            select(RegionOrm.region_code, RegionOrm.geometry_ref).where(
                RegionOrm.geometry_ref.is_not(None)
            )
        ).all()
        index = RegionIndex.from_refs(_REPO_ROOT, [tuple(r) for r in refs])
        print(f"경계 인덱스: {len(refs)}개 행정동")

        stmt = select(
            StoreOrm.store_id, StoreOrm.lng, StoreOrm.lat, StoreOrm.district_code
        ).where(StoreOrm.lat.is_not(None), StoreOrm.lng.is_not(None))
        if not full:
            stmt = stmt.where(StoreOrm.region_code.is_(None))
        rows = session.execute(stmt).all()
        print(f"판정 대상: {len(rows)}건")
        if not rows:
            return

        codes = index.locate_many([r.lng for r in rows], [r.lat for r in rows])

        updates = [
            {"store_id": row.store_id, "region_code": code}
            for row, code in zip(rows, codes)
            if code is not None
        ]
        for start in range(0, len(updates), _UPDATE_CHUNK):
            session.execute(update(StoreOrm), updates[start : start + _UPDATE_CHUNK])

        unassigned = len(rows) - len(updates)
        # 교차검증: 판정된 행정동의 소속 구 vs 인허가 관할 구 (경계 인접부는 정상 불일치 가능)
        district_by_region = {
            rc: dc
            for rc, dc in session.execute(select(RegionOrm.region_code, RegionOrm.district_code))
        }
        mismatch = sum(
            1
            for row, code in zip(rows, codes)
            if code is not None and district_by_region.get(code) != row.district_code
        )
        print(f"기입: {len(updates)}건 / 미판정: {unassigned}건 / 구 교차 불일치: {mismatch}건")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="region_code 기존 값 포함 전체 재판정")
    args = parser.parse_args()
    assign_all(full=args.full)


if __name__ == "__main__":
    main()
