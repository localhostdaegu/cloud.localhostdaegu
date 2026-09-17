from datetime import date


def last_complete_year(latest_record_date: date) -> int:
    """원천 최신 기록일이 속한 연도는 집계 중인 부분 연도 — 그 직전 해가 마지막 완결 연도다.

    연도 미지정 조회(사이드패널 카드·위험도)의 기본값. 부분 연도를 연간 지표처럼 보여주지 않기 위함.
    """
    return latest_record_date.year - 1
