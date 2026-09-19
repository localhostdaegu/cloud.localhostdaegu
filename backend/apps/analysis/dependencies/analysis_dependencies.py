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
from apps.analysis.adapter.outbound.llm.ollama_report_writer import OllamaReportWriter
from apps.analysis.adapter.outbound.stores.in_memory_analysis_request_store import (
    InMemoryAnalysisRequestStore,
)
from apps.analysis.app.ports.input.analysis_use_case import AnalysisUseCase
from apps.analysis.app.ports.output.analysis_port import ReportWriterPort
from apps.analysis.app.use_cases.analysis_agents import FundingAgent, MarketAgent, ShockAgent
from apps.analysis.app.use_cases.analysis_interactor import AnalysisInteractor
from apps.analysis.app.use_cases.report_sections import sections_for
from apps.master.dependencies.region_dependencies import get_region_use_case
from apps.metric.dependencies.region_industry_metric_dependencies import get_risk_use_case
from apps.rag.dependencies.rag_dependencies import get_rag_search_use_case
from core.matrix.grid_keymaker_secret_manager import Settings, get_settings
from core.matrix.grid_region_config import REGION_NAME

# 리포트 작성기 레지스트리 — provider 문자열 → 팩토리 (온라인 gemini / 오프라인 ollama, if/elif 대신 dict)
_REPORT_WRITER_REGISTRY = {
    "gemini": lambda s: GeminiReportWriter(
        client=genai.Client(api_key=s.gemini_api_key), model=s.gemini_report_model
    ),
    "ollama": lambda s: OllamaReportWriter(model=s.ollama_report_model),
}


def build_report_writer(provider: str, settings: Settings) -> ReportWriterPort:
    return _REPORT_WRITER_REGISTRY[provider](settings)


def build_agents(settings: Settings | None = None) -> list:
    """수집 에이전트 3종 — 운영과 평가 하네스(compare_report_writers)가 같은 배선을 쓴다."""
    settings = settings or get_settings()
    # 질의 임베더는 색인한 모델과 같아야 한다(embedded_by 필터). 기본 gemini, 오프라인 시연은 재색인 뒤
    # RAG_EMBEDDING_PROVIDER=ollama (docs/model-evaluation.md §11 절차).
    search = EvidenceSearchGateway(get_rag_search_use_case(provider=settings.rag_embedding_provider))
    return [
        MarketAgent(MarketDataGateway(get_region_use_case(), get_risk_use_case())),
        ShockAgent(search, REGION_NAME),
        FundingAgent(search, EngineSimulationGateway(), ManualProductMatchingGateway(), REGION_NAME),
    ]


@lru_cache
def get_analysis_use_case() -> AnalysisUseCase:
    settings = get_settings()
    return AnalysisInteractor(
        store=InMemoryAnalysisRequestStore(),
        agents=build_agents(settings),
        sections=lambda purpose: sections_for(purpose, REGION_NAME),
        writer=build_report_writer(settings.report_writer_provider, settings),
    )
