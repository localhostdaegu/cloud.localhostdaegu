"""Ollama /api/embed 공통 어댑터 베이스 — 배치 분할·L2 정규화 (Template Method).

모델별 차이(모델명·차원·쿼리 프리픽스)는 서브클래스가 `_request_body`·`_query_text`로 채운다.
"""

from abc import abstractmethod

import httpx

from apps.rag.app.ports.output.rag_port import EmbeddingPort


class OllamaEmbeddingAdapterBase(EmbeddingPort):
    PROVIDER = "ollama"
    BATCH_SIZE = 50

    def __init__(self, base_url: str = "http://127.0.0.1:11434", transport=None):
        self.base_url = base_url
        # 기본 httpx 타임아웃(5s)은 콜드스타트(모델 로드·GPU 상주 모델 교체) 실측 초과 —
        # 색인 배치는 최초 요청에서 모델 로딩을 겸하므로 넉넉히 잡는다.
        self.client = httpx.Client(base_url=base_url, transport=transport, timeout=120.0)

    @property
    def provider(self) -> str:
        return self.PROVIDER

    @abstractmethod
    def _request_body(self, batch: list[str]) -> dict:
        """/api/embed 요청 바디 — 모델명·차원 등 모델별 항목."""

    def _query_text(self, text: str) -> str:
        """쿼리 프리픽스 훅 — 기본은 원문 그대로."""
        return text

    def embed_query(self, text: str) -> list[float]:
        return self._embed_batch([self._query_text(text)])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed_batch(texts)

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        all_embeddings = []
        for i in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[i : i + self.BATCH_SIZE]
            response = self.client.post("/api/embed", json=self._request_body(batch))
            response.raise_for_status()
            for embedding in response.json().get("embeddings", []):
                all_embeddings.append(self._l2_normalize(embedding))
        return all_embeddings

    @staticmethod
    def _l2_normalize(vector: list[float]) -> list[float]:
        norm = sum(v * v for v in vector) ** 0.5
        if norm < 1e-10:
            return vector  # 제로 벡터는 그대로 반환
        return [v / norm for v in vector]
