"""Driven Ports — regional_indicator가 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod

from apps.indicator.domain.entities.regional_indicator_entity import RegionalIndicator


class RegionalIndicatorRepositoryPort(ABC):
    @abstractmethod
    def upsert(self, indicators: list[RegionalIndicator]) -> int:
        """자연키(dataset_id, region_code, industry_id, period, indicator_key, breakdown) 업서트(멱등).

        적재한 행 수를 반환한다. 미승인·미등록 데이터셋이면 적재 없이 도메인 예외를 던진다
        (DatasetNotApprovedError / DatasetNotFoundError) — 승인 전 수치가 서비스에 들어갈 길을 끊는다.
        """
