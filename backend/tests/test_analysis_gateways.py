"""analysis 아웃바운드 게이트웨이 — 타 BC 결과를 analysis 값 객체로 변환 (ACL).

업종명은 테스트 DB 마스터 시드(conftest seed_all: cafe=카페)를 읽는다. 나머지 타 BC 는 Fake 유스케이스.
"""

from datetime import datetime

from apps.analysis.adapter.outbound.gateways.evidence_search_gateway import EvidenceSearchGateway
from apps.analysis.adapter.outbound.gateways.finance_gateways import (
    EngineSimulationGateway,
    ManualProductMatchingGateway,
)
from apps.analysis.adapter.outbound.gateways.market_data_gateway import MarketDataGateway
from apps.analysis.domain.analysis_context import EvidenceDoc, MatchedProduct, MetricCard, RiskView
from apps.master.app.dtos.region_dto import RegionDto, RegionSummaryDto, SummaryCardDto
from apps.master.app.ports.input.region_use_case import RegionUseCase
from apps.master.domain.errors import RegionNotFoundError
from apps.metric.app.dtos.region_industry_metric_dto import RiskScoreDto
from apps.metric.app.ports.input.risk_use_case import RiskUseCase
from apps.rag.app.ports.input.rag_use_case import RagSearchUseCase
from apps.rag.domain.entities.rag_chunk_entity import RagHit
from tests.analysis_fakes import FINANCE, SIMULATION


class FakeRegionUseCase(RegionUseCase):
    def myself(self) -> RegionDto:
        raise NotImplementedError

    def geojson(self) -> dict:
        raise NotImplementedError

    def summary(self, region_code: str, industry_id: str) -> RegionSummaryDto:
        if region_code != "2711059500":
            raise RegionNotFoundError(region_code)
        return RegionSummaryDto(
            region_code=region_code,
            name="대신동",
            industry_id=industry_id,
            cards=[
                SummaryCardDto("점포수", "120개", "fact"),
                SummaryCardDto("폐업률", "6.4%", "fact"),
                SummaryCardDto("성장률", "+2.1%", "fact"),
            ],
        )


class FakeRiskUseCase(RiskUseCase):
    def __init__(self, dto: RiskScoreDto | None) -> None:
        self._dto = dto

    def rank_by_region(self, industry_id, year):
        raise NotImplementedError

    def rank_by_industry(self, region_code, year):
        raise NotImplementedError

    def score_for(self, region_code, industry_id, year):
        return self._dto


_RISK = RiskScoreDto("2711059500", "cafe", 72.5, "red", {"closure": 30.0, "density": 28.5, "growth": 14.0})


def test_market_gateway_maps_summary_risk_and_industry_name():
    snapshot = MarketDataGateway(FakeRegionUseCase(), FakeRiskUseCase(_RISK)).fetch("2711059500", "cafe")

    assert snapshot.region_name == "대신동"
    assert snapshot.industry_name == "카페"
    assert snapshot.cards == [MetricCard("점포수", "120개"), MetricCard("폐업률", "6.4%"), MetricCard("성장률", "+2.1%")]
    assert snapshot.risk == RiskView(72.5, "red", {"closure": 30.0, "density": 28.5, "growth": 14.0})


def test_market_gateway_returns_none_for_unknown_region():
    assert MarketDataGateway(FakeRegionUseCase(), FakeRiskUseCase(_RISK)).fetch("0000000000", "cafe") is None


def test_market_gateway_keeps_snapshot_without_risk_and_falls_back_to_industry_id():
    snapshot = MarketDataGateway(FakeRegionUseCase(), FakeRiskUseCase(None)).fetch("2711059500", "unknown_industry")
    assert snapshot.risk is None
    assert snapshot.industry_name == "unknown_industry"


class FakeRagSearch(RagSearchUseCase):
    def __init__(self, hits: list[RagHit]) -> None:
        self._hits = hits
        self.calls: list[tuple] = []

    def search(self, query, top_k=5, source_type=None):
        self.calls.append((query, top_k, source_type))
        return self._hits


def _hit(content: str, published_at: datetime | None = datetime(2026, 9, 10, 9, 0)) -> RagHit:
    return RagHit("news:1", "news", "1", content, 0.8, "https://news.example/1", "매일신문", published_at)


def test_evidence_gateway_splits_title_and_snippet_and_passes_filters():
    rag = FakeRagSearch([_hit("원두값 급등에 카페 원가 압박\n원두 선물 가격이 전년 대비 8% 상승했다.")])

    docs = EvidenceSearchGateway(rag).search("대구 카페", "news", 5)

    assert rag.calls == [("대구 카페", 5, "news")]
    assert docs == [
        EvidenceDoc("news", "원두값 급등에 카페 원가 압박", "원두 선물 가격이 전년 대비 8% 상승했다.",
                    "https://news.example/1", "매일신문", "2026-09-10")
    ]


def test_evidence_gateway_title_only_content_and_long_body_truncation():
    title_only = EvidenceSearchGateway(FakeRagSearch([_hit("제목만", published_at=None)])).search("q", "news", 5)[0]
    assert (title_only.title, title_only.snippet, title_only.published_at) == ("제목만", "제목만", None)

    long_doc = EvidenceSearchGateway(FakeRagSearch([_hit("제목\n" + "가" * 500)])).search("q", "news", 5)[0]
    assert len(long_doc.snippet) == 300


def test_simulation_gateway_runs_deterministic_engine():
    assert EngineSimulationGateway().simulate(FINANCE) == SIMULATION


def _product(product_id, provider, provider_type, name, loan_limit, rate, category):
    return {
        "product_id": product_id, "provider": provider, "provider_type": provider_type,
        "product_name": name, "business_age_min": 0, "business_age_max": None, "category": category,
        "owner_age_max": None, "loan_limit": loan_limit, "interest_rate": rate,
    }


def test_matching_gateway_filters_by_gap_and_industry_and_orders_guarantee_first():
    products = [
        _product("b1", "iM뱅크", "bank", "창업대출", 100_000_000, 5.5, ["cafe"]),
        _product("g1", "대구신용보증재단", "guarantee", "창업 보증", 50_000_000, 3.2, ["cafe"]),
        _product("b2", "iM뱅크", "bank", "소액대출", 5_000_000, 6.0, ["cafe"]),
        _product("r1", "iM뱅크", "bank", "음식점대출", 100_000_000, 5.0, ["restaurant"]),
    ]

    matched = ManualProductMatchingGateway(lambda: products).match(10_000_000, "cafe")

    assert matched == [
        MatchedProduct("대구신용보증재단", "창업 보증", 50_000_000, 3.2),
        MatchedProduct("iM뱅크", "창업대출", 100_000_000, 5.5),
    ]


def test_simulation_gateway_carries_funding_breakdown():
    """전환계획 §4-1 — 분석 요약도 자기자본 외 조달 필요액을 함께 전달한다.
    리포트가 부족액 0원만 보고 '자기자본으로 충분'이라고 쓰지 못하게 하는 근거값이다."""
    summary = EngineSimulationGateway().simulate(FINANCE)
    assert summary.reserve_months == 6
    assert summary.operating_reserve == 18_849_996
    assert summary.total_required_funds == 58_849_996
    assert summary.external_funding_need == 28_849_996
