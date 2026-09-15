from fastapi import APIRouter
from apps.finance.adapter.inbound.api.schemas.finance_schema import SimulateRequest, SimulateResponse
from apps.finance.domain.engine import FinanceInput, simulate

router = APIRouter(prefix="/finance", tags=["finance"])

@router.get("/myself")
def myself() -> dict:
    return {"app": "finance", "status": "wired"}

@router.post("/simulate", response_model=SimulateResponse)
def run_simulation(req: SimulateRequest) -> SimulateResponse:
    return SimulateResponse.from_result(simulate(FinanceInput(**req.model_dump())))
