from functools import lru_cache
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from apps.intent.domain.parser import parse_intent
from core.matrix.grid_oracle_database_manager import session_scope
from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from apps.master.adapter.outbound.orms.district_orm import DistrictOrm

router = APIRouter(prefix="/intent", tags=["intent"])


class IntentRequest(BaseModel):
    text: str


class IntentResponse(BaseModel):
    intent_type: str
    district_code: str | None = None
    region_name: str | None = None
    industry_slug: str | None = None
    budget_krw: int | None = None
    missing: list[str] = []


@lru_cache(maxsize=1)
def _load_dongs_gus() -> tuple[dict[str, str], dict[str, str]]:
    """Load dongs (region) and gus (district) from database with caching."""
    dongs: dict[str, str] = {}
    gus: dict[str, str] = {}

    with session_scope() as session:
        # Load regions (dongs)
        regions = session.execute(select(RegionOrm)).scalars().all()
        for region in regions:
            dongs[region.name] = region.district_code

        # Load districts (gus)
        districts = session.execute(select(DistrictOrm)).scalars().all()
        for district in districts:
            gus[district.name] = district.district_code

    return dongs, gus


def get_dongs_gus() -> tuple[dict[str, str], dict[str, str]]:
    """Dependency injection function for dongs and gus dictionaries."""
    return _load_dongs_gus()


@router.get("/myself")
def myself() -> dict:
    """Validation endpoint to verify router wiring."""
    return {"status": "ok", "message": "intent router is working"}


@router.post("", response_model=IntentResponse)
def extract_intent(
    request: IntentRequest,
    dicts: tuple[dict[str, str], dict[str, str]] = Depends(get_dongs_gus),
) -> IntentResponse:
    """Extract intent from user input text."""
    dongs, gus = dicts
    result = parse_intent(request.text, dongs, gus)

    return IntentResponse(
        intent_type=result.intent_type,
        district_code=result.district_code,
        region_name=result.region_name,
        industry_slug=result.industry_slug,
        budget_krw=result.budget_krw,
        missing=result.missing,
    )
