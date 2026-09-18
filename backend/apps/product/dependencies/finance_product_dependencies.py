"""Composition Root (DIP) — product 포트에 어댑터를 주입한다."""

from functools import lru_cache

from apps.product.adapter.outbound.repositories.finance_product_repository import (
    SqlAlchemyFinanceProductRepository,
)
from apps.product.app.ports.input.finance_product_use_case import FinanceProductUseCase
from apps.product.app.use_cases.finance_product_interactor import FinanceProductInteractor


@lru_cache
def get_finance_product_use_case() -> FinanceProductUseCase:
    return FinanceProductInteractor(SqlAlchemyFinanceProductRepository())
