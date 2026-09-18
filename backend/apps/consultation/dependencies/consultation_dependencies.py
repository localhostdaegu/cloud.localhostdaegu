"""Composition Root (DIP) — Port에 Adapter를 주입한다 (FastAPI Depends)."""

from apps.consultation.adapter.outbound.repositories.consultation_repository import (
    SqlAlchemyConsultationRepository,
)
from apps.consultation.app.ports.input.consultation_use_case import ConsultationUseCase
from apps.consultation.app.use_cases.consultation_interactor import ConsultationInteractor


def get_consultation_use_case() -> ConsultationUseCase:
    return ConsultationInteractor(repository=SqlAlchemyConsultationRepository())
