"""OllamaQwen3EmbeddingAdapter 임베딩 검증 — httpx.MockTransport 기반."""

import json

import httpx
import pytest

from apps.rag.adapter.outbound.embeddings.ollama_qwen3_adapter import (
    OllamaQwen3EmbeddingAdapter,
    QUERY_PROMPT,
)


def _transport(captured):
    """MockTransport: /api/embed 요청 바디 캡처."""
    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={"embeddings": [[3.0, 4.0] + [0.0] * 2558]})
    return httpx.MockTransport(handler)


def test_query_embedding_applies_instruct_prefix_and_dims():
    """embed_query: QUERY_PROMPT 프리픽스 + dimensions=2560(운영 차원)."""
    captured = []
    adapter = OllamaQwen3EmbeddingAdapter(transport=_transport(captured))
    vec = adapter.embed_query("카페 지원")
    assert captured[0]["input"] == [QUERY_PROMPT + "카페 지원"]
    assert captured[0]["dimensions"] == 2560
    assert abs(sum(v * v for v in vec) - 1.0) < 1e-6  # L2 정규화


def test_document_embedding_has_no_prefix():
    """embed_documents: 프리픽스 없음."""
    captured = []
    OllamaQwen3EmbeddingAdapter(transport=_transport(captured)).embed_documents(["문서"])
    assert captured[0]["input"] == ["문서"]


def test_fp16_adapter_does_not_load_model_on_init():
    """Fp16Qwen3EmbeddingAdapter: 인스턴스 생성이 모델을 로드하지 않음 (GPU 미점유 원칙)."""
    pytest.importorskip("sentence_transformers")
    from apps.rag.adapter.outbound.embeddings.fp16_qwen3_adapter import Fp16Qwen3EmbeddingAdapter

    adapter = Fp16Qwen3EmbeddingAdapter()
    assert adapter._model is None
    assert adapter.model_name == "qwen3-embedding-4b-fp16"
    assert adapter.provider == "local"


class _FakeEmbedding:
    def __init__(self, values):
        self.values = values


class _FakeEmbedResult:
    def __init__(self, count):
        self.embeddings = [_FakeEmbedding([0.0] * 2560) for _ in range(count)]


def test_gemini_adapter_class_attributes():
    """GeminiEmbeddingAdapter: model_name·provider 확인."""
    from apps.rag.adapter.outbound.embeddings.gemini_embedding_adapter import GeminiEmbeddingAdapter

    adapter = GeminiEmbeddingAdapter(api_key="test-key")
    assert adapter.model_name == "gemini-embedding-001"
    assert adapter.provider == "gemini"


def test_gemini_adapter_splits_250_inputs_into_3_batches(monkeypatch):
    """GeminiEmbeddingAdapter: 배치 100 제한 → 250개 입력이 3회 호출로 분할."""
    from apps.rag.adapter.outbound.embeddings.gemini_embedding_adapter import GeminiEmbeddingAdapter

    adapter = GeminiEmbeddingAdapter(api_key="test-key")
    captured_batches = []

    def fake_embed_content(model, contents, config):
        captured_batches.append(contents)
        return _FakeEmbedResult(len(contents))

    monkeypatch.setattr(adapter._client.models, "embed_content", fake_embed_content)

    texts = [f"문서 {i}" for i in range(250)]
    vectors = adapter.embed_documents(texts)

    assert len(captured_batches) == 3
    assert [len(batch) for batch in captured_batches] == [100, 100, 50]
    assert len(vectors) == 250


def test_gemini_adapter_retries_5xx_server_error_then_succeeds(monkeypatch):
    """GeminiEmbeddingAdapter: 일시적 5xx(ServerError)도 429처럼 백오프 재시도한다."""
    from google.genai import errors

    from apps.rag.adapter.outbound.embeddings import gemini_embedding_adapter as module

    adapter = module.GeminiEmbeddingAdapter(api_key="test-key")
    calls = []
    sleeps = []

    def flaky_embed_content(model, contents, config):
        calls.append(contents)
        if len(calls) == 1:
            raise errors.ServerError(503, {"error": {"code": 503, "message": "unavailable"}})
        return _FakeEmbedResult(len(contents))

    monkeypatch.setattr(adapter._client.models, "embed_content", flaky_embed_content)
    monkeypatch.setattr(module.time, "sleep", sleeps.append)

    vectors = adapter.embed_documents(["문서"])

    assert len(calls) == 2
    assert len(sleeps) == 1
    assert len(vectors) == 1


