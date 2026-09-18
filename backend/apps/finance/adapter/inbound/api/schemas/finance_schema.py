from dataclasses import asdict
from typing import Annotated, Self

from pydantic import BaseModel, Field, model_validator

from apps.finance.domain.engine import FinanceResult

_Won = Annotated[int, Field(ge=0)]  # 금액(원) — 음수 불가
_Ratio = Annotated[float, Field(ge=0, lt=1)]  # 비율 0 이상 1 미만


class SimulationScenarioResponse(BaseModel):
    name: str
    monthly_revenue: int
    variable_cost: int
    operating_profit: int
    payback_months: float | None
    runway_months: float | None


class StressResultResponse(BaseModel):
    rate_delta: float
    monthly_fixed: int
    base_operating_profit: int


class SimulateResponse(BaseModel):
    capex: int
    monthly_fixed: int
    bep_revenue: int
    funding_gap: int  # 희망대출 반영 후 남는 부족액 — external_funding_need 와 다르다 (§4-1)
    reserve_months: int
    operating_reserve: int
    total_required_funds: int
    external_funding_need: int  # 자기자본 외 조달 필요액 — 상담 주제가 되는 금액
    scenarios: list[SimulationScenarioResponse]
    stress: list[StressResultResponse]

    @classmethod
    def from_result(cls, result: FinanceResult) -> "SimulateResponse":
        return cls(
            capex=result.capex,
            monthly_fixed=result.monthly_fixed,
            bep_revenue=result.bep_revenue,
            funding_gap=result.funding_gap,
            reserve_months=result.reserve_months,
            operating_reserve=result.operating_reserve,
            total_required_funds=result.total_required_funds,
            external_funding_need=result.external_funding_need,
            scenarios=[
                SimulationScenarioResponse(**asdict(s)) for s in result.scenarios
            ],
            stress=[
                StressResultResponse(**asdict(s)) for s in result.stress
            ],
        )


class SimulateRequest(BaseModel):
    deposit: _Won
    key_money: _Won
    interior_cost: _Won
    equipment_cost: _Won
    monthly_rent: _Won
    monthly_payroll: _Won
    monthly_insurance: _Won
    cost_ratio: _Ratio
    fee_ratio: _Ratio
    equity: _Won
    desired_loan: _Won
    loan_rate: _Ratio
    expected_monthly_revenue: _Won

    @model_validator(mode="after")
    def _variable_ratio_below_one(self) -> Self:
        """BEP 매출 = 고정비/(1-변동비율) — 변동비율 ≥ 1 이면 0 나눗셈·음수 BEP (422)."""
        if self.cost_ratio + self.fee_ratio >= 1:
            raise ValueError("cost_ratio + fee_ratio 는 1 미만이어야 합니다")
        return self
