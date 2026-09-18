"""Driving Port — 다른 BC 가 금융상품을 읽을 때 쓰는 유일한 입구.

다른 BC 는 이 포트만 본다. 리포지토리(Adapter)를 직접 import 하면 §7 위반이다.
"""

from abc import ABC, abstractmethod

from apps.product.domain.entities.finance_product_entity import FinanceProduct


class FinanceProductUseCase(ABC):
    @abstractmethod
    def list_all(self) -> list[FinanceProduct]:
        """정본 상품 전체. 시드 전이면 빈 목록 — 호출자가 폴백을 정한다."""
