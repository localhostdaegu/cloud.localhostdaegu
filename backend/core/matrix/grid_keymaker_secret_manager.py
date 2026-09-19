"""전역 Secret 매니저 — .env / 환경변수를 단일 창구로 제공한다.

우선순위: OS 환경변수(도커 컴포즈 주입) > backend/.env (API 키 원본) > 루트 .env (도커 컴포즈 변수 치환용 POSTGRES_* 등).
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_ENV_FILES = (_BACKEND_DIR.parent / ".env", _BACKEND_DIR / ".env")  # 뒤가 우선


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        env_ignore_empty=True,  # backend/.env 의 빈 KEY= 자리표시자가 루트 .env 값을 가리지 않게
        extra="ignore",
    )

    database_url: str
    naver_ncp_api_key_id: str = ""
    naver_ncp_api_key: str = ""
    data_go_kr_api_key: str = ""
    bizinfo_api_key: str = ""
    youthcenter_api_key: str = ""
    seoul_open_data_api_key: str = ""
    childcare_api_key: str = ""  # 어린이집정보공개포털 (별도 키, 일 1,000회)
    neis_api_key: str = ""  # 나이스 교육정보 개방포털 — 학원교습소정보 (없으면 1회 5건 제한)
    ecos_api_key: str = ""
    rone_api_key: str = ""
    vworld_api_key: str = ""
    # 통계청 SGIS 오픈API — 지오코딩(브이월드는 결과 저장을 약관으로 금지해 영구 적재에 못 쓴다)
    sgis_service_id: str = ""
    sgis_security_key: str = ""
    # 브이월드 인증키에 등록된 서비스URL — 데이터·WFS API는 domain 불일치 시 INCORRECT_KEY
    vworld_service_domain: str = "beyondfacade.cloud"
    gemini_api_key: str = ""
    gemini_report_model: str = "gemini-3.8-flash"  # AI 리포트 생성 모델 — 환경변수 GEMINI_REPORT_MODEL 로 교체
    # 리포트 작성기 경로 — gemini(온라인) | ollama(오프라인). 오프라인 모델은 docs/model-evaluation.md 로 고른다.
    report_writer_provider: str = "gemini"
    ollama_report_model: str = "gemma4:12b"
    # RAG 질의 임베더 — 색인한 모델과 같아야 한다(embedded_by 필터). 오프라인 전환은 재색인 뒤 ollama.
    rag_embedding_provider: str = "gemini"
    region: str = "daegu"
    # 배포 오리진 — 쉼표 구분. 예: https://localhostdaegu.cloud,https://www.localhostdaegu.cloud
    cors_allow_origins: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
