"""RagIndexInteractor·RagSearchInteractor — 색인/검색 오케스트레이션 (얇은 Application Service).

검색은 쿼리 임베더의 model_name으로 embedded_by를 걸러 같은 모델이 색인한 벡터끼리만 비교한다
(운영 코퍼스는 gemini-embedding-001 — 색인·검색 모두 gemini).
"""

from apps.rag.app.ports.input.rag_use_case import RagIndexUseCase, RagSearchUseCase
from apps.rag.app.ports.output.rag_port import EmbeddingPort, RagRepositoryPort, RagSourcePort
from apps.rag.domain.entities.rag_chunk_entity import RagHit

_EMBED_BATCH_SIZE = 32


class RagIndexInteractor(RagIndexUseCase):
    def __init__(
        self,
        embedder: EmbeddingPort,
        repository: RagRepositoryPort,
        sources: list[RagSourcePort],
    ) -> None:
        self._embedder = embedder
        self._repository = repository
        self._sources = sources

    def index(self, full: bool = False) -> int:
        processed = 0
        for source in self._sources:
            chunks = list(source.iter_chunks())
            if not chunks:
                continue
            if not full:
                existing = self._repository.existing_ids(chunks[0].source_type)
                chunks = [c for c in chunks if c.chunk_id not in existing]
            for start in range(0, len(chunks), _EMBED_BATCH_SIZE):
                batch = chunks[start : start + _EMBED_BATCH_SIZE]
                vectors = self._embedder.embed_documents([c.content for c in batch])
                for chunk, vector in zip(batch, vectors, strict=True):
                    chunk.embedding = vector
                    chunk.embedded_by = self._embedder.model_name
                processed += self._repository.upsert_chunks(batch)
        return processed


class RagSearchInteractor(RagSearchUseCase):
    def __init__(self, embedder: EmbeddingPort, repository: RagRepositoryPort) -> None:
        self._embedder = embedder
        self._repository = repository

    def search(
        self, query: str, top_k: int = 5, source_type: str | None = None
    ) -> list[RagHit]:
        embedding = self._embedder.embed_query(query)
        return self._repository.search(embedding, self._embedder.model_name, top_k, source_type)
