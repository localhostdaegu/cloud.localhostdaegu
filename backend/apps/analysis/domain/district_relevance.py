"""참고 문서의 지역 적합성 — 다른 구·군만 가리키는 공고·기사를 뺀다 (순수 함수).

검색 질의는 '대구 ○○업 정책자금'이라 수성구 공고가 달성군 사용자에게도 올라온다(2026-09-19 페르소나 테스트).
제목에 구·군 이름이 없으면 대구 전체 대상으로 보고 남긴다.
"""

from apps.analysis.domain.analysis_context import EvidenceDoc


def _districts_in(title: str, names: list[str]) -> set[str]:
    """제목에 나온 구·군 — 긴 이름부터 지워 '달서구' 안의 '서구'를 따로 세지 않는다."""
    found, rest = set(), title
    for name in sorted(names, key=len, reverse=True):
        if name in rest:
            found.add(name)
            rest = rest.replace(name, "")
    return found


def keep_relevant(docs: list[EvidenceDoc], district_name: str | None, all_names: list[str]) -> list[EvidenceDoc]:
    if district_name is None:
        return docs
    return [
        doc
        for doc in docs
        if not (named := _districts_in(doc.title, all_names)) or district_name in named
    ]
