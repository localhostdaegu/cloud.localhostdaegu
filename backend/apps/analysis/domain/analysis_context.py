"""분석 요청·수집 결과 값 객체와 오케스트레이션 컨텍스트 (프레임워크·타 BC import 금지)."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AnalysisRequest:
    region: str  # 행정동 region_code
    industry: str  # industry_id
    question: str | None = None
    finance: dict | None = None  # /finance/simulate 요청 13필드(원 단위) — 있으면 시뮬레이션·계산표 포함


@dataclass(frozen=True)
class MetricCard:
    label: str
    value: str


@dataclass(frozen=True)
class RiskView:
    score: float
    grade: str  # red | yellow | green
    components: dict[str, float]  # closure·density·growth


@dataclass(frozen=True)
class MarketSnapshot:
    region_name: str
    industry_name: str
    cards: list[MetricCard]
    risk: RiskView | None


@dataclass(frozen=True)
class EvidenceDoc:
    source_type: str  # funding | news
    title: str
    snippet: str
    url: str | None
    org: str | None
    published_at: str | None  # YYYY-MM-DD


@dataclass(frozen=True)
class ScenarioLine:
    name: str
    monthly_revenue: int
    operating_profit: int
    payback_months: float | None


@dataclass(frozen=True)
class SimulationSummary:
    capex: int
    monthly_fixed: int
    bep_revenue: int
    funding_gap: int
    scenarios: list[ScenarioLine]


@dataclass(frozen=True)
class MatchedProduct:
    provider: str
    product_name: str
    loan_limit: int | None
    interest_rate: float | None


@dataclass
class AnalysisContext:
    """오케스트레이션 1회분 작업 공간 — 에이전트가 채우고 리포트 섹션이 읽는다."""

    analysis_id: str
    request: AnalysisRequest
    market: MarketSnapshot | None = None
    news: list[EvidenceDoc] = field(default_factory=list)
    funding_docs: list[EvidenceDoc] = field(default_factory=list)
    products: list[MatchedProduct] = field(default_factory=list)
    simulation: SimulationSummary | None = None

    @property
    def region_label(self) -> str:
        return self.market.region_name if self.market else self.request.region

    @property
    def industry_label(self) -> str:
        return self.market.industry_name if self.market else self.request.industry

    @property
    def risk(self) -> RiskView | None:
        return self.market.risk if self.market else None

    @property
    def cards(self) -> list[MetricCard]:
        return self.market.cards if self.market else []

    @property
    def funding_gap(self) -> int:
        return self.simulation.funding_gap if self.simulation else 0
