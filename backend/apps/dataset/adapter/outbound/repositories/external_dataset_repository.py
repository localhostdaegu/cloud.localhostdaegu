from sqlalchemy import select

from apps.dataset.adapter.outbound.orm_mappers.external_dataset_orm_mapper import (
    apply_to_orm,
    to_entity,
    to_orm,
)
from apps.dataset.adapter.outbound.orms.external_dataset_orm import ExternalDatasetOrm
from apps.dataset.app.ports.output.external_dataset_port import ExternalDatasetRepositoryPort
from apps.dataset.domain.entities.external_dataset_entity import ExternalDataset
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyExternalDatasetRepository(ExternalDatasetRepositoryPort):
    def upsert(self, datasets: list[ExternalDataset]) -> tuple[int, int]:
        if not datasets:
            return 0, 0
        # dict — 같은 배치 안의 중복 dataset_id 제거 (funding·news BC 관행)
        batch = {d.dataset_id: d for d in datasets}
        inserted = updated = 0
        with session_scope() as session:
            existing = {
                orm.dataset_id: orm
                for orm in session.execute(
                    select(ExternalDatasetOrm).where(
                        ExternalDatasetOrm.dataset_id.in_(batch.keys())
                    )
                ).scalars()
            }
            for dataset_id, dataset in batch.items():
                orm = existing.get(dataset_id)
                if orm is None:
                    session.add(to_orm(dataset))
                    inserted += 1
                else:
                    apply_to_orm(dataset, orm)
                    updated += 1
        return inserted, updated

    def get_by_id(self, dataset_id: str) -> ExternalDataset | None:
        with session_scope() as session:
            orm = session.get(ExternalDatasetOrm, dataset_id)
            return to_entity(orm) if orm is not None else None

    def list_all(self) -> list[ExternalDataset]:
        with session_scope() as session:
            orms = session.execute(
                select(ExternalDatasetOrm).order_by(ExternalDatasetOrm.dataset_id)
            ).scalars()
            return [to_entity(orm) for orm in orms]
