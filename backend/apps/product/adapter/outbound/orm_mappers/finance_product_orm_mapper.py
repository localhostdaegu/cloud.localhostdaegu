"""Outbound Boundary Gate — entity ↔ ORM 4테이블 조립/해체 (Repository ↔ DB 경계)."""

from apps.product.adapter.outbound.orms.finance_product_category_orm import (
    FinanceProductCategoryOrm,
)
from apps.product.adapter.outbound.orms.finance_product_orm import FinanceProductOrm
from apps.product.adapter.outbound.orms.product_consultation_metadata_orm import (
    ProductConsultationMetadataOrm,
)
from apps.product.adapter.outbound.orms.product_procedure_step_orm import (
    ProductProcedureStepOrm,
)
from apps.product.domain.entities.finance_product_entity import (
    ConsultationMetadata,
    FinanceProduct,
    ProcedureStep,
)
from apps.product.domain.finance_product_rules import decode_category, encode_category

_FIELDS = (
    "product_id",
    "provider",
    "provider_type",
    "product_name",
    "target",
    "region",
    "business_age_min",
    "business_age_max",
    "owner_age_max",
    "loan_limit",
    "interest_rate",
    "guarantee_fee",
    "url",
    "source_url",
    "source_file",
    "district_code",
)

_METADATA_FIELDS = (
    "bank_connection",
    "bank_connection_source_url",
    "business_registration_required",
    "verified_at",
)

_STEP_FIELDS = ("step_type", "step_order", "description")


def to_orm(entity: FinanceProduct) -> FinanceProductOrm:
    category_restricted, _ = encode_category(entity.category)
    return FinanceProductOrm(
        **{name: getattr(entity, name) for name in _FIELDS},
        category_restricted=category_restricted,
    )


def to_category_orms(entity: FinanceProduct) -> list[FinanceProductCategoryOrm]:
    _, industry_ids = encode_category(entity.category)
    return [
        FinanceProductCategoryOrm(product_id=entity.product_id, industry_id=industry_id)
        for industry_id in industry_ids
    ]


def to_metadata_orm(entity: FinanceProduct) -> ProductConsultationMetadataOrm | None:
    """미확인(consultation=None)이면 행을 만들지 않는다 — 스펙 §2-3."""
    if entity.consultation is None:
        return None
    return ProductConsultationMetadataOrm(
        product_id=entity.product_id,
        **{name: getattr(entity.consultation, name) for name in _METADATA_FIELDS},
    )


def to_step_orms(entity: FinanceProduct) -> list[ProductProcedureStepOrm]:
    return [
        ProductProcedureStepOrm(
            product_id=entity.product_id,
            **{name: getattr(step, name) for name in _STEP_FIELDS},
        )
        for step in entity.procedure_steps
    ]


def to_entity(
    orm: FinanceProductOrm,
    category_orms: list[FinanceProductCategoryOrm],
    metadata_orm: ProductConsultationMetadataOrm | None,
    step_orms: list[ProductProcedureStepOrm],
) -> FinanceProduct:
    return FinanceProduct(
        **{name: getattr(orm, name) for name in _FIELDS},
        category=decode_category(orm.category_restricted, (c.industry_id for c in category_orms)),
        consultation=None
        if metadata_orm is None
        else ConsultationMetadata(
            **{name: getattr(metadata_orm, name) for name in _METADATA_FIELDS}
        ),
        procedure_steps=sorted(
            (ProcedureStep(**{name: getattr(s, name) for name in _STEP_FIELDS}) for s in step_orms),
            key=lambda step: (step.step_type, step.step_order),
        ),
    )


def apply_to_orm(entity: FinanceProduct, orm: FinanceProductOrm) -> None:
    """업서트 갱신 — 자식 3테이블은 리포지토리가 행 교체로 처리한다."""
    for name in _FIELDS:
        setattr(orm, name, getattr(entity, name))
    orm.category_restricted, _ = encode_category(entity.category)
