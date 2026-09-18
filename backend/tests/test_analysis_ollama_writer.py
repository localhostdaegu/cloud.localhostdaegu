"""OllamaReportWriter — httpx.MockTransport로 요청 구성·스트림 조각 검증 (네트워크 없음)."""

import json

import httpx

from apps.analysis.adapter.outbound.llm.ollama_report_writer import OllamaReportWriter


def _ndjson(chunks: list[str], done_stats: dict | None = None) -> bytes:
    lines = [json.dumps({"message": {"role": "assistant", "content": c}, "done": False}) for c in chunks]
    lines.append(json.dumps({"message": {"role": "assistant", "content": ""}, "done": True, **(done_stats or {})}))
    return ("\n".join(lines) + "\n").encode()


def _writer(captured: list, chunks: list[str], model: str = "gemma4:12b") -> OllamaReportWriter:
    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, content=_ndjson(chunks))

    return OllamaReportWriter(model=model, transport=httpx.MockTransport(handler))


def test_stream_yields_non_empty_chunks_in_order():
    writer = _writer([], ["가", "", "나"])
    assert list(writer.stream("시스템", "프롬프트")) == ["가", "나"]


def test_stream_sends_system_prompt_options_and_disables_thinking():
    captured = []
    list(_writer(captured, ["가"]).stream("시스템 지시", "사용자 프롬프트"))
    body = captured[0]
    assert body["model"] == "gemma4:12b"
    assert body["messages"] == [
        {"role": "system", "content": "시스템 지시"},
        {"role": "user", "content": "사용자 프롬프트"},
    ]
    assert body["stream"] is True
    assert body["think"] is False
    assert body["options"] == {"temperature": 0.3, "num_predict": 1024}


def test_last_stats_records_eval_counts_from_done_frame():
    def handler(request):
        return httpx.Response(200, content=_ndjson(["가"], {"eval_count": 12, "eval_duration": 600_000_000}))

    writer = OllamaReportWriter(model="gemma4:12b", transport=httpx.MockTransport(handler))
    list(writer.stream("s", "p"))
    assert writer.last_stats["eval_count"] == 12
    assert writer.last_stats["eval_duration"] == 600_000_000


def test_registry_builds_writer_by_provider(monkeypatch):
    from apps.analysis.dependencies import analysis_dependencies as deps

    settings = deps.get_settings.__wrapped__()  # lru_cache 우회 — 실제 .env 값
    ollama = deps.build_report_writer("ollama", settings)
    assert isinstance(ollama, OllamaReportWriter)
    assert ollama.model == settings.ollama_report_model
    from apps.analysis.adapter.outbound.llm.gemini_report_writer import GeminiReportWriter

    assert isinstance(deps.build_report_writer("gemini", settings), GeminiReportWriter)
