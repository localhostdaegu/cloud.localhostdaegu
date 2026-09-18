from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상 테이블이 메타데이터에 항상 존재하도록 보장
import apps.product.adapter.outbound.orms.finance_product_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class ProductProcedureStepOrm(OrmBase):
    """사전조건·신청절차·준비서류 1:N — 세 리스트가 (순서, 문자열)로 구조·접근이 같아 판별자 1테이블로 둔다.

    빈 준비서류는 행 0건이며, 화면에서 "공식 안내에서 준비서류 확인 필요"로 표시한다(전환계획 §5-2).
    """

    __tablename__ = "product_procedure_step"
    __table_args__ = (
        UniqueConstraint("product_id", "step_type", "step_order"),
    )

    step_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(
        ForeignKey("finance_product.product_id"), index=True
    )
    step_type: Mapped[str]  # prerequisite / application_step / document
    step_order: Mapped[int]  # 1부터 — 상품별 실제 순서 보존 (전환계획 §4-2)
    description: Mapped[str]
