"""수집 에이전트 (Strategy) — 각자 포트로 데이터를 모아 컨텍스트를 채우고 tool_call 이벤트를 낸다.

오케스트레이터(AnalysisInteractor)는 에이전트 종류를 모른 채 collect() 만 호출한다.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import ClassVar

from apps.analysis.app.ports.output.analysis_port import (
    EvidenceSearchPort,
    MarketDataPort,
    ProductMatchingPort,
    SimulationPort,
)
from apps.analysis.domain.agent_event import ToolCallEvent
from apps.analysis.domain.analysis_context import AnalysisContext

NEWS_TOP_K = 5
FUNDING_TOP_K = 5


def _with_question(base: str, ctx: AnalysisContext) -> str:
    return " ".join(part for part in (base, ctx.request.question) if part)


class AnalysisAgent(ABC):
    name: ClassVar[str]  # 프론트 AgentName: market | shock | funding

    @abstractmethod
    def collect(self, ctx: AnalysisContext) -> Iterator[ToolCallEvent]:
        """데이터를 모아 ctx 를 채우며 도구 호출마다 이벤트를 낸다."""


class MarketAgent(AnalysisAgent):
    name = "market"

    def __init__(self, market: MarketDataPort) -> None:
        self._market = market

    def collect(self, ctx: AnalysisContext) -> Iterator[ToolCallEvent]:
        ctx.market = self._market.fetch(ctx.request.region, ctx.request.industry, ctx.request.year)
        yield ToolCallEvent(
            agent=self.name,
            tool="region_metrics",
            summary=f"{ctx.region_label} {ctx.industry_label} 점포수·폐업률·성장률 조회",
        )
        yield ToolCallEvent(agent=self.name, tool="risk_score", summary="위험도 스코어(폐업·밀집·성장) 조회")


class ShockAgent(AnalysisAgent):
    name = "shock"

    def __init__(self, search: EvidenceSearchPort, region_name: str) -> None:
        self._search = search
        self._region_name = region_name

    def collect(self, ctx: AnalysisContext) -> Iterator[ToolCallEvent]:
        query = _with_question(f"{self._region_name} {ctx.industry_label} 소상공인 원가 금리 경기", ctx)
        ctx.news = self._search.search(query, "news", NEWS_TOP_K)
        yield ToolCallEvent(agent=self.name, tool="news_search", summary=f"뉴스 RAG 검색 — {len(ctx.news)}건")


class FundingAgent(AnalysisAgent):
    name = "funding"

    def __init__(
        self,
        search: EvidenceSearchPort,
        simulation: SimulationPort,
        matching: ProductMatchingPort,
        region_name: str,
    ) -> None:
        self._search = search
        self._simulation = simulation
        self._matching = matching
        self._region_name = region_name

    def collect(self, ctx: AnalysisContext) -> Iterator[ToolCallEvent]:
        # finance 는 선택 입력이다 — 있으면 시뮬레이션을 돌려 상품을 매칭하고,
        # 없으면 둘 다 건너뛴다. 누락 재무를 0원으로 간주해 후보를 구하지 않는다
        # (전환계획 §3-1, 타입/상태 분기가 아닌 입력 유무 분기).
        if ctx.request.finance is not None:
            ctx.simulation = self._simulation.simulate(ctx.request.finance)
            # 비교 원본도 서버에서 다시 계산한다 — 클라이언트가 보낸 결과를 기준으로 삼지 않는다(§5-1).
            # SSE 이벤트 종류는 그대로 둔다.
            baseline = ctx.request.consultation.baseline_finance if ctx.request.consultation else None
            if baseline is not None:
                ctx.baseline_simulation = self._simulation.simulate(baseline)
            yield ToolCallEvent(
                agent=self.name,
                tool="finance_simulate",
                summary=f"재무 시뮬레이션 — 조달 필요 {ctx.external_funding_need:,}원",
            )
            ctx.products = self._matching.match(ctx.external_funding_need, ctx.request.industry)
            yield ToolCallEvent(
                agent=self.name, tool="product_matching", summary=f"금융상품 매칭 — {len(ctx.products)}건"
            )
        query = _with_question(f"{self._region_name} {ctx.industry_label} 소상공인 창업 정책자금 보증 대출", ctx)
        ctx.funding_docs = self._search.search(query, "funding", FUNDING_TOP_K)
        yield ToolCallEvent(
            agent=self.name,
            tool="funding_search",
            summary=f"정책자금 공고 RAG 검색 — {len(ctx.funding_docs)}건",
        )
