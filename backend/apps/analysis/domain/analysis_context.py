"""분석 요청·수집 결과 값 객체와 오케스트레이션 컨텍스트 (프레임워크·타 BC import 금지)."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ConsultationProfile:
    """창업 단계·시점 — 사용자가 직접 확인해 입력한다(전환계획 §5-1).
    모르는 값은 None·"unknown" 으로 남긴다. 0·False 로 바꾸지 않는다."""

    business_registered: bool | None = None
    business_age_months: int | None = None
    planned_opening_date: str | None = None  # YYYY-MM-DD
    funds_needed_by: str | None = None
    owner_age: int | None = None
    guarantee_status: str = "unknown"
    policy_confirmation_status: str = "unknown"


@dataclass(frozen=True)
class ConsultationContext:
    """선택안에 딸린 상담 정보. 계산식을 덮어쓰지 않고 설명·확인 사항으로만 쓴다(§5-1)."""

    profile: ConsultationProfile
    baseline_finance: dict | None = None  # 비교 원본 — 서버가 다시 계산한다
    change_reason: str = ""
    assumptions: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AnalysisRequest:
    region: str  # 행정동 region_code
    industry: str  # industry_id
    question: str | None = None
    finance: dict | None = None  # /finance/simulate 요청 13필드(원 단위) — 있으면 시뮬레이션·계산표 포함
    purpose: str = "review"  # review = 계획 점검 / handoff = 상담자료 (§5-1)
    consultation: ConsultationContext | None = None


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
    funding_gap: int  # 희망대출 반영 후 남는 부족액 — external_funding_need 와 다르다 (§4-1)
    reserve_months: int
    operating_reserve: int
    total_required_funds: int
    external_funding_need: int  # 자기자본 외 조달 필요액 — 상담 주제가 되는 금액
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
    baseline_simulation: SimulationSummary | None = None  # 비교 원본 — 서버가 다시 계산한다(§5-1)

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

    @property
    def external_funding_need(self) -> int:
        """자기자본 외 조달 필요액 — 상품 조회·상담 주제가 되는 금액(§4-1)."""
        return self.simulation.external_funding_need if self.simulation else 0
