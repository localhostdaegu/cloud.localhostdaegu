"""Driving Port — consultation UseCase 인터페이스."""

from abc import ABC, abstractmethod

from apps.consultation.app.dtos.consultation_dto import (
    ConsultationDetailDto,
    ConsultationDocumentDto,
    ConsultationPlanDto,
    ConsultationSessionDto,
)


class ConsultationUseCase(ABC):
    @abstractmethod
    def myself(self) -> ConsultationDetailDto:
        """배선 검증용 — 하드코딩 데이터 왕복 (CLAUDE.md §12). DB에 접근하지 않는다."""

    @abstractmethod
    def start_session(self, draft: ConsultationSessionDto) -> str:
        """세션을 만들고 session_id(uuid4 hex)를 반환한다. 미입력 프로필은 None으로 저장한다."""

    @abstractmethod
    def get_session(self, session_id: str) -> ConsultationDetailDto | None:
        """세션 + 계획안 + 노트. 없는 session_id는 None — 라우터가 404로 옮긴다."""

    @abstractmethod
    def replace_session(self, session_id: str, draft: ConsultationSessionDto) -> bool:
        """세션 상태를 교체한다. 없는 세션이면 False — 라우터가 404 로 옮긴다."""

    @abstractmethod
    def save_document(
        self, session_id: str, plan_kind: str, purpose: str, content_markdown: str
    ) -> ConsultationDocumentDto | None:
        """생성된 상담자료를 남긴다. 세션이나 그 계획안이 없으면 None — 라우터가 404."""

    @abstractmethod
    def save_plan(
        self, session_id: str, plan_kind: str, plan: ConsultationPlanDto
    ) -> ConsultationPlanDto | None:
        """(session_id, plan_kind) 기준 멱등 upsert. 없는 session_id는 None을 반환한다."""
