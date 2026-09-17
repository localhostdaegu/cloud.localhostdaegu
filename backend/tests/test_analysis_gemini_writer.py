"""GeminiReportWriter — 가짜 클라이언트로 요청 구성·빈 조각 필터 검증 (네트워크 없음)."""

from types import SimpleNamespace

from apps.analysis.adapter.outbound.llm.gemini_report_writer import GeminiReportWriter


class _FakeModels:
    def __init__(self, texts: list[str | None]) -> None:
        self._texts = texts
        self.kwargs: dict = {}

    def generate_content_stream(self, **kwargs):
        self.kwargs = kwargs
        return iter(SimpleNamespace(text=text) for text in self._texts)


def test_stream_yields_non_empty_text_chunks_in_order():
    models = _FakeModels(["가", None, "", "나"])
    writer = GeminiReportWriter(client=SimpleNamespace(models=models), model="gemini-test")

    assert list(writer.stream("시스템 지시", "사용자 프롬프트")) == ["가", "나"]


def test_stream_sends_model_prompt_system_instruction_and_disables_thinking():
    models = _FakeModels(["가"])
    writer = GeminiReportWriter(client=SimpleNamespace(models=models), model="gemini-test")

    list(writer.stream("시스템 지시", "사용자 프롬프트"))

    assert models.kwargs["model"] == "gemini-test"
    assert models.kwargs["contents"] == "사용자 프롬프트"
    config = models.kwargs["config"]
    assert config.system_instruction == "시스템 지시"
    assert config.thinking_config.thinking_budget == 0
