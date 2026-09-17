"""Driven Adapter — rag BC 검색 결과(RagHit)를 EvidenceDoc 으로 변환 (ACL).

청크 content 는 "제목\\n본문" 형식(rag_chunk_entity.build_funding_chunk / build_news_chunk).
"""

from apps.analysis.app.ports.output.analysis_port import EvidenceSearchPort
from apps.analysis.domain.analysis_context import EvidenceDoc
from apps.rag.app.ports.input.rag_use_case import RagSearchUseCase
from apps.rag.domain.entities.rag_chunk_entity import RagHit

SNIPPET_CHARS = 300


def _to_doc(hit: RagHit) -> EvidenceDoc:
    title, _, body = hit.content.partition("\n")
    title = title.strip()
    return EvidenceDoc(
        source_type=hit.source_type,
        title=title,
        snippet=(body.strip() or title)[:SNIPPET_CHARS],
        url=hit.url,
        org=hit.org,
        published_at=hit.published_at.date().isoformat() if hit.published_at else None,
    )


class EvidenceSearchGateway(EvidenceSearchPort):
    def __init__(self, search_use_case: RagSearchUseCase) -> None:
        self._search = search_use_case

    def search(self, query: str, source_type: str, top_k: int) -> list[EvidenceDoc]:
        return [_to_doc(hit) for hit in self._search.search(query, top_k=top_k, source_type=source_type)]
