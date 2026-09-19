from datetime import datetime

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import HALFVEC

# FK 대상(마스터 허브) 테이블이 메타데이터에 항상 존재하도록 보장
import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class RagChunkOrm(OrmBase):
    """RAG 청크 — 임베딩 벡터(halfvec(2560)) + HNSW 인덱스.

    HNSW 인덱스는 vector 타입 2000차원 상한이 있어 2560은 fp16 halfvec 로 둔다(마이그레이션 c1d2e3f4a5b6).

    청크 저장소(chunk_id PK, source_type/source_id FK, embedding vector).
    임베딩된 청크는 embedded_by 필드로 어떤 모델이 생성했는지 추적.
    region_code FK로 행정동 단위 조회 가능.
    """

    __tablename__ = "rag_chunk"
    __table_args__ = (
        # 소스 기반 조회 (source_type + source_id 조합)
        Index("ix_rag_chunk_source", "source_type", "source_id"),
        # 코사인 유사도 ANN — 마이그레이션 c1d2e3f4a5b6와 동일 선언 (autogenerate가 drop하지 않도록)
        Index(
            "ix_rag_chunk_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "halfvec_cosine_ops"},
        ),
    )

    chunk_id: Mapped[str] = mapped_column(primary_key=True)  # unique chunk ID
    source_type: Mapped[str]  # 소스 유형 (예: "funding", "news")
    source_id: Mapped[str]  # 소스 ID (해당 테이블의 PK)
    content: Mapped[str]  # 청크 텍스트
    embedding: Mapped[list[float] | None] = mapped_column(HALFVEC(2560), nullable=True)  # 2560-dim — 온라인(Gemini)·오프라인(qwen) 공통 차원
    embedded_by: Mapped[str | None]  # 임베딩 모델명 (예: "gemini-embedding-001") — 검색 시 쿼리 임베더와 일치하는 행만 비교
    published_at: Mapped[datetime | None]  # 원본 발행 시간
    org: Mapped[str | None]  # 발행 기관/출처
    url: Mapped[str | None]  # 원본 URL
    region_code: Mapped[str | None] = mapped_column(ForeignKey("region.region_code"), nullable=True)
