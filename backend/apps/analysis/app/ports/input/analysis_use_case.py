"""Driving Port — AI 분석 리포트 UseCase (POST 시작 → GET SSE 스트림)."""

from abc import ABC, abstractmethod
from collections.abc import Iterator

from apps.analysis.domain.agent_event import AgentEvent
from apps.analysis.domain.analysis_context import AnalysisRequest


class AnalysisUseCase(ABC):
    @abstractmethod
    def start(self, request: AnalysisRequest) -> str:
        """요청을 보관하고 analysis_id 를 돌려준다 (분석은 스트림 구독 시 실행)."""

    @abstractmethod
    def stream(self, analysis_id: str) -> Iterator[AgentEvent]:
        """요청을 1회 꺼내 이벤트 스트림을 돌려준다. 없으면 호출 즉시 AnalysisNotFoundError."""
