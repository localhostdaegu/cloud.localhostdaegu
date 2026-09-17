"""리포트 텍스트 빌더 (순수 함수) — "결론 첫 줄은 LLM이 아니라 코드가 쓴다".

수치는 전부 여기서 포맷해 리포트에 직접 쓰고, LLM 프롬프트에는 이미 계산된 값만 넣는다
(LLM 수치 계산 금지 — docs/daegunavi.md §7).
"""

from apps.analysis.domain.agent_event import Citation
from apps.analysis.domain.analysis_context import AnalysisContext, EvidenceDoc, SimulationSummary

_GRADE_LABEL = {"red": "진입 주의", "yellow": "보통", "green": "양호"}
_CITATION_GRADE = {"funding": "fact", "news": "signal"}  # 공고=확인된 사실, 뉴스=참고 신호

FALLBACK_MARKDOWN = "\n\n_AI 해석을 생성하지 못했습니다. 위 수치와 참고 자료를 확인해 주세요._\n\n"


def system_instruction(region_name: str) -> str:
    return (
        f"너는 {region_name} 소상공인 창업 금융 컨설턴트다. "
        "사용자 메시지에 주어진 데이터와 문서만 근거로 한국어 마크다운으로 답한다. "
        "숫자는 주어진 값만 그대로 인용하고 새로 계산하거나 추정하지 않는다. "
        "문서에 없는 사실·상품명·금리는 만들지 않는다. "
        "제목(#)은 쓰지 않고, 요청한 분량을 넘기지 않는다."
    )


def _subject(ctx: AnalysisContext) -> str:
    return f"{ctx.region_label} {ctx.industry_label}"


def _grade_label(grade: str) -> str:
    return _GRADE_LABEL.get(grade, grade)


def _question(ctx: AnalysisContext) -> str:
    question = ctx.request.question
    return f"\n\n사용자 추가 질문(답변에 반영): {question}" if question else ""


def market_facts(ctx: AnalysisContext) -> str:
    cards = ", ".join(f"{c.label} {c.value}" for c in ctx.cards) or "지표 없음"
    risk = ctx.risk
    risk_text = (
        f"위험도 {risk.score:.1f}점(등급 {_grade_label(risk.grade)}, 구성 폐업 {risk.components['closure']}"
        f"·밀집 {risk.components['density']}·성장 {risk.components['growth']})"
        if risk
        else "위험도 데이터 없음"
    )
    return f"대상: {_subject(ctx)}\n상권 지표: {cards}\n{risk_text}"


def finance_facts(ctx: AnalysisContext) -> str:
    sim = ctx.simulation
    if sim is None:
        return "재무 시뮬레이션: 입력 없음"
    return (
        f"재무 시뮬레이션: 초기 투자 {sim.capex:,}원, 월 고정비 {sim.monthly_fixed:,}원, "
        f"손익분기 월매출 {sim.bep_revenue:,}원, 부족 자금 {sim.funding_gap:,}원"
    )


def _limit_text(limit: int | None) -> str:
    return f"{limit:,}원" if limit is not None else "미정"


def _rate_text(rate: float | None) -> str:
    return f"{rate}%" if rate is not None else "미정"


def products_text(ctx: AnalysisContext) -> str:
    lines = [
        f"- {p.provider} {p.product_name}: 한도 {_limit_text(p.loan_limit)}, 금리 {_rate_text(p.interest_rate)}"
        for p in ctx.products
    ]
    return "\n".join(lines) or "- 조건에 맞는 상품 없음"


def format_docs(docs: list[EvidenceDoc]) -> str:
    if not docs:
        return "(관련 문서 없음)"
    return "\n".join(
        f"[{i}] {d.title} ({d.org or '출처 미상'}, {d.published_at or '날짜 미상'})\n{d.snippet}"
        for i, d in enumerate(docs, start=1)
    )


def verdict_lead(ctx: AnalysisContext) -> str:
    risk = ctx.risk
    headline = f"위험도 {risk.score:.1f}점 — {_grade_label(risk.grade)}" if risk else "위험도 데이터 없음"
    return f"### 종합 진단\n\n**{_subject(ctx)} · {headline}**\n\n"


