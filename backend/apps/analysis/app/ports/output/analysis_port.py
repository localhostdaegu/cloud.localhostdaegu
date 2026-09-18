"""Driven Ports — analysis 가 바깥 세계에 요구하는 계약 (ISP: 역할별 분리)."""

from abc import ABC, abstractmethod
from collections.abc import Iterator

from apps.analysis.domain.analysis_context import (
    AnalysisRequest,
    EvidenceDoc,
    MarketSnapshot,
    MatchedProduct,
    SimulationSummary,
)


class MarketDataPort(ABC):
    @abstractmethod
    def fetch(
        self, region_code: str, industry_id: str, year: int | None = None
    ) -> MarketSnapshot | None:
        """행정동×업종 상권 지표·위험도. 미등록 행정동이면 None.

        year 미지정이면 마지막 완결 연도 — 지도에서 고른 연도를 그대로 넘겨
        화면과 리포트의 기준연도를 맞춘다(§7-3).
        """


class EvidenceSearchPort(ABC):
    @abstractmethod
    def search(self, query: str, source_type: str, top_k: int) -> list[EvidenceDoc]:
        """RAG 문서 검색 — source_type: funding | news."""


class SimulationPort(ABC):
    @abstractmethod
    def simulate(self, finance: dict) -> SimulationSummary:
        """결정론 재무 엔진 실행 — finance 는 /finance/simulate 요청 13필드."""


class ProductMatchingPort(ABC):
    @abstractmethod
    def match(self, funding_gap: int, industry_id: str) -> list[MatchedProduct]:
        """부족 자금·업종 조건 금융상품 (보증 → 은행 → 정책자금 순)."""


class ReportWriterPort(ABC):
    @abstractmethod
    def stream(self, system: str, prompt: str) -> Iterator[str]:
        """LLM 해석 텍스트 조각 스트림."""


class AnalysisRequestStorePort(ABC):
    @abstractmethod
    def save(self, request: AnalysisRequest) -> str:
        """요청 보관 후 analysis_id 반환."""

    @abstractmethod
    def take(self, analysis_id: str) -> AnalysisRequest | None:
        """요청을 꺼내고 지운다(1회 소비). 없으면 None."""
