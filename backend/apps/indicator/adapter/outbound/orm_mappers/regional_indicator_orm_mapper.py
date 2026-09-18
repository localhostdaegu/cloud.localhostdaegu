"""Outbound Boundary Gate — entity ↔ ORM 변환 (Repository ↔ DB 경계)."""

from apps.indicator.adapter.outbound.orms.regional_indicator_orm import RegionalIndicatorOrm
from apps.indicator.domain.entities.regional_indicator_entity import RegionalIndicator

# id(autoincrement)는 DB가 매기는 대리키 — 엔티티의 정체성은 아래 자연키다
_FIELDS = (
    "dataset_id",
    "region_code",
    "industry_id",
    "period",
    "indicator_key",
    "breakdown",
    "value",
    "unit",
)

# UNIQUE(… NULLS NOT DISTINCT) 구성 컬럼 — 업서트 충돌 판정의 기준
CONFLICT_KEY = (
    "dataset_id",
    "region_code",
    "industry_id",
    "period",
    "indicator_key",
    "breakdown",
)


def to_orm(entity: RegionalIndicator) -> RegionalIndicatorOrm:
    return RegionalIndicatorOrm(**{name: getattr(entity, name) for name in _FIELDS})


def to_entity(orm: RegionalIndicatorOrm) -> RegionalIndicator:
    return RegionalIndicator(**{name: getattr(orm, name) for name in _FIELDS})


def to_values(entity: RegionalIndicator) -> dict[str, object]:
    """PG 업서트(INSERT … ON CONFLICT)용 값 묶음 — 대량 적재라 ORM 인스턴스를 만들지 않는다."""
    return {name: getattr(entity, name) for name in _FIELDS}
