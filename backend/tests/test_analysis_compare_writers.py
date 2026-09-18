"""compare_report_writers 하네스 — 결정론 게이트(순수 함수) 검증."""

from apps.analysis.adapter.inbound.cli.compare_report_writers import (
    count_bullets,
    count_questions,
    count_sentences,
    direction_ok,
    foreign_numbers,
    hangul_ratio,
    has_bracket_citation,
    has_heading,
    unknown_citations,
)


def test_heading_and_bracket_detection():
    assert has_heading("# 제목\n본문")
    assert not has_heading("본문에 # 기호는 괜찮다")
    assert has_bracket_citation("근거 [1]")
    assert not has_bracket_citation("근거 「제목」")


def test_bullet_sentence_question_counts():
    assert count_bullets("- 하나\n* 둘\n1. 셋\n본문") == 3
    assert count_sentences("위험도 5.2점으로 높다. 폐업률이 문제다! 자금을 늘려라") == 3
    assert count_questions("- 금리는 얼마인가요?\n- 한도를 확인해 주세요.\n- 서류는?") == 2


def test_foreign_numbers_ignores_prompt_numbers_and_single_digits():
    prompt = "초기 투자 40,000,000원, 위험도 5.2점"
    assert foreign_numbers("투자 4000만원과 5.2점, 3문장", prompt) == []
    assert foreign_numbers("금리 4.5%와 한도 30,000,000원", prompt) == ["4.5", "30000000"]


def test_unknown_citations_matches_by_substring():
    titles = ["iM뱅크, 추석 특별자금 1조원 푼다…중소기업·소상공인 지원"]
    assert unknown_citations("근거「iM뱅크 추석 특별자금」", titles) == []  # 쉼표 생략은 정당
    assert unknown_citations("근거「iM뱅크 명절 대출 확대」", titles) == ["iM뱅크 명절 대출 확대"]
    assert unknown_citations("근거「iM뱅크, 추석 특별자금 1조원 푼다」", titles) == []
    # 괄호·쉼표를 뺀 인용도 정당하다 / 너무 짧은 인용(6자 미만)은 제목 대조가 불가능해 위반으로 본다
    bracketed = ["[내년 최저임금 1만700원] 대구 소상공인·외식업계 “인건비 부담”"]
    assert unknown_citations("「내년 최저임금 1만700원 대구 소상공인·외식업계 인건비 부담」", bracketed) == []
    assert unknown_citations("「월세 부담」", ["월세 부담 커진 대구 상가"]) == ["월세 부담"]


def test_hangul_ratio_and_direction():
    assert hangul_ratio("한글 abc") == 2 / 5
    assert direction_ok("이 계획은 진입 주의가 필요하다. 다음.", "red")
    assert not direction_ok("이 계획은 양호하다. 다음.", "red")
    assert direction_ok("상권이 안정적이다.", "green")
