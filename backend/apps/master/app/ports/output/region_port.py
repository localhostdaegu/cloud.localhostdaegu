"""Driven Ports — region이 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod

from apps.master.app.dtos.region_dto import RegionMetricSnapshot
from apps.master.domain.entities.region_entity import Region


class RegionRepositoryPort(ABC):
    @abstractmethod
    def list_regions(self) -> list[Region]:
        """전체 행정동을 region_code 순으로 반환한다."""

    @abstractmethod
    def find(self, region_code: str) -> Region | None:
        """행정동코드 단건 조회 — 없으면 None."""


class RegionBoundaryReaderPort(ABC):
    @abstractmethod
    def read_feature(self, geometry_ref: str) -> dict:
        """geometry_ref 경로의 경계 GeoJSON Feature를 읽어 반환한다."""


class RegionMetricSummaryPort(ABC):
    @abstractmethod
    def fetch(
        self, region_code: str, industry_id: str, year: int | None = None
    ) -> RegionMetricSnapshot | None:
        """해당 행정동×업종 지표 스냅샷. year 미지정이면 마지막 완결 연도. 없으면 None."""
