"""compare_embedders 하네스 — 순수 함수(랭킹·교차 일치) 검증."""

import numpy as np

from apps.rag.adapter.inbound.cli.compare_embedders import (
    jaccard_at_k,
    rank_documents,
    spearman_rho,
    truncate_normalize,
)


def test_rank_documents_filters_by_source_type_and_orders_by_cosine():
    ids = ["funding:a", "news:b", "funding:c"]
    source_types = ["funding", "news", "funding"]
    docs = np.array([[1.0, 0.0], [0.0, 1.0], [0.6, 0.8]])
    query = np.array([0.0, 1.0])
    ranked = rank_documents(query, docs, ids, source_types, source_type="funding", top_k=5)
    assert ranked == ["funding:c", "funding:a"]  # news:b 제외, 코사인 내림차순


def test_jaccard_at_k():
    assert jaccard_at_k(["a", "b", "c"], ["b", "c", "d"], k=3) == 0.5
    assert jaccard_at_k(["a"], ["a"], k=5) == 1.0


def test_spearman_rho_perfect_and_reversed():
    assert abs(spearman_rho(np.array([3.0, 1.0, 2.0]), np.array([30.0, 10.0, 20.0])) - 1.0) < 1e-9
    assert abs(spearman_rho(np.array([1.0, 2.0, 3.0]), np.array([3.0, 2.0, 1.0])) + 1.0) < 1e-9


def test_truncate_normalize_keeps_prefix_and_unit_norm():
    vectors = np.array([[3.0, 4.0, 100.0]])
    out = truncate_normalize(vectors, 2)
    assert out.shape == (1, 2)
    assert np.allclose(out, [[0.6, 0.8]])
