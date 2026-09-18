"""FinanceProductInteractor — 얇은 Application Service (조회 위임만)."""

from apps.product.app.ports.input.finance_product_use_case import FinanceProductUseCase
from apps.product.app.ports.output.finance_product_port import FinanceProductRepositoryPort
from apps.product.domain.entities.finance_product_entity import FinanceProduct


class FinanceProductInteractor(FinanceProductUseCase):
    def __init__(self, repository: FinanceProductRepositoryPort) -> None:
        self._repository = repository

    def list_all(self) -> list[FinanceProduct]:
        return self._repository.list_all()
