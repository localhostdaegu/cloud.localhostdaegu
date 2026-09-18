"""Outbound Boundary Gate — entity ↔ ORM 변환 (Repository ↔ DB 경계)."""

from apps.dataset.adapter.outbound.orms.external_dataset_orm import ExternalDatasetOrm
from apps.dataset.domain.entities.external_dataset_entity import ExternalDataset

_FIELDS = (
    "dataset_id",
    "name",
    "provider",
    "source_channel",
    "period_start",
    "period_end",
    "aggregation_note",
    "restriction_note",
    "export_approved_on",
    "approval_ref",
    "source_url",
    "catalog_page",
)


def to_orm(entity: ExternalDataset) -> ExternalDatasetOrm:
    return ExternalDatasetOrm(**{name: getattr(entity, name) for name in _FIELDS})


def to_entity(orm: ExternalDatasetOrm) -> ExternalDataset:
    return ExternalDataset(**{name: getattr(orm, name) for name in _FIELDS})


def apply_to_orm(entity: ExternalDataset, orm: ExternalDatasetOrm) -> None:
    """업서트 갱신 — dataset_id(PK)는 동일하므로 나머지 출처 항목을 반출본 기준으로 맞춘다."""
    for name in _FIELDS:
        if name == "dataset_id":
            continue
        setattr(orm, name, getattr(entity, name))