def market_lead(ctx: AnalysisContext) -> str:
    rows = [f"| {c.label} | {c.value} |" for c in ctx.cards]
    risk = ctx.risk
    if risk is not None:
        comps = risk.components
        rows.append(
            f"| 위험도 구성(폐업·밀집·성장) | {comps['closure']} · {comps['density']} · {comps['growth']} |"
        )
    table = "\n".join(["| 지표 | 값 |", "|---|---|", *rows]) if rows else "_상권 지표 데이터가 없습니다._"
    return f"### 상권 진단\n\n{table}\n\n"


def shock_lead(ctx: AnalysisContext) -> str:
    return "### 충격 분석\n\n"


def funding_lead(ctx: AnalysisContext) -> str:
    return f"### 정책자금\n\n**매칭 금융상품 (보증 → 은행 → 정책자금 순)**\n\n{products_text(ctx)}\n\n"


def verdict_prompt(ctx: AnalysisContext) -> str:
    return (
        f"{market_facts(ctx)}\n{finance_facts(ctx)}\n\n"
        "위 데이터로 이 창업 계획의 종합 판단을 3문장 이내로 써라. "
        "첫 문장은 위험 수준, 둘째 문장은 가장 큰 위험 변수, "
        "셋째 문장은 바꿔볼 만한 선택(입지·업종·자금 구성)이다." + _question(ctx)
    )


def market_prompt(ctx: AnalysisContext) -> str:
    return (
        f"{market_facts(ctx)}\n\n"
        "표의 지표가 창업자에게 무엇을 뜻하는지, 어떤 변수가 문제인지 불릿 3개 이내로 해석하라." + _question(ctx)
    )


def shock_prompt(ctx: AnalysisContext) -> str:
    return (
        f"대상: {_subject(ctx)}\n\n최근 뉴스:\n{format_docs(ctx.news)}\n\n"
        "이 업종·지역 창업에 영향을 줄 외부 충격(원가·금리·수요)을 불릿 3개 이내로 정리하고 "
        "근거 뉴스 번호를 [n] 형식으로 붙여라. 관련 뉴스가 없으면 없다고만 써라." + _question(ctx)
    )


def funding_prompt(ctx: AnalysisContext) -> str:
    return (
        f"대상: {_subject(ctx)}\n{finance_facts(ctx)}\n\n"
        f"매칭 금융상품:\n{products_text(ctx)}\n\n"
        f"정책자금·지원사업 공고:\n{format_docs(ctx.funding_docs)}\n\n"
        "자금 조달 경로를 보증 → 은행 → 정책자금 순서로 불릿 3개 이내로 제안하고 "
        "근거 공고 번호를 [n] 형식으로 붙여라." + _question(ctx)
    )


def _payback(months: float | None) -> str:
    return "회수 불가" if months is None else f"{months}개월"


def calculator_markdown(sim: SimulationSummary) -> str:
    rows = [
        f"| {s.name} | {s.monthly_revenue:,}원 | {s.operating_profit:,}원 | {_payback(s.payback_months)} |"
        for s in sim.scenarios
    ]
    return (
        "\n".join(
            [
                "### 재무 시뮬레이션",
                "",
                f"초기 투자 {sim.capex:,}원 · 월 고정비 {sim.monthly_fixed:,}원 · "
                f"손익분기 월매출 {sim.bep_revenue:,}원 · 부족 자금 {sim.funding_gap:,}원",
                "",
                "| 시나리오 | 월매출 | 영업이익 | 투자 회수 |",
                "|---|---|---|---|",
                *rows,
            ]
        )
        + "\n"
    )


def citations_from(ctx: AnalysisContext) -> list[Citation]:
    """공고 → 뉴스 순, URL 기준 중복 제거. URL 없는 문서는 링크를 못 걸어 제외."""
    by_url: dict[str, Citation] = {}
    for doc in [*ctx.funding_docs, *ctx.news]:
        if doc.url and doc.url not in by_url:
            by_url[doc.url] = Citation(
                title=doc.title, url=doc.url, grade=_CITATION_GRADE.get(doc.source_type, "signal")
            )
    return list(by_url.values())
