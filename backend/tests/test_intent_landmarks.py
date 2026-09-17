"""랜드마크 사전 정합성 — 모든 별칭이 시드된 region 행(동명·구코드)을 가리켜야 한다 (테스트 DB)."""

from sqlalchemy import select

from apps.intent.domain.landmarks import LANDMARKS
from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from core.matrix.grid_oracle_database_manager import session_scope


def test_every_landmark_points_at_seeded_region_row():
    with session_scope() as session:
        rows = {(name, code) for name, code in session.execute(select(RegionOrm.name, RegionOrm.district_code))}

    dangling = {landmark: target for landmark, target in LANDMARKS.items() if target not in rows}
    assert dangling == {}, f"region 테이블에 없는 동을 가리키는 랜드마크: {dangling}"
