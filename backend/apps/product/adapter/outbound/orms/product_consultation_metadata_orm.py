from datetime import date

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상 테이블이 메타데이터에 항상 존재하도록 보장
import apps.product.adapter.outbound.orms.finance_product_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class ProductConsultationMetadataOrm(OrmBase):
    """상품 원문 대조 기록 1:1 — 행이 없으면 '미확인'이다 (스펙 §2-3).

    bank_connection 허용값은 도메인 상수 BANK_CONNECTIONS 가 정하며 리포지토리 쓰기 경로에서 검증한다.
    DB CHECK 제약은 두지 않는다 — 값 추가가 마이그레이션을 유발하지 않게 한다.
    """

    __tablename__ = "product_consultation_metadata"

    product_id: Mapped[str] = mapped_column(
        ForeignKey("finance_product.product_id"), primary_key=True
    )
    bank_connection: Mapped[str]  # direct / linked / unverified / none
    bank_connection_source_url: Mapped[str | None]
    business_registration_required: Mapped[bool | None]  # None = 미확인 (추정 금지)
    verified_at: Mapped[date | None]  # 원문 확인일 — 접수 가능 보장이 아니다
