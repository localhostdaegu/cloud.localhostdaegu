"""외부 API 오류 번역 (Exception translation) — httpx 오류 메시지의 API 키 노출 차단.

httpx 오류 문자열은 전체 URL(쿼리스트링의 crtfcKey·serviceKey·apiKeyNm·KEY 등)을 담아
수집기 traceback → 크론 로그로 키가 샌다(2026-09-18 funding-collector.log 실사례).
게이트웨이 경계에서 상태코드·메서드·경로만 남긴 예외로 바꾸고 원 예외 연결(__context__)도 끊는다.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import httpx


class ExternalApiError(RuntimeError):
    """쿼리스트링을 제거한 외부 API 호출 실패."""


def _where(request: httpx.Request) -> str:
    return f"{request.method} {request.url.host}{request.url.path}"


@contextmanager
def translate_http_errors() -> Iterator[None]:
    try:
        yield
    except httpx.HTTPStatusError as error:
        raise ExternalApiError(f"HTTP {error.response.status_code} — {_where(error.request)}") from None
    except httpx.RequestError as error:
        raise ExternalApiError(f"{type(error).__name__} — {_where(error.request)}") from None
