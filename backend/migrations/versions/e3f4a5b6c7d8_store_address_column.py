"""store address column

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-09-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """지오코딩 입력 주소. 원천에 좌표가 없는 업종(학원·부동산중개업)의 lat/lng 산출 근거."""
    op.add_column("store", sa.Column("address", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("store", "address")
