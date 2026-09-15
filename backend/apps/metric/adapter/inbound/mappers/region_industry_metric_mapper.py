"""Inbound Boundary Gate — dto ↔ schema 변환 (Router ↔ Interactor 경계)."""

from dataclasses import asdict

from apps.metric.adapter.inbound.api.schemas.region_industry_metric_schema import (
    MetricValueResponse,
    RegionIndustryMetricResponse,
)
from apps.metric.app.dtos.region_industry_metric_dto import (
    MetricValueDto,
    RegionIndustryMetricDto,
    RiskScoreDto,
)


def to_response(dto: RegionIndustryMetricDto) -> RegionIndustryMetricResponse:
    return RegionIndustryMetricResponse(**asdict(dto))


def to_metric_value_response(dto: MetricValueDto) -> MetricValueResponse:
    return MetricValueResponse(**asdict(dto))


def to_region_risk_response(dto: RiskScoreDto) -> dict:
    """업종 고정 랭킹 / region×industry 단건 — {region_code, score, grade, components}."""
    return {
        "region_code": dto.region_code,
        "score": dto.score,
        "grade": dto.grade,
        "components": dto.components,
    }


def to_industry_risk_response(dto: RiskScoreDto) -> dict:
    """region 고정 업종별 랭킹 — {industry_id, score, grade, components}."""
    return {
        "industry_id": dto.industry_id,
        "score": dto.score,
        "grade": dto.grade,
        "components": dto.components,
    }
