from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_oracle_database_manager import OrmBase


class FinanceProductOrm(OrmBase):
    """금융상품 정본 — data/manual/*.json 은 시드 입력이다(스펙 §2).

    상담 메타데이터(1:1)·절차(1:N)·업종(M:N)은 별도 테이블로 분리한다.
    """

    __tablename__ = "finance_product"
    __table_args__ = (
        Index("ix_finance_product_provider_type", "provider_type"),
    )

    product_id: Mapped[str] = mapped_column(primary_key=True)  # "imbank-1" 등 수기 슬러그
    provider: Mapped[str]  # "iM뱅크" / "대구신용보증재단"
    provider_type: Mapped[str]  # bank / guarantee / policy (matcher._PRIORITY 키)
    product_name: Mapped[str]
    target: Mapped[str]  # 지원대상 원문 (LLM 구조화 추출 원천)
    region: Mapped[str]  # "전국 (iM뱅크 영업점 취급)" 등 원문
    business_age_min: Mapped[int | None]
    business_age_max: Mapped[int | None]
    owner_age_max: Mapped[int | None]
    loan_limit: Mapped[int | None]  # 원 단위
    interest_rate: Mapped[float | None]  # 연 %
    guarantee_fee: Mapped[float | None]  # 연 %
    url: Mapped[str]
    source_url: Mapped[str]
    # JSON category 의 None(업종 무관) ↔ [](해당 업종 없음) 구분 보존 — finance_product_rules 참조
    category_restricted: Mapped[bool] = mapped_column(default=False)
    source_file: Mapped[str]  # 시드 출처 파일명 — 재시드·대조 추적
