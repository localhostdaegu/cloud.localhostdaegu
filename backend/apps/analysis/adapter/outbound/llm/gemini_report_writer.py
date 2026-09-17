"""Driven Adapter — Gemini 스트리밍 생성으로 ReportWriterPort 구현.

thinking_budget=0: 해석 문단 수준이라 추론 토큰 없이 첫 토큰 지연을 줄인다(gemini-3.8-flash에서 수용 실측
2026-09-17 — 모델을 바꾸면 해당 모델의 thinking 설정 지원 여부를 확인할 것).
"""

from collections.abc import Iterator

from google.genai import types

from apps.analysis.app.ports.output.analysis_port import ReportWriterPort

_TEMPERATURE = 0.3
_MAX_OUTPUT_TOKENS = 1024


class GeminiReportWriter(ReportWriterPort):
    def __init__(self, client, model: str) -> None:
        self._client = client
        self._model = model

    def stream(self, system: str, prompt: str) -> Iterator[str]:
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=_TEMPERATURE,
            max_output_tokens=_MAX_OUTPUT_TOKENS,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )
        for chunk in self._client.models.generate_content_stream(
            model=self._model, contents=prompt, config=config
        ):
            if chunk.text:
                yield chunk.text