def test_gemini_adapter_does_not_retry_non_429_client_error(monkeypatch):
    """4xx(429 제외)는 재시도해도 풀리지 않는다 — 즉시 전파."""
    from google.genai import errors

    from apps.rag.adapter.outbound.embeddings import gemini_embedding_adapter as module

    adapter = module.GeminiEmbeddingAdapter(api_key="test-key")
    calls = []

    def bad_request(model, contents, config):
        calls.append(contents)
        raise errors.ClientError(400, {"error": {"code": 400, "message": "bad request"}})

    monkeypatch.setattr(adapter._client.models, "embed_content", bad_request)
    monkeypatch.setattr(module.time, "sleep", lambda _: None)

    with pytest.raises(errors.ClientError):
        adapter.embed_documents(["문서"])
    assert len(calls) == 1


def test_gemini_adapter_logger_uses_project_namespace():
    from apps.rag.adapter.outbound.embeddings.gemini_embedding_adapter import LOGGER

    assert LOGGER.name == "localhostdaegu.rag.embedding"


# ---------- 차원 지정·bge-m3 어댑터 (로컬/외부 임베더 비교 평가용) ----------


def test_qwen_adapter_accepts_reduced_1536_dimensions():
    """OllamaQwen3EmbeddingAdapter(dimensions=1536): 요청 바디 dimensions·model_name 접미사(기본 2560이 아닐 때만)."""
    captured = []

    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={"embeddings": [[1.0] + [0.0] * 1535]})

    adapter = OllamaQwen3EmbeddingAdapter(dimensions=1536, transport=httpx.MockTransport(handler))
    vec = adapter.embed_documents(["문서"])[0]
    assert captured[0]["dimensions"] == 1536
    assert len(vec) == 1536
    assert adapter.model_name == "qwen3-embedding-4b-q4-1536d"


def test_qwen_adapter_default_model_name_is_unchanged():
    """기본 2560은 접미사 없는 모델명 — DB embedded_by 값과 같아야 한다."""
    adapter = OllamaQwen3EmbeddingAdapter(transport=_transport([]))
    assert adapter.model_name == "qwen3-embedding-4b-q4"


def test_bge_m3_adapter_sends_no_prefix_and_no_dimensions():
    """bge-m3는 1024 고정·instruct 프리픽스 없음 — dimensions 키를 보내지 않는다."""
    from apps.rag.adapter.outbound.embeddings.ollama_bge_m3_adapter import (
        OllamaBgeM3EmbeddingAdapter,
    )

    captured = []

    def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={"embeddings": [[3.0, 4.0] + [0.0] * 1022]})

    adapter = OllamaBgeM3EmbeddingAdapter(transport=httpx.MockTransport(handler))
    vec = adapter.embed_query("카페 지원")
    assert captured[0]["model"] == "bge-m3"
    assert captured[0]["input"] == ["카페 지원"]
    assert "dimensions" not in captured[0]
    assert len(vec) == 1024
    assert abs(sum(v * v for v in vec) - 1.0) < 1e-6
    assert adapter.model_name == "bge-m3"
    assert adapter.provider == "ollama"


def test_gemini_adapter_output_dimensionality_is_configurable(monkeypatch):
    """GeminiEmbeddingAdapter(output_dimensionality=1536): config 전달·model_name 접미사(기본 2560이 아닐 때만)."""
    from apps.rag.adapter.outbound.embeddings.gemini_embedding_adapter import GeminiEmbeddingAdapter

    adapter = GeminiEmbeddingAdapter(api_key="test-key", output_dimensionality=1536)
    configs, models = [], []

    def fake_embed_content(model, contents, config):
        configs.append(config)
        models.append(model)
        return _FakeEmbedResult(len(contents))

    monkeypatch.setattr(adapter._client.models, "embed_content", fake_embed_content)
    adapter.embed_query("질의")
    assert configs[0].output_dimensionality == 1536
    assert models[0] == "gemini-embedding-001"  # API 모델 ID에는 차원 접미사가 붙으면 안 된다
    assert adapter.model_name == "gemini-embedding-001-1536d"
    assert GeminiEmbeddingAdapter(api_key="test-key").model_name == "gemini-embedding-001"


def test_registry_exposes_bge_m3_provider():
    """레지스트리에 bge-m3가 등록돼 provider 문자열로 고를 수 있다."""
    from apps.rag.adapter.outbound.embeddings.ollama_bge_m3_adapter import (
        OllamaBgeM3EmbeddingAdapter,
    )
    from apps.rag.dependencies.rag_dependencies import _INDEX_EMBEDDER_REGISTRY

    assert _INDEX_EMBEDDER_REGISTRY["bge-m3"] is OllamaBgeM3EmbeddingAdapter
