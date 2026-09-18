"""finance_product district_code

Revision ID: 079cb96619ca
Revises: b93358fab70e
Create Date: 2026-09-18 18:46:08.575905

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '079cb96619ca'
down_revision: Union[str, Sequence[str], None] = 'b93358fab70e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_FK = "fk_finance_product_district_code"


def upgrade() -> None:
    """자치구 한정 상품용 nullable FK. 기존 행은 NULL = 지역 제한 없음."""
    op.add_column("finance_product", sa.Column("district_code", sa.String(), nullable=True))
    op.create_foreign_key(_FK, "finance_product", "district", ["district_code"], ["district_code"])


def downgrade() -> None:
    # 제약 이름을 명시하지 않으면 롤백이 실패한다.
    op.drop_constraint(_FK, "finance_product", type_="foreignkey")
    op.drop_column("finance_product", "district_code")
