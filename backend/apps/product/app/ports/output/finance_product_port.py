"""Driven Ports — finance_product 가 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod

from apps.product.domain.entities.finance_product_entity import FinanceProduct


class FinanceProductRepositoryPort(ABC):
    @abstractmethod
    def upsert(self, products: list[FinanceProduct]) -> tuple[int, int]:
        """product_id 기준 업서트(멱등) — (신규, 갱신) 건수 반환.

        category 의 industry_id 가 industry 마스터에 없으면 ValueError 로 실패한다 — 조용히 버리지 않는다.
        """

    @abstractmethod
    def list_all(self) -> list[FinanceProduct]:
        """전체 상품을 product_id 오름차순으로 반환한다 (12건 규모 — 페이징 없음)."""
