from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상 테이블이 메타데이터에 항상 존재하도록 보장
import apps.consultation.adapter.outbound.orms.consultation_session_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class ConsultationNoteOrm(OrmBase):
    """가정(assumption) · 미확인 항목(open_question)의 1NF 저장소.

    전환계획 §5-1: *"단계폼에서 '모름'을 선택한 사실이 숫자 가정으로 바뀌면서 사라지지 않게 한다."*
    `note_order`로 사용자가 남긴 순서를 보존한다.
    """

    __tablename__ = "consultation_note"
    __table_args__ = (UniqueConstraint("session_id", "note_type", "note_order"),)

    note_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("consultation_session.session_id"), index=True
    )
    note_type: Mapped[str]  # assumption(가정·출처) / open_question(미확인 항목)
    note_order: Mapped[int]
    content: Mapped[str]
