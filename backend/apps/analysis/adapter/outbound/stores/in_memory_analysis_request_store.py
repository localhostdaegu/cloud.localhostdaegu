"""Driven Adapter — 프로세스 메모리 요청 저장소.

POST(보관) → GET(1회 소비) 사이만 산다. 단일 uvicorn 워커 전제 — 다중 워커 배포 시 Redis 어댑터로 교체.
"""

import threading
from uuid import uuid4

from apps.analysis.app.ports.output.analysis_port import AnalysisRequestStorePort
from apps.analysis.domain.analysis_context import AnalysisRequest


class InMemoryAnalysisRequestStore(AnalysisRequestStorePort):
    def __init__(self) -> None:
        self._requests: dict[str, AnalysisRequest] = {}
        self._lock = threading.Lock()

    def save(self, request: AnalysisRequest) -> str:
        analysis_id = uuid4().hex
        with self._lock:
            self._requests[analysis_id] = request
        return analysis_id

    def take(self, analysis_id: str) -> AnalysisRequest | None:
        with self._lock:
            return self._requests.pop(analysis_id, None)
