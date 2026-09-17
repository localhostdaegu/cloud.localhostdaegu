"""analysis BC 도메인 예외 — 라우터가 잡아 404 에러 바디로 변환한다."""


class AnalysisNotFoundError(Exception):
    """존재하지 않거나 이미 스트림으로 소비된 analysis_id."""
