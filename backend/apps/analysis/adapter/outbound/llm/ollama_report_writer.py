"""Driven Adapter — Ollama /api/chat 스트리밍으로 ReportWriterPort 구현 (오프라인 경로).

Gemini 작성기와 같은 생성 조건(temperature 0.3·최대 1024토큰·추론 토큰 차단)을 둔다.
think=false 는 thinking 모델(gemma4 등)의 추론 토큰을 막고, 비-thinking 모델도 오류 없이 받는다(2026-09-18 실측).
"""

import json
from collections.abc import Iterator

import httpx

from apps.analysis.app.ports.output.analysis_port import ReportWriterPort

_TEMPERATURE = 0.3
_MAX_OUTPUT_TOKENS = 1024


class OllamaReportWriter(ReportWriterPort):
    def __init__(self, model: str, base_url: str = "http://127.0.0.1:11434", transport=None) -> None:
        self.model = model
        # 콜드스타트(모델 로드·GPU 상주 교체)와 긴 생성을 감안해 넉넉히 잡는다
        self._client = httpx.Client(base_url=base_url, transport=transport, timeout=300.0)
        self.last_stats: dict = {}  # 마지막 응답의 done 프레임 통계(eval_count·eval_duration 등) — 평가용

    def stream(self, system: str, prompt: str) -> Iterator[str]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "stream": True,
            "think": False,
            "options": {"temperature": _TEMPERATURE, "num_predict": _MAX_OUTPUT_TOKENS},
        }
        with self._client.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                frame = json.loads(line)
                if frame.get("done"):
                    self.last_stats = {k: v for k, v in frame.items() if k not in ("message", "model")}
                    break
                text = frame.get("message", {}).get("content", "")
                if text:
                    yield text
