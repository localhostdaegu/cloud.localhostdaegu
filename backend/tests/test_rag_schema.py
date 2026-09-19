"""rag_chunk 스키마 — halfvec(2560) + HNSW 인덱스 (마이그레이션 c1d2e3f4a5b6)."""
from sqlalchemy import text
from core.matrix.grid_oracle_database_manager import session_scope

def test_rag_chunk_table_exists_with_halfvec_2560():
    with session_scope() as s:
        type_name = s.execute(text(
            "SELECT format_type(atttypid, atttypmod) FROM pg_attribute "
            "WHERE attrelid='rag_chunk'::regclass AND attname='embedding'"
        )).scalar()
    assert type_name == "halfvec(2560)"

def test_rag_chunk_hnsw_index_exists():
    with session_scope() as s:
        n = s.execute(text(
            "SELECT count(*) FROM pg_indexes WHERE tablename='rag_chunk' AND indexdef ILIKE '%hnsw%'"
        )).scalar()
    assert n == 1

def test_rag_chunk_orm_declares_hnsw_index_matching_migration():
    """ORM이 HNSW 인덱스를 선언해야 alembic autogenerate가 ix_rag_chunk_embedding_hnsw를 drop하지 않는다."""
    from apps.rag.adapter.outbound.orms.rag_chunk_orm import RagChunkOrm

    indexes = {index.name: index for index in RagChunkOrm.__table__.indexes}
    hnsw = indexes["ix_rag_chunk_embedding_hnsw"]
    assert [column.name for column in hnsw.columns] == ["embedding"]
    assert hnsw.dialect_options["postgresql"]["using"] == "hnsw"
    assert hnsw.dialect_options["postgresql"]["ops"] == {"embedding": "halfvec_cosine_ops"}
