"""Driving Port — 학원 수집 UseCase 인터페이스."""

from abc import ABC, abstractmethod
from datetime import date


class AcademyIngestUseCase(ABC):
    @abstractmethod
    def ingest(self, observed_on: date) -> tuple[int, int, int]:
        """학원·교습소 스냅샷 전량을 수집해 (점포 업서트, 교습과정 재적재, 폐업 추정 건수)를 반환한다.

        원천(NEIS)이 현행 스냅샷만 제공하므로 매 실행 전량 수집(업서트라 멱등). 좌표·행정동은 이월하고,
        이전 스냅샷에 있었으나 이번에 없는 점포는 관측일을 close_date로 폐업(추정) 처리한다 (broker 전례).
        """
