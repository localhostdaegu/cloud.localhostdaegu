from dataclasses import asdict
from pydantic import BaseModel

from apps.finance.domain.engine import FinanceInput, FinanceResult, SimulationScenario, StressResult


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
    funding_gap: int
    scenarios: list[SimulationScenarioResponse]
    stress: list[StressResultResponse]

    @classmethod
    def from_result(cls, result: FinanceResult) -> "SimulateResponse":
        return cls(
            capex=result.capex,
            monthly_fixed=result.monthly_fixed,
            bep_revenue=result.bep_revenue,
            funding_gap=result.funding_gap,
            scenarios=[
                SimulationScenarioResponse(**asdict(s)) for s in result.scenarios
            ],
            stress=[
                StressResultResponse(**asdict(s)) for s in result.stress
            ],
        )


class SimulateRequest(BaseModel):
    deposit: int
    key_money: int
    interior_cost: int
    equipment_cost: int
    monthly_rent: int
    monthly_payroll: int
    monthly_insurance: int
    cost_ratio: float
    fee_ratio: float
    equity: int
    desired_loan: int
    loan_rate: float
    expected_monthly_revenue: int
