"""Gemini 임베딩 어댑터 — 온라인용 EmbeddingPort 구현.

1536차원 (foodrm 식품 법규 임베딩과 동일 규격).
"""

import logging
import time

from google import genai
from google.genai import errors, types

from apps.rag.app.ports.output.rag_port import EmbeddingPort
from core.matrix.grid_keymaker_secret_manager import get_settings

LOGGER = logging.getLogger("localhostdaegu.rag.embedding")

EMBEDDING_DIM = 1536
_GEMINI_BATCH_LIMIT = 100

# 429의 출처는 우리 호출량이 아니라 gemini-embedding 베이스 모델의 전역 공용 풀이다
# (global_embed_content_requests_per_minute_per_base_model). 2026-09-01 실측:
# 분당 20회에서 실패, 분당 164회 30연발은 전량 성공 — 분 단위 대기는 근거가 없다.
# 대개 1초 안에 풀리므로 짧게 시작하고, 긴 장애에도 촘촘히 재시도하도록 상한을 둔다.
_RETRY_BASE_DELAY = 0.5
_RETRY_MAX_DELAY = 4.0
_RETRY_BUDGET_SECONDS = 30.0


class GeminiEmbeddingAdapter(EmbeddingPort):
    """Gemini 임베딩 어댑터 — 쿼리 및 문서 벡터화 (배치 100 + 429·5xx 재시도)."""

    MODEL_NAME = "gemini-embedding-001"
    PROVIDER = "gemini"

    def __init__(
        self, api_key: str | None = None, output_dimensionality: int = EMBEDDING_DIM
    ) -> None:
        self._client = genai.Client(api_key=api_key or get_settings().gemini_api_key)
        # gemini-embedding-001은 MRL: 지정 차원 벡터 == 3072 벡터의 앞부분(2026-09-18 실측 cos 1.0)
        self._output_dimensionality = output_dimensionality

    @property
    def model_name(self) -> str:
        """모델명 — 기본 차원이 아니면 접미사로 차원을 밝힌다 (embedded_by 혼용 차단)."""
        if self._output_dimensionality == EMBEDDING_DIM:
            return self.MODEL_NAME
        return f"{self.MODEL_NAME}-{self._output_dimensionality}d"

    @property
    def provider(self) -> str:
        """제공자."""
        return self.PROVIDER

    def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), _GEMINI_BATCH_LIMIT):
            batch = texts[start : start + _GEMINI_BATCH_LIMIT]
            result = self._embed_batch_with_retry(batch, task_type)
            vectors.extend(e.values for e in result.embeddings)
        return vectors

    def _embed_batch_with_retry(self, batch: list[str], task_type: str):
        # 전역 공용 쿼터(429)·일시적 5xx 대비 — 지수 백오프로 예산 안에서 재시도
        waited = 0.0
        attempt = 0
        while True:
            try:
                return self._client.models.embed_content(
                    model=self.MODEL_NAME,  # API 모델 ID — 차원 접미사가 붙는 model_name과 구분
                    contents=batch,
                    config=types.EmbedContentConfig(
                        task_type=task_type,
                        output_dimensionality=self._output_dimensionality,
                    ),
                )
            except errors.ClientError as exc:
                if exc.code != 429:
                    raise  # 429 외 4xx는 재시도해도 풀리지 않는다
                waited = self._back_off_or_raise(exc, waited, attempt)
            except errors.ServerError as exc:
                waited = self._back_off_or_raise(exc, waited, attempt)
            attempt += 1

    @staticmethod
    def _back_off_or_raise(exc: errors.APIError, waited: float, attempt: int) -> float:
        """예산 안이면 대기 후 누적 대기시간을 돌려주고, 예산을 넘기면 원 예외를 올린다."""
        delay = min(_RETRY_BASE_DELAY * 2**attempt, _RETRY_MAX_DELAY)
        if waited + delay > _RETRY_BUDGET_SECONDS:
            LOGGER.warning(
                "임베딩 %s 재시도 예산 %.1fs 소진 (%d회) — 호출부가 폴백한다",
                exc.code,
                waited,
                attempt + 1,
            )
            raise exc
        time.sleep(delay)
        return waited + delay

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, task_type="RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], task_type="RETRIEVAL_QUERY")[0]
