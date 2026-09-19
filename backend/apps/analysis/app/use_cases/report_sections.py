"""리포트 섹션 (Strategy) — 섹션마다 무엇을 어떻게 쓰는지 스스로 안다.

InterpretedSection 은 Template Method: 코드가 쓰는 첫머리(수치) → LLM 해석 스트림.
lead·prompt·LLM 스트림 어느 단계가 실패해도 폴백 문구로 섹션을 닫아 스트림이 report_done 까지 가게 한다.
"""

import logging
from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import ClassVar

from apps.analysis.app.ports.output.analysis_port import ReportWriterPort
from apps.analysis.domain.analysis_context import AnalysisContext
from apps.analysis.domain.report_text import (
    FALLBACK_MARKDOWN,
    calculator_markdown,
    comparison_markdown,
    funding_lead,
    funding_prompt,
    has_market_data,
    market_lead,
    market_prompt,
    plan_lead,
    plan_prompt,
    questions_lead,
    questions_prompt,
    shock_lead,
    shock_prompt,
    system_instruction,
    verdict_lead,
    verdict_prompt,
)

LOGGER = logging.getLogger("localhostdaegu.analysis")


class ReportSection(ABC):
    key: ClassVar[str]  # 프론트 ReportView SECTION_ORDER 값

    @abstractmethod
    def render(self, ctx: AnalysisContext, writer: ReportWriterPort) -> Iterator[str]:
        """이 섹션의 markdown 조각들."""


class InterpretedSection(ReportSection):
    def __init__(self, system: str) -> None:
        self._system = system

    def render(self, ctx: AnalysisContext, writer: ReportWriterPort) -> Iterator[str]:
        try:
            yield self.lead(ctx)
            yield from writer.stream(self._system, self.prompt(ctx))
        except Exception:
            LOGGER.exception("리포트 섹션 %s LLM 생성 실패 — 폴백 문구로 대체", self.key)
            yield FALLBACK_MARKDOWN

    @abstractmethod
    def lead(self, ctx: AnalysisContext) -> str:
        """코드가 쓰는 첫머리 (제목·수치)."""

    @abstractmethod
    def prompt(self, ctx: AnalysisContext) -> str:
        """LLM 사용자 프롬프트."""


class VerdictSection(InterpretedSection):
    key = "verdict"

    def lead(self, ctx: AnalysisContext) -> str:
        return verdict_lead(ctx)

    def prompt(self, ctx: AnalysisContext) -> str:
        return verdict_prompt(ctx)


class MarketSection(InterpretedSection):
    key = "market"

    def render(self, ctx: AnalysisContext, writer: ReportWriterPort) -> Iterator[str]:
        # 해석할 지표가 없으면 LLM 을 부르지 않는다 — 부르면 "데이터가 없다"는 문장만 되풀이한다.
        if not has_market_data(ctx):
            yield self.lead(ctx)
            return
        yield from super().render(ctx, writer)

    def lead(self, ctx: AnalysisContext) -> str:
        return market_lead(ctx)

    def prompt(self, ctx: AnalysisContext) -> str:
        return market_prompt(ctx)


class ShockSection(InterpretedSection):
    key = "shock"

    def lead(self, ctx: AnalysisContext) -> str:
        return shock_lead(ctx)

    def prompt(self, ctx: AnalysisContext) -> str:
        return shock_prompt(ctx)


class FundingSection(InterpretedSection):
    key = "funding"

    def lead(self, ctx: AnalysisContext) -> str:
        return funding_lead(ctx)

    def prompt(self, ctx: AnalysisContext) -> str:
        return funding_prompt(ctx)


class CalculatorSection(ReportSection):
    """재무 입력이 있을 때만 결정론 계산표 — LLM 호출 없음."""

    key = "calculator"

    def render(self, ctx: AnalysisContext, writer: ReportWriterPort) -> Iterator[str]:
        # ctx.simulation 유무는 타입/상태 분기가 아니라 선택 입력(재무 정보) 존재 여부 확인이다.
        if ctx.simulation is not None:
            yield calculator_markdown(ctx.simulation)


class PlanSection(InterpretedSection):
    """상담할 계획 — 수치는 코드가 쓰고 LLM 은 상태 설명만 한다(§6 T4)."""

    key = "plan"

    def lead(self, ctx: AnalysisContext) -> str:
        return plan_lead(ctx)

    def prompt(self, ctx: AnalysisContext) -> str:
        return plan_prompt(ctx)


class ComparisonSection(ReportSection):
    """최초안·현재안 비교표 — 결정론 계산 결과만 쓴다. LLM 호출 없음."""

    key = "comparison"

    def render(self, ctx: AnalysisContext, writer: ReportWriterPort) -> Iterator[str]:
        yield comparison_markdown(ctx)


class QuestionsSection(InterpretedSection):
    """확인 사항은 코드가 나열하고, 상담 질문만 LLM 이 쓴다."""

    key = "questions"

    def lead(self, ctx: AnalysisContext) -> str:
        return questions_lead(ctx)

    def prompt(self, ctx: AnalysisContext) -> str:
        return questions_prompt(ctx)


def default_sections(region_name: str) -> list[ReportSection]:
    system = system_instruction(region_name)
    return [
        VerdictSection(system),
        MarketSection(system),
        ShockSection(system),
        FundingSection(system),
        CalculatorSection(),
    ]


def handoff_sections(region_name: str) -> list[ReportSection]:
    """상담자료 — 선택안·비교·자금이 앞, 위험 판정 헤드라인은 두지 않는다(§3-1)."""
    system = system_instruction(region_name)
    return [
        PlanSection(system),
        ComparisonSection(),
        CalculatorSection(),
        FundingSection(system),
        QuestionsSection(system),
        MarketSection(system),
    ]


# 목적 → 섹션 구성 (Factory). 목적이 늘어도 분기문을 고치지 않는다.
_SECTION_PLANS = {"review": default_sections, "handoff": handoff_sections}


def sections_for(purpose: str, region_name: str) -> list[ReportSection]:
    return _SECTION_PLANS.get(purpose, default_sections)(region_name)
