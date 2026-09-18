from datetime import datetime

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상 테이블이 메타데이터에 항상 존재하도록 보장
import apps.consultation.adapter.outbound.orms.consultation_plan_orm  # noqa: F401
import apps.consultation.adapter.outbound.orms.consultation_session_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class ConsultationDocumentOrm(OrmBase):
    """생성된 상담자료 — 어떤 선택안(plan_id)으로 만든 자료인지 함께 남긴다.

    `content_hash`는 sha256(content_markdown)이며 **내용 변경 여부 확인용**이다.
    블록체인 앵커링은 이번 범위에서 구현하지 않으며, 이 컬럼의 존재를 블록체인 연동으로
    설명하지 않는다 (problem.md §8-1은 앵커링을 선택·후속 항목으로 둔다).
    """

    __tablename__ = "consultation_document"
    __table_args__ = (
        # 세션별 생성 이력 조회
        Index("ix_consultation_document_session_generated", "session_id", "generated_at"),
    )

    document_id: Mapped[str] = mapped_column(primary_key=True)  # uuid4 hex
    session_id: Mapped[str] = mapped_column(ForeignKey("consultation_session.session_id"))
    plan_id: Mapped[str] = mapped_column(ForeignKey("consultation_plan.plan_id"))
    purpose: Mapped[str]  # review(AI 계획 점검) / handoff(최종 상담자료)
    generated_at: Mapped[datetime]
    content_markdown: Mapped[str]
    content_hash: Mapped[str]  # sha256(content_markdown)
