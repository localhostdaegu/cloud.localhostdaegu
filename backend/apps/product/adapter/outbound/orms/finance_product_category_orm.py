from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상 테이블이 메타데이터에 항상 존재하도록 보장
import apps.master.adapter.outbound.orms.industry_orm  # noqa: F401
import apps.product.adapter.outbound.orms.finance_product_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class FinanceProductCategoryOrm(OrmBase):
    """상품×업종 M:N — 행이 없는 것만으로는 '업종 무관'과 '해당 업종 없음'을 구분할 수 없다.

    구분은 finance_product.category_restricted 가 맡는다 (스펙 §2-2).
    """

    __tablename__ = "finance_product_category"

    product_id: Mapped[str] = mapped_column(
        ForeignKey("finance_product.product_id"), primary_key=True
    )
    industry_id: Mapped[str] = mapped_column(
        ForeignKey("industry.industry_id"), primary_key=True
    )
