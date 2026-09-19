"""Driven Port — rent_price가 바깥 세계에 요구하는 계약."""

from abc import ABC, abstractmethod

from apps.rent.domain.entities.rent_price_entity import RentPrice


class RentPriceRepositoryPort(ABC):
    @abstractmethod
    def find_latest(self) -> list[RentPrice]:
        """테이블 전체에서 period(YYYYQn)가 가장 늦은 분기의 전 행 (순서 무보장) — 없으면 []."""
