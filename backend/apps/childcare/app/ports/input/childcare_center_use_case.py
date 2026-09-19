"""Driving Ports — 어린이집 스냅샷 수집 UseCase 계약."""

from abc import ABC, abstractmethod
from datetime import date


class ChildcareSnapshotUseCase(ABC):
    @abstractmethod
    def ingest(self, district_code: str, observed_on: date) -> int:
        """자치구 스냅샷 전량 업서트(시설 + 기준일 현황) — 처리 건수 반환.
        소실 시설은 last_seen_on 정지로 남는다(폐원 판정 없음 — 후속 분석 몫)."""
