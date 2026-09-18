from dataclasses import replace
from apps.finance.domain.engine import FinanceInput, simulate

BASE = FinanceInput(
    deposit=20_000_000, key_money=0, interior_cost=30_000_000, equipment_cost=10_000_000,
    monthly_rent=2_000_000, monthly_payroll=6_000_000, monthly_insurance=500_000,
    cost_ratio=0.40, fee_ratio=0.03,
    equity=50_000_000, desired_loan=20_000_000, loan_rate=0.045,
    expected_monthly_revenue=20_000_000,
)

def test_capex_and_fixed():
    r = simulate(BASE)
    assert r.capex == 60_000_000                       # 보증금+권리금+인테리어+설비
    # 고정비 = 월세 + 이자(2천만×4.5%/12=75,000) + 보험 + 인건비
    assert r.monthly_fixed == 2_000_000 + 75_000 + 500_000 + 6_000_000

def test_bep_revenue():
    r = simulate(BASE)
    assert abs(r.bep_revenue - r.monthly_fixed / (1 - 0.43)) < 1   # 고정비/(1-변동비율)

def test_three_scenarios_and_payback():
    r = simulate(BASE)
    assert [s.name for s in r.scenarios] == ["비관", "기준", "낙관"]
    pess, base, opt = r.scenarios
    assert pess.monthly_revenue == 12_000_000          # 기준 × 0.6
    assert opt.monthly_revenue == 32_000_000           # 기준 × 1.6
    assert base.operating_profit == int(20_000_000 * (1 - 0.43)) - r.monthly_fixed
    assert base.payback_months == round(r.capex / base.operating_profit, 1)

def test_funding_gap_and_runway():
    r = simulate(BASE)
    # 필요총액 = capex + 운전자금(고정비×6개월). 부족 = 필요총액 - (자기자본+희망대출), 음수면 0
    need = r.capex + r.monthly_fixed * 6
    assert r.funding_gap == max(0, need - (50_000_000 + 20_000_000))
    pess = r.scenarios[0]
    if pess.operating_profit < 0:                       # 적자 시나리오만 runway 유한
        cash = 50_000_000 + 20_000_000 - r.capex
        assert pess.runway_months == round(cash / -pess.operating_profit, 1)

def test_interest_stress():
    from apps.finance.domain.engine import _profit_at, _fixed
    r = simulate(BASE)
    assert r.stress[0].rate_delta == 0.01 and r.stress[1].rate_delta == 0.02
    assert r.stress[0].monthly_fixed > r.monthly_fixed  # 금리 +1%p → 고정비 증가
    # Verify profit formula is unified: if stress had delta=0, it should match scenarios[1]
    base_profit_at_zero_delta = _profit_at(BASE.expected_monthly_revenue, BASE.cost_ratio + BASE.fee_ratio, _fixed(BASE, BASE.loan_rate + 0))
    assert base_profit_at_zero_delta == r.scenarios[1].operating_profit


# --- 전환계획 §7 인수 기준: 자금 구성 4수치 분리 ---------------------------

# §7-1 최초안. 월세 200만 원, 희망대출 0원.
PLAN_BASELINE = FinanceInput(
    deposit=20_000_000, key_money=0, interior_cost=20_000_000, equipment_cost=10_000_000,
    monthly_rent=2_000_000, monthly_payroll=900_000, monthly_insurance=100_000,
    cost_ratio=0.57, fee_ratio=0.03,
    equity=60_000_000, desired_loan=0, loan_rate=0.045,
    expected_monthly_revenue=8_000_000,
)


def test_plan_baseline_funding_breakdown():
    """§7-1 최초안 — 운영준비금 1,800만, 총 준비자금 6,800만, 조달 필요 800만."""
    r = simulate(PLAN_BASELINE)
    assert r.capex == 50_000_000
    assert r.monthly_fixed == 3_000_000
    assert r.bep_revenue == 7_500_000
    assert r.operating_reserve == 18_000_000
    assert r.total_required_funds == 68_000_000
    assert r.external_funding_need == 8_000_000
    assert r.funding_gap == 8_000_000


def test_plan_revised_funding_breakdown():
    """§7-1 수정안 — 월세만 100만으로 낮추면 조달 필요가 200만으로 줄어든다."""
    r = simulate(replace(PLAN_BASELINE, monthly_rent=1_000_000))
    assert r.monthly_fixed == 2_000_000
    assert r.bep_revenue == 5_000_000
    assert r.operating_reserve == 12_000_000
    assert r.total_required_funds == 62_000_000
    assert r.external_funding_need == 2_000_000
    assert r.funding_gap == 2_000_000


def test_unsecured_loan_remains_visible_when_gap_is_zero():
    """§7-2 필수 회귀 — 희망대출 2,500만으로 부족액이 0원이 되어도
    자기자본 외 조달 필요 2,260만이 남아야 한다. '자기자본으로 충분'이 아니다."""
    r = simulate(replace(
        PLAN_BASELINE,
        monthly_rent=1_000_000, equity=40_000_000,
        desired_loan=25_000_000, loan_rate=0.048,
    ))
    assert r.monthly_fixed == 2_100_000
    assert r.operating_reserve == 12_600_000
    assert r.total_required_funds == 62_600_000
    assert r.external_funding_need == 22_600_000
    assert r.funding_gap == 0


def test_reserve_months_is_exposed_for_display():
    """준비금 개월 수는 화면·상담자료가 '6개월치'라고 설명할 수 있어야 한다."""
    assert simulate(PLAN_BASELINE).reserve_months == 6
