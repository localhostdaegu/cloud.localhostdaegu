"""Composition Root (DIP) — analysis 포트에 어댑터를 주입한다.

lru_cache: 인메모리 요청 저장소가 POST↔GET 사이 상태를 들고 있으므로 프로세스당 1개 (단일 워커 전제).
"""

from functools import lru_cache

from google import genai

from apps.analysis.adapter.outbound.gateways.evidence_search_gateway import EvidenceSearchGateway
from apps.analysis.adapter.outbound.gateways.finance_gateways import (
    EngineSimulationGateway,
    ManualProductMatchingGateway,
)
from apps.analysis.adapter.outbound.gateways.market_data_gateway import MarketDataGateway
from apps.analysis.adapter.outbound.llm.gemini_report_writer import GeminiReportWriter
from apps.analysis.adapter.outbound.stores.in_memory_analysis_request_store import (
    InMemoryAnalysisRequestStore,
)
from apps.analysis.app.ports.input.analysis_use_case import AnalysisUseCase
from apps.analysis.app.use_cases.analysis_agents import FundingAgent, MarketAgent, ShockAgent
from apps.analysis.app.use_cases.analysis_interactor import AnalysisInteractor
from apps.analysis.app.use_cases.report_sections import default_sections
from apps.master.dependencies.region_dependencies import get_region_use_case
from apps.metric.dependencies.region_industry_metric_dependencies import get_risk_use_case
from apps.rag.dependencies.rag_dependencies import get_rag_search_use_case
from core.matrix.grid_keymaker_secret_manager import get_settings
from core.matrix.grid_region_config import REGION_NAME


@lru_cache
def get_analysis_use_case() -> AnalysisUseCase:
    settings = get_settings()
    # rag_chunk 는 전량 gemini-embedding-001 로 색인됨 — 질의 임베더도 같아야 한다 (기본 ollama 금지).
    search = EvidenceSearchGateway(get_rag_search_use_case(provider="gemini"))
    return AnalysisInteractor(
        store=InMemoryAnalysisRequestStore(),
        agents=[
            MarketAgent(MarketDataGateway(get_region_use_case(), get_risk_use_case())),
            ShockAgent(search, REGION_NAME),
            FundingAgent(search, EngineSimulationGateway(), ManualProductMatchingGateway(), REGION_NAME),
        ],
        sections=default_sections(REGION_NAME),
        writer=GeminiReportWriter(
            client=genai.Client(api_key=settings.gemini_api_key), model=settings.gemini_report_model
        ),
    )
