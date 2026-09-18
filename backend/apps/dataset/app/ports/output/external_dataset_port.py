"""Driven Ports — external_dataset이 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod

from apps.dataset.domain.entities.external_dataset_entity import ExternalDataset


class ExternalDatasetRepositoryPort(ABC):
    @abstractmethod
    def upsert(self, datasets: list[ExternalDataset]) -> tuple[int, int]:
        """dataset_id 기준 업서트(멱등) — (신규, 갱신) 건수 반환."""

    @abstractmethod
    def get_by_id(self, dataset_id: str) -> ExternalDataset | None:
        """등록되지 않은 데이터셋이면 None."""

    @abstractmethod
    def list_all(self) -> list[ExternalDataset]:
        """등록된 데이터셋 전체 (dataset_id 오름차순) — 승인·미승인을 함께 돌려준다.

        미승인을 감추면 "반출 승인을 받은 것만 있다"는 인상을 주므로 걸러내지 않는다.
        """
