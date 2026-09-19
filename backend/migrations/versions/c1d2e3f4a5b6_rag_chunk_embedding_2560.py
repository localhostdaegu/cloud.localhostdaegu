"""rag_chunk.embedding vector(1536) -> halfvec(2560) — 온라인(Gemini)·오프라인(qwen) 임베딩 차원 통일

Revision ID: c1d2e3f4a5b6
Revises: 079cb96619ca
Create Date: 2026-09-19

2026-09-18 가용성 평가(docs/model-evaluation.md): 로컬 대체 임베더 qwen3-embedding:4b의 네이티브 차원이 2560이고
Gemini는 MRL이라 차원 손실이 없어(§6), 운영 컬럼을 2560으로 맞춘다 — 오프라인 시연 전환 시 스키마를 건드리지 않게.
pgvector HNSW 인덱스는 vector 타입에서 2000차원까지만 지원한다(실측: "column cannot have more than 2000
dimensions for hnsw index"). 2560은 fp16 halfvec(인덱스 4000차원까지)으로 저장한다 — 코사인 검색 정밀도 차이는 무시할 수준.
차원이 바뀌면 기존 벡터는 못 쓰므로 embedding·embedded_by를 비우고 전량 재색인한다
(python -m apps.rag.adapter.inbound.cli.build_rag_index --full --provider gemini).
"""

import pgvector.sqlalchemy
import sqlalchemy as sa
from alembic import op

revision = "c1d2e3f4a5b6"
down_revision = "079cb96619ca"
branch_labels = None
depends_on = None


def _retype(type_, ops: str) -> None:
    op.drop_index("ix_rag_chunk_embedding_hnsw", table_name="rag_chunk")
    # 차원이 다른 기존 벡터는 형 변환이 실패한다 — 비우고 재색인 대상으로 남긴다(embedded_by도 함께)
    op.execute("UPDATE rag_chunk SET embedding = NULL, embedded_by = NULL")
    op.alter_column("rag_chunk", "embedding", type_=type_, existing_nullable=True, postgresql_using="NULL")
    op.execute(f"CREATE INDEX ix_rag_chunk_embedding_hnsw ON rag_chunk USING hnsw (embedding {ops})")


def upgrade() -> None:
    _retype(pgvector.sqlalchemy.HALFVEC(dim=2560), "halfvec_cosine_ops")


def downgrade() -> None:
    _retype(pgvector.sqlalchemy.vector.VECTOR(dim=1536), "vector_cosine_ops")
