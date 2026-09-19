"""점→행정동 공간 인덱스 — region.geometry_ref 경계 GeoJSON × 좌표 포함 판정 (shapely STRtree).

DB에 PostGIS가 없어(pgvector 이미지) 앱사이드 공간조인을 쓴다. store·tobacco·indicator 등 여러 BC의
적재 CLI가 같은 판정을 써야 하므로 core에 둔다 (core는 apps를 import하지 않는다).
미포함 점은 최근접 경계 허용 오차 내 스냅 — 경계 틈·좌표 변환 오차 흡수.
"""

import json
from pathlib import Path

import shapely
from shapely import STRtree

# 경계 틈·좌표 변환 오차 흡수 스냅 한계 — 대구 위도(35.9°)에서 0.0005° ≈ 45~56m
# (EPSG:5174→WGS84 변환 오차 ±3m 실측 + 인접 폴리곤 사이 미세 틈 대비)
_NEAREST_TOLERANCE_DEG = 0.0005


class RegionIndex:
    """(region_code, GeoJSON geometry) 목록의 공간 인덱스 — 점→행정동 판정."""

    def __init__(self, items: list[tuple[str, dict]]) -> None:
        self._codes = [code for code, _ in items]
        self._geoms = shapely.from_geojson(
            json.dumps(
                {
                    "type": "GeometryCollection",
                    "geometries": [geometry for _, geometry in items],
                }
            )
        ).geoms
        self._tree = STRtree(list(self._geoms))

    @classmethod
    def from_refs(cls, repo_root: Path, refs: list[tuple[str, str]]) -> "RegionIndex":
        """refs: [(region_code, geometry_ref 상대경로)] — 파일에서 geometry만 읽는다."""
        items = []
        for region_code, ref in refs:
            feature = json.loads((repo_root / ref).read_text(encoding="utf-8"))
            items.append((region_code, feature["geometry"]))
        return cls(items)

    def locate_many(self, lngs: list[float], lats: list[float]) -> list[str | None]:
        points = shapely.points(lngs, lats)
        result: list[str | None] = [None] * len(points)
        for point_idx, geom_idx in zip(*self._tree.query(points, predicate="within")):
            result[point_idx] = self._codes[geom_idx]
        for i, code in enumerate(result):
            if code is None:
                nearest = self._tree.nearest(points[i])
                if points[i].distance(self._geoms[int(nearest)]) <= _NEAREST_TOLERANCE_DEG:
                    result[i] = self._codes[int(nearest)]
        return result

    def locate(self, lng: float, lat: float) -> str | None:
        return self.locate_many([lng], [lat])[0]
