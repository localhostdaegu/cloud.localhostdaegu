from dataclasses import replace

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

# 마스터 ORM 2종 — FK 대상 테이블이 같은 metadata 에 있어야 SQLAlchemy 가 FK 를 해석한다.
# (industry: finance_product_category, district: finance_product.district_code)
from apps.master.adapter.outbound.orms.district_orm import DistrictOrm  # noqa: F401
from apps.master.adapter.outbound.orms.industry_orm import IndustryOrm
from apps.product.adapter.outbound.orm_mappers.finance_product_orm_mapper import (
    apply_to_orm,
    to_category_orms,
    to_entity,
    to_metadata_orm,
    to_orm,
    to_step_orms,
)
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
from apps.product.app.ports.output.finance_product_port import FinanceProductRepositoryPort
from apps.product.domain.entities.finance_product_entity import FinanceProduct
from apps.product.domain.finance_product_rules import BANK_CONNECTIONS, STEP_TYPES
from core.matrix.grid_oracle_database_manager import session_scope


def _normalized(product: FinanceProduct) -> FinanceProduct:
    """비교용 정규화 — to_entity 의 복원 순서(category 정렬, 절차 (유형, 순서) 정렬)에 맞춘다."""
    return replace(
        product,
        category=None if product.category is None else sorted(product.category),
        procedure_steps=sorted(
            product.procedure_steps, key=lambda step: (step.step_type, step.step_order)
        ),
    )


def _validate(products: list[FinanceProduct], session: Session) -> None:
    """도메인 허용값 + industry 마스터 존재 검증 — 위반은 조용히 버리지 않고 실패시킨다(스펙 §2-2·§2-3)."""
    for product in products:
        if product.consultation is not None and product.consultation.bank_connection not in BANK_CONNECTIONS:
            raise ValueError(
                f"상품 {product.product_id}: 알 수 없는 bank_connection "
                f"{product.consultation.bank_connection!r}"
            )
        for step in product.procedure_steps:
            if step.step_type not in STEP_TYPES:
                raise ValueError(f"상품 {product.product_id}: 알 수 없는 step_type {step.step_type!r}")

    wanted = {industry_id for p in products for industry_id in (p.category or [])}
    if not wanted:
        return
    known = set(
        session.execute(
            select(IndustryOrm.industry_id).where(IndustryOrm.industry_id.in_(wanted))
        ).scalars()
    )
    unknown = sorted(wanted - known)
    if unknown:
        raise ValueError(f"industry 마스터에 없는 업종: {', '.join(unknown)}")


class SqlAlchemyFinanceProductRepository(FinanceProductRepositoryPort):
    def upsert(self, products: list[FinanceProduct]) -> tuple[int, int]:
        if not products:
            return 0, 0
        # dict — 같은 배치 안의 중복 product_id 제거 (funding·shock BC 관행)
        batch = {p.product_id: _normalized(p) for p in products}
        inserted = updated = 0
        with session_scope() as session:
            _validate(list(batch.values()), session)
            existing = {
                orm.product_id: orm
                for orm in session.execute(
                    select(FinanceProductOrm).where(
                        FinanceProductOrm.product_id.in_(batch.keys())
                    )
                ).scalars()
            }
            children = _load_children(session, batch.keys())
            for product_id, product in batch.items():
                orm = existing.get(product_id)
                if orm is None:
                    session.add(to_orm(product))
                    session.flush()  # FK 순서 보장 — 부모(finance_product) 먼저 INSERT
                    _add_children(session, product)
                    inserted += 1
                    continue
                if to_entity(orm, *children(product_id)) == product:
                    continue  # 내용 동일 — 무변경 (재시드 멱등)
                apply_to_orm(product, orm)
                _delete_children(session, product_id)
                session.flush()  # 교체 전 삭제 확정 — UNIQUE(product_id, step_type, step_order) 충돌 방지
                _add_children(session, product)
                updated += 1
        return inserted, updated

    def list_all(self) -> list[FinanceProduct]:
        with session_scope() as session:
            orms = list(
                session.execute(
                    select(FinanceProductOrm).order_by(FinanceProductOrm.product_id)
                ).scalars()
            )
            children = _load_children(session, [orm.product_id for orm in orms])
            return [to_entity(orm, *children(orm.product_id)) for orm in orms]


def _load_children(session: Session, product_ids):
    """자식 3테이블을 한 번씩 조회해 product_id → (업종, 메타데이터, 절차) 로 묶는다 (N+1 회피)."""
    product_ids = list(product_ids)
    categories: dict[str, list[FinanceProductCategoryOrm]] = {}
    steps: dict[str, list[ProductProcedureStepOrm]] = {}
    metadata: dict[str, ProductConsultationMetadataOrm] = {}
    if product_ids:
        for row in session.execute(
            select(FinanceProductCategoryOrm).where(
                FinanceProductCategoryOrm.product_id.in_(product_ids)
            )
        ).scalars():
            categories.setdefault(row.product_id, []).append(row)
        for row in session.execute(
            select(ProductProcedureStepOrm).where(
                ProductProcedureStepOrm.product_id.in_(product_ids)
            )
        ).scalars():
            steps.setdefault(row.product_id, []).append(row)
        for row in session.execute(
            select(ProductConsultationMetadataOrm).where(
                ProductConsultationMetadataOrm.product_id.in_(product_ids)
            )
        ).scalars():
            metadata[row.product_id] = row

    def children(product_id: str):
        return categories.get(product_id, []), metadata.get(product_id), steps.get(product_id, [])

    return children


def _add_children(session: Session, product: FinanceProduct) -> None:
    session.add_all(to_category_orms(product))
    session.add_all(to_step_orms(product))
    metadata_orm = to_metadata_orm(product)
    if metadata_orm is not None:
        session.add(metadata_orm)


def _delete_children(session: Session, product_id: str) -> None:
    for orm_class in (
        FinanceProductCategoryOrm,
        ProductProcedureStepOrm,
        ProductConsultationMetadataOrm,
    ):
        session.execute(delete(orm_class).where(orm_class.product_id == product_id))
