"""SSE 이벤트 계약 — frontend/src/shared/api/types.ts 의 AgentEvent 와 필드명·값이 1:1.

각 이벤트가 자기 type 을 안다(분기 없이 to_payload 한 곳에서 직렬화).
"""

from dataclasses import asdict, dataclass, field
from typing import ClassVar


@dataclass(frozen=True)
class Citation:
    title: str
    url: str
    grade: str  # fact | signal — 프론트 GradeBadge 계약


@dataclass(frozen=True)
class AgentEvent:
    TYPE: ClassVar[str] = ""

    def to_payload(self) -> dict:
        return {"type": self.TYPE, **asdict(self)}


@dataclass(frozen=True)
class AgentStatusEvent(AgentEvent):
    TYPE: ClassVar[str] = "agent_status"
    agent: str
    status: str  # running | done | error


@dataclass(frozen=True)
class ToolCallEvent(AgentEvent):
    TYPE: ClassVar[str] = "tool_call"
    agent: str
    tool: str
    summary: str


@dataclass(frozen=True)
class ReportDeltaEvent(AgentEvent):
    TYPE: ClassVar[str] = "report_delta"
    section: str
    markdown: str


@dataclass(frozen=True)
class ReportDoneEvent(AgentEvent):
    TYPE: ClassVar[str] = "report_done"
    report_id: str
    citations: list[Citation] = field(default_factory=list)
