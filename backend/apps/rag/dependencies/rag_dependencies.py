"""Composition Root (DIP) — RAG 색인·검색 UseCase 배선.

운영 코퍼스는 gemini-embedding-001로 색인돼 있어 색인·검색 기본 provider 모두 gemini다.
검색은 쿼리 임베더와 같은 모델이 색인한 청크만 비교한다(embedded_by 필터) — provider는
Factory Method 레지스트리(CLAUDE.md §5)로 if/elif 분기 없이 고른다.
"""

from apps.rag.adapter.outbound.embeddings.fp16_qwen3_adapter import Fp16Qwen3EmbeddingAdapter
from apps.rag.adapter.outbound.embeddings.gemini_embedding_adapter import (
    GeminiEmbeddingAdapter,
)
from apps.rag.adapter.outbound.embeddings.ollama_qwen3_adapter import (
    OllamaQwen3EmbeddingAdapter,
)
from apps.rag.adapter.outbound.gateways.rag_source_gateway import (
    FundingRagSourceGateway,
    NewsRagSourceGateway,
)
from apps.rag.adapter.outbound.repositories.rag_repository import SqlAlchemyRagRepository
from apps.rag.app.ports.input.rag_use_case import RagIndexUseCase, RagSearchUseCase
from apps.rag.app.use_cases.rag_interactor import RagIndexInteractor, RagSearchInteractor

# 색인 임베더 레지스트리 — provider 문자열 → 어댑터 클래스 (if/elif 대신 dict 디스패치)
_INDEX_EMBEDDER_REGISTRY = {
    "fp16": Fp16Qwen3EmbeddingAdapter,
    "ollama": OllamaQwen3EmbeddingAdapter,
    "gemini": GeminiEmbeddingAdapter,
}


def get_rag_search_use_case(provider: str = "gemini") -> RagSearchUseCase:
    """검색 UseCase. provider의 임베더가 색인한 청크만 검색된다(embedded_by 필터)."""
    embedder_cls = _INDEX_EMBEDDER_REGISTRY[provider]
    return RagSearchInteractor(
        embedder=embedder_cls(),
        repository=SqlAlchemyRagRepository(),
    )


def get_rag_index_use_case(provider: str = "gemini") -> RagIndexUseCase:
    embedder_cls = _INDEX_EMBEDDER_REGISTRY[provider]
    return RagIndexInteractor(
        embedder=embedder_cls(),
        repository=SqlAlchemyRagRepository(),
        sources=[FundingRagSourceGateway(), NewsRagSourceGateway()],
    )
