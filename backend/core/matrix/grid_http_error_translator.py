"""외부 API 오류 번역 (Exception translation) — httpx 오류 메시지의 API 키 노출 차단.

httpx 오류 문자열은 전체 URL(쿼리스트링의 crtfcKey·serviceKey·apiKeyNm·KEY 등)을 담아
수집기 traceback → 크론 로그로 키가 샌다(2026-09-18 funding-collector.log 실사례).
게이트웨이 경계에서 상태코드·메서드·경로만 남긴 예외로 바꾸고 원 예외 연결(__context__)도 끊는다.
"""

from collections.abc import Iterable, Iterator
from contextlib import contextmanager

import httpx


class ExternalApiError(RuntimeError):
    """쿼리스트링을 제거한 외부 API 호출 실패."""


def _where(request: httpx.Request) -> str:
    return f"{request.method} {request.url.host}{request.url.path}"


def _redact(text: str, secrets: Iterable[str]) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


@contextmanager
def translate_http_errors(secrets: Iterable[str] = ()) -> Iterator[None]:
    """secrets: 쿼리스트링이 아니라 URL 경로 세그먼트에 키가 실리는 원천(예: 서울 열린데이터광장)을 위한
    보조 가림 — 지정한 문자열을 메시지에서 '***'로 치환한다. 기존 호출부(인자 생략)는 그대로 동작."""
    try:
        yield
    except httpx.HTTPStatusError as error:
        raise ExternalApiError(_redact(f"HTTP {error.response.status_code} — {_where(error.request)}", secrets)) from None
    except httpx.RequestError as error:
        raise ExternalApiError(_redact(f"{type(error).__name__} — {_where(error.request)}", secrets)) from None
