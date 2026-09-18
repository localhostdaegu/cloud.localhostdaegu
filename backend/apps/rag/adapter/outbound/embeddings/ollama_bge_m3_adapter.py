"""Ollama bge-m3 임베딩 어댑터 — 1024차원 고정, instruct 프리픽스 없음 (한국어 친화 로컬 후보)."""

from apps.rag.adapter.outbound.embeddings.ollama_embedding_base import OllamaEmbeddingAdapterBase


class OllamaBgeM3EmbeddingAdapter(OllamaEmbeddingAdapterBase):
    MODEL_NAME = "bge-m3"
    OLLAMA_MODEL = "bge-m3"
    DIMENSIONS = 1024

    @property
    def model_name(self) -> str:
        return self.MODEL_NAME

    def _request_body(self, batch: list[str]) -> dict:
        return {"model": self.OLLAMA_MODEL, "input": batch}
