"""CORS 허용 오리진 조립 — 로컬 개발 오리진 + 환경변수로 받은 운영 오리진.

배포 시 `CORS_ALLOW_ORIGINS=https://localhostdaegu.cloud` 처럼 쉼표로 넘긴다.
하드코딩하면 배포한 프론트가 백엔드를 부르지 못한다.
"""

_LOCAL_ORIGINS = ("http://localhost:3300", "http://127.0.0.1:3300")


def allowed_origins(configured: str) -> list[str]:
    """로컬 오리진은 항상 허용하고, 설정값을 뒤에 붙인다. 빈 항목·중복은 버린다."""
    origins: list[str] = []
    for origin in (*_LOCAL_ORIGINS, *configured.split(",")):
        cleaned = origin.strip()
        if cleaned and cleaned not in origins:
            origins.append(cleaned)
    return origins
