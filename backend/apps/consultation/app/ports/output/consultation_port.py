"""Driven Port — consultation이 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod

from apps.consultation.domain.entities.consultation_entity import (
    ConsultationNote,
    ConsultationPlan,
    ConsultationSession,
)


class ConsultationRepositoryPort(ABC):
    """상담 세션 애그리게이트의 저장소 (Aggregate Root = ConsultationSession).

    **읽기 제약:** `ConsultationPlan`의 계산 결과 8필드는 감사·재현용 스냅샷이다.
    리포트 생성 경로가 이 값을 읽어 리포트의 기준으로 삼아서는 안 된다 (전환계획 §5-3).
    """

    @abstractmethod
    def create_session(self, session: ConsultationSession) -> None:
        """세션을 저장한다. 프로필의 None은 None 그대로 기록한다 (0·False 변환 금지)."""

    @abstractmethod
    def find_session(self, session_id: str) -> ConsultationSession | None:
        """세션 1건. 없으면 None."""

    @abstractmethod
    def list_plans(self, session_id: str) -> list[ConsultationPlan]:
        """세션의 계획안 전부 (plan_kind 오름차순 — baseline, current)."""

    @abstractmethod
    def list_notes(self, session_id: str) -> list[ConsultationNote]:
        """세션의 가정·미확인 항목 전부 (note_type, note_order 오름차순)."""

    @abstractmethod
    def upsert_plan(self, plan: ConsultationPlan) -> ConsultationPlan:
        """(session_id, plan_kind) 기준 멱등 upsert — 갱신 시 기존 plan_id를 유지한다."""
