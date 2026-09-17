"""리포트 섹션 — 코드 첫머리 + LLM 스트림, LLM 실패 폴백, 계산표 조건부 출력."""

from apps.analysis.app.use_cases.report_sections import CalculatorSection, VerdictSection, default_sections
from apps.analysis.domain.analysis_context import AnalysisContext
from apps.analysis.domain.report_text import FALLBACK_MARKDOWN, calculator_markdown, verdict_lead, verdict_prompt
from tests.analysis_fakes import SIMULATION, FailingWriter, FakeWriter, full_context


def test_default_sections_follow_frontend_section_order():
    assert [s.key for s in default_sections("대구")] == ["verdict", "market", "shock", "funding", "calculator"]


def test_interpreted_section_yields_code_lead_then_llm_chunks():
    ctx = full_context()
    writer = FakeWriter(chunks=("첫 조각", "둘째 조각"))

    chunks = list(VerdictSection("시스템").render(ctx, writer))

    assert chunks == [verdict_lead(ctx), "첫 조각", "둘째 조각"]
    assert writer.calls == [("시스템", verdict_prompt(ctx))]


def test_interpreted_section_falls_back_when_llm_fails_mid_stream():
    ctx = full_context()

    chunks = list(VerdictSection("시스템").render(ctx, FailingWriter()))

    assert chunks == [verdict_lead(ctx), "부분", FALLBACK_MARKDOWN]


def test_interpreted_section_falls_back_when_lead_raises():
    """PF1: lead(ctx) 가 예외를 던져도 스트림이 죽지 않고 폴백 문구로 닫혀야 한다."""

    class ExplodingLeadSection(VerdictSection):
        def lead(self, ctx: AnalysisContext) -> str:
            raise RuntimeError("lead 실패")

    chunks = list(ExplodingLeadSection("시스템").render(full_context(), FakeWriter()))

    assert chunks == [FALLBACK_MARKDOWN]


def test_default_sections_pass_region_system_instruction_to_writer():
    writer = FakeWriter()
    list(default_sections("대구")[0].render(full_context(), writer))
    assert "대구" in writer.calls[0][0]


def test_calculator_section_renders_table_without_llm_when_simulated():
    writer = FakeWriter()
    assert list(CalculatorSection().render(full_context(), writer)) == [calculator_markdown(SIMULATION)]
    assert writer.calls == []


def test_calculator_section_renders_nothing_without_simulation():
    ctx = full_context()
    ctx.simulation = None
    assert list(CalculatorSection().render(ctx, FakeWriter())) == []
