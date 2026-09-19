"""참고 문서 지역 적합성 — 다른 구·군만 가리키는 문서는 빼고, 구·군이 없는 문서는 남긴다."""

from apps.analysis.domain.analysis_context import EvidenceDoc
from apps.analysis.domain.district_relevance import keep_relevant

_NAMES = ["중구", "동구", "서구", "남구", "북구", "수성구", "달서구", "달성군"]


def _doc(title: str) -> EvidenceDoc:
    return EvidenceDoc(source_type="funding", title=title, snippet="", url=None, org=None, published_at=None)


def test_drops_other_districts_but_keeps_citywide_and_own():
    docs = [
        _doc("[대구] 수성구 2026년 소상공인 정책자금 이차보전"),
        _doc("[대구] 달성군 2026년 소상공인 경영안정자금"),
        _doc("[대구] 2026년 중소기업경영안정자금 지원계획"),
    ]
    assert [d.title for d in keep_relevant(docs, "달성군", _NAMES)] == [docs[1].title, docs[2].title]


def test_dalseo_is_not_counted_as_seo():
    docs = [_doc("대구 달서구 소상공인 특례보증")]
    assert keep_relevant(docs, "서구", _NAMES) == []
    assert keep_relevant(docs, "달서구", _NAMES) == docs


def test_unknown_district_keeps_everything():
    docs = [_doc("[대구] 수성구 공고")]
    assert keep_relevant(docs, None, _NAMES) == docs
