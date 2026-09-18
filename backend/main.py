from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from apps.analysis.adapter.inbound.api.v1.analysis_router import router as analysis_router
from apps.consultation.adapter.inbound.api.v1.consultation_router import (
    router as consultation_router,
)
from apps.finance.adapter.inbound.api.v1.finance_router import router as finance_router
from apps.funding.adapter.inbound.api.v1.funding_program_router import (
    router as funding_router,
)
from apps.intent.adapter.inbound.api.v1.intent_router import router as intent_router
from apps.master.adapter.inbound.api.v1.region_router import router as region_router
from apps.matching.adapter.inbound.api.v1.matching_router import router as matching_router
from apps.metric.adapter.inbound.api.v1.region_industry_metric_router import (
    router as metric_router,
)
from apps.news.adapter.inbound.api.v1.news_article_router import router as news_router
from apps.shock.adapter.inbound.api.v1.interest_rate_router import router as rate_router
from apps.shock.adapter.inbound.api.v1.shock_event_router import router as shock_router
from apps.store.adapter.inbound.api.v1.store_router import router as store_router

app = FastAPI(title="대구 창업 금융 네비게이터 backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3300", "http://127.0.0.1:3300"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1024)  # /regions/geojson 등 대형 응답 압축
app.include_router(analysis_router)
app.include_router(consultation_router)
app.include_router(finance_router)
app.include_router(funding_router)
app.include_router(intent_router)
app.include_router(matching_router)
app.include_router(region_router)
app.include_router(metric_router)
app.include_router(news_router)
app.include_router(rate_router)
app.include_router(shock_router)
app.include_router(store_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
