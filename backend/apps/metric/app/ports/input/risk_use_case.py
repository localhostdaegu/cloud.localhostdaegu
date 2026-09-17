"""Driving Port — risk 위험도 스코어 UseCase 인터페이스 (region_industry_metric 파생 계산).

신규 ERD 테이블이 아니라 region_industry_metric의 파생 계산이므로 별도 Fractal
11-File Set을 두지 않고, 기존 RegionIndustryMetricRepositoryPort를 재사용한다.
"""

from abc import ABC, abstractmethod

from apps.metric.app.dtos.region_industry_metric_dto import RiskScoreDto


class RiskUseCase(ABC):
    @abstractmethod
    def rank_by_region(self, industry_id: str, year: int | None) -> list[RiskScoreDto]:
        """업종 고정 — 전 region 위험도 내림차순 랭킹. 데이터 없으면 빈 배열.

        year 미지정(세 메서드 공통) 시 마지막 완결 연도 이하의 최신 연도 — 부분 연도 제외.
        """

    @abstractmethod
    def score_for(
        self, region_code: str, industry_id: str, year: int | None
    ) -> RiskScoreDto | None:
        """region×industry 단건. 데이터 없거나 랭킹 불가(전년 표본 부재)면 None."""

    @abstractmethod
    def rank_by_industry(self, region_code: str, year: int | None) -> list[RiskScoreDto]:
        """region 고정 — 업종별 위험도 내림차순 랭킹. 데이터 없으면 빈 배열."""
