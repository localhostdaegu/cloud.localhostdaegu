"""AnalysisInteractor — 오케스트레이터 (얇은 Application Service).

순서(프론트 mock SSE 와 동일): orchestrator running → 에이전트별 running/tool_call/done
→ 섹션별 report_delta → orchestrator done → report_done.
에이전트 하나가 실패해도 error 상태만 알리고 계속 — 스트림은 항상 report_done 으로 끝난다.
"""

import logging
from collections.abc import Iterator

from apps.analysis.app.ports.input.analysis_use_case import AnalysisUseCase
from apps.analysis.app.ports.output.analysis_port import AnalysisRequestStorePort, ReportWriterPort
from apps.analysis.app.use_cases.analysis_agents import AnalysisAgent
from apps.analysis.app.use_cases.report_sections import ReportSection
from apps.analysis.domain.agent_event import AgentEvent, AgentStatusEvent, ReportDeltaEvent, ReportDoneEvent
from apps.analysis.domain.analysis_context import AnalysisContext, AnalysisRequest
from apps.analysis.domain.errors import AnalysisNotFoundError
from apps.analysis.domain.report_text import citations_from

LOGGER = logging.getLogger("localhostdaegu.analysis")

ORCHESTRATOR = "orchestrator"


class AnalysisInteractor(AnalysisUseCase):
    def __init__(
        self,
        store: AnalysisRequestStorePort,
        agents: list[AnalysisAgent],
        sections: list[ReportSection],
        writer: ReportWriterPort,
    ) -> None:
        self._store = store
        self._agents = agents
        self._sections = sections
        self._writer = writer

    def start(self, request: AnalysisRequest) -> str:
        return self._store.save(request)

    def stream(self, analysis_id: str) -> Iterator[AgentEvent]:
        # 제너레이터가 아닌 일반 메서드 — 404 판단을 응답 시작 전에 끝내기 위해 take 를 즉시 수행한다.
        request = self._store.take(analysis_id)
        if request is None:
            raise AnalysisNotFoundError(analysis_id)
        return self._run(AnalysisContext(analysis_id=analysis_id, request=request))

    def _run(self, ctx: AnalysisContext) -> Iterator[AgentEvent]:
        yield AgentStatusEvent(agent=ORCHESTRATOR, status="running")
        for agent in self._agents:
            yield from self._collect(agent, ctx)
        for section in self._sections:
            for markdown in section.render(ctx, self._writer):
                yield ReportDeltaEvent(section=section.key, markdown=markdown)
        yield AgentStatusEvent(agent=ORCHESTRATOR, status="done")
        yield ReportDoneEvent(report_id=ctx.analysis_id, citations=citations_from(ctx))

    def _collect(self, agent: AnalysisAgent, ctx: AnalysisContext) -> Iterator[AgentEvent]:
        yield AgentStatusEvent(agent=agent.name, status="running")
        try:
            yield from agent.collect(ctx)
        except Exception:
            LOGGER.exception("분석 에이전트 %s 실패 — 나머지로 계속", agent.name)
            yield AgentStatusEvent(agent=agent.name, status="error")
            return
        yield AgentStatusEvent(agent=agent.name, status="done")
