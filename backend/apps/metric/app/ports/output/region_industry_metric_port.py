"""Driven Ports — metric이 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod

from apps.metric.app.dtos.region_industry_metric_dto import YearlyStoreStat
from apps.metric.domain.entities.region_industry_metric_entity import (
    RegionIndustryMetric,
)


class RegionIndustryMetricRepositoryPort(ABC):
    @abstractmethod
    def upsert(self, metrics: list[RegionIndustryMetric]) -> int:
        """(region_code, industry_id, year) 기준 업서트 — 처리 건수 반환."""

    @abstractmethod
    def list_by_industry_year(
        self, industry_id: str, year: int
    ) -> list[RegionIndustryMetric]:
        """해당 업종×연도의 전 행정동 지표를 region_code 순으로 반환한다."""

    @abstractmethod
    def find(
        self, region_code: str, industry_id: str, year: int
    ) -> RegionIndustryMetric | None:
        """복합키 단건 조회 — 없으면 None."""

    @abstractmethod
    def latest_year(self, industry_id: str | None = None) -> int | None:
        """해당 industry(미지정 시 전체)의 최신(최대) year. 데이터 없으면 None (risk API용)."""

    @abstractmethod
    def list_by_region_year(
        self, region_code: str, year: int
    ) -> list[RegionIndustryMetric]:
        """해당 region의 해당 연도 전 업종 지표를 industry_id 순으로 반환한다 (risk API용)."""

    @abstractmethod
    def list_latest_by_region(self, region_code: str) -> list[RegionIndustryMetric]:
        """해당 region의 업종별 최신(최대) year 행을 1개씩 반환한다.

        업종마다 최신 연도가 다를 수 있으므로(예: A업종 2025, B업종 2023) 단일
        year로 필터링하지 않는다 — region 전체 업종 랭킹(risk API)에서 다른
        연도의 업종이 조용히 누락되는 것을 막기 위함.
        """


class StoreStatsPort(ABC):
    @abstractmethod
    def yearly_stats(self, years: list[int]) -> list[YearlyStoreStat]:
        """연도별 행정동×업종 store 원천 카운트 (region_code 보유 점포만)."""


class IndustryCatalogPort(ABC):
    @abstractmethod
    def exists(self, industry_id: str) -> bool:
        """industry 마스터 등록 여부."""
