"""Ollama Qwen3 임베딩 어댑터 — EmbeddingPort 구현.

Qwen3-Embedding-4B는 MRL(32~2560차원)을 지원한다. dimensions 기본 1536은 운영 DB
vector(1536)·기존 embedded_by 값과의 호환용이고, 네이티브 최고 차원은 2560이다.
"""

from apps.rag.adapter.outbound.embeddings.ollama_embedding_base import OllamaEmbeddingAdapterBase

QUERY_PROMPT = "Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: "


class OllamaQwen3EmbeddingAdapter(OllamaEmbeddingAdapterBase):
    """Ollama Qwen3 임베딩 어댑터 (쿼리 및 문서 벡터화)."""

    MODEL_NAME = "qwen3-embedding-4b-q4"
    OLLAMA_MODEL = "qwen3-embedding:4b"
    DIMENSIONS = 1536

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        transport=None,
        dimensions: int = DIMENSIONS,
    ):
        super().__init__(base_url=base_url, transport=transport)
        self.dimensions = dimensions

    @property
    def model_name(self) -> str:
        """모델명 — 기본 차원이 아니면 접미사로 차원을 밝힌다 (embedded_by 혼용 차단)."""
        if self.dimensions == self.DIMENSIONS:
            return self.MODEL_NAME
        return f"{self.MODEL_NAME}-{self.dimensions}d"

    def _query_text(self, text: str) -> str:
        return QUERY_PROMPT + text

    def _request_body(self, batch: list[str]) -> dict:
        return {"model": self.OLLAMA_MODEL, "input": batch, "dimensions": self.dimensions}
