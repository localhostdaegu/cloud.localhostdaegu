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


# --- 전환계획 T4: 상담자료(handoff) 섹션 ------------------------------------


def _handoff_context():
    """선택안·비교 원본·상담 정보가 모두 있는 상담자료 컨텍스트."""
    from dataclasses import replace

    from apps.analysis.domain.analysis_context import ConsultationContext, ConsultationProfile

    ctx = full_context()
    ctx.request = replace(
        ctx.request,
        purpose="handoff",
        consultation=ConsultationContext(
            profile=ConsultationProfile(
                business_registered=False,
                planned_opening_date="2026-11-01",
                funds_needed_by="2026-10-15",
                policy_confirmation_status="in_progress",
            ),
            change_reason="월세가 낮은 자리로 바꿨습니다",
            assumptions=["원가율 35%는 업종 벤치마크 기본값"],
            open_questions=["설비 견적 미확정"],
        ),
    )
    ctx.simulation = SIMULATION
    ctx.baseline_simulation = replace(SIMULATION, external_funding_need=38_849_996, bep_revenue=6_000_000)
    return ctx


def test_handoff_sections_follow_the_consultation_order():
    from apps.analysis.app.use_cases.report_sections import sections_for

    assert [s.key for s in sections_for("handoff", "대구")] == [
        "plan", "comparison", "calculator", "funding", "questions", "market",
    ]


def test_review_keeps_the_existing_sections():
    from apps.analysis.app.use_cases.report_sections import sections_for

    assert [s.key for s in sections_for("review", "대구")] == [s.key for s in default_sections("대구")]


def test_plan_lead_states_the_selected_plan_numbers_and_change_reason():
    from apps.analysis.domain.report_text import plan_lead

    text = plan_lead(_handoff_context())

    assert "28,849,996원" in text  # 자기자본 외 조달 필요
    assert "월세가 낮은 자리로 바꿨습니다" in text


def test_comparison_is_written_by_code_without_the_llm():
    from apps.analysis.app.use_cases.report_sections import ComparisonSection

    writer = FakeWriter(chunks=("LLM 이 쓰면 안 된다",))
    chunks = list(ComparisonSection().render(_handoff_context(), writer))

    assert writer.calls == []
    assert "38,849,996원" in "".join(chunks)  # 최초안
    assert "28,849,996원" in "".join(chunks)  # 현재안


def test_comparison_says_so_when_there_is_nothing_to_compare():
    from apps.analysis.app.use_cases.report_sections import ComparisonSection

    ctx = _handoff_context()
    ctx.baseline_simulation = None

    assert "비교할 최초안이 없습니다" in "".join(list(ComparisonSection().render(ctx, FakeWriter())))


def test_questions_lead_keeps_unconfirmed_items_visible():
    """'모름'이 숫자 가정으로 바뀌면서 사라지지 않게 한다(§5-1)."""
    from apps.analysis.domain.report_text import questions_lead

    text = questions_lead(_handoff_context())

    assert "설비 견적 미확정" in text
    assert "원가율 35%는 업종 벤치마크 기본값" in text
    assert "보증" in text  # guarantee_status=unknown → 확인 대상


def test_calculator_shows_external_funding_need_not_only_the_gap():
    text = calculator_markdown(SIMULATION)

    assert "28,849,996원" in text
