"""regional_indicator 적재 규칙 (테스트 DB) — 미승인 데이터셋 거부·NULL 슬라이스 중복 차단·멱등 업서트.

설계 스펙 §3-2 "적재 규칙": export_approved_on이 NULL인 데이터셋에는 지표를 적재하지 않는다.
승인 전 데이터가 서비스에 들어가는 길을 리포지토리에서 구조적으로 끊는다.
"""

from datetime import date

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from apps.dataset.adapter.outbound.orms.external_dataset_orm import ExternalDatasetOrm
from apps.dataset.adapter.outbound.repositories.external_dataset_repository import (
    SqlAlchemyExternalDatasetRepository,
)
from apps.dataset.domain.entities.external_dataset_entity import ExternalDataset
from apps.indicator.adapter.outbound.orms.regional_indicator_orm import RegionalIndicatorOrm
from apps.indicator.adapter.outbound.repositories.regional_indicator_repository import (
    SqlAlchemyRegionalIndicatorRepository,
)
from apps.indicator.domain.entities.regional_indicator_entity import RegionalIndicator
from apps.indicator.domain.errors import DatasetNotApprovedError
from core.matrix.grid_oracle_database_manager import session_scope

_REGION = "2711059500"  # 중구 대신동 (시드 마스터)
_APPROVED_ID = "test-dip-approved"
_UNAPPROVED_ID = "test-dip-unapproved"
_DATASET_IDS = (_APPROVED_ID, _UNAPPROVED_ID)


def _dataset(dataset_id: str, approved_on: date | None) -> ExternalDataset:
    return ExternalDataset(
        dataset_id=dataset_id,
        name="적재 규칙 테스트 결과표",
        provider="삼성카드",
        source_channel="dip_center",
        period_start="202401",
        period_end="202412",
        aggregation_note="동×업종×월 AMT 합계의 전년 동월 대비 변화율",
        restriction_note="점포당 매출로 환산 금지",
        export_approved_on=approved_on,
        approval_ref=None,
        source_url=None,
        catalog_page="18",
    )


def _indicator(dataset_id: str, value: float, breakdown: str | None = None) -> RegionalIndicator:
    return RegionalIndicator(
        dataset_id=dataset_id,
        region_code=_REGION,
        industry_id=None,  # 업종 무관 지표 — NULL 슬라이스 경로를 그대로 탄다
        period="202412",
        indicator_key="test_card_amt_index",
        breakdown=breakdown,
        value=value,
        unit="지수",
    )


@pytest.fixture(autouse=True)
def datasets():
    SqlAlchemyExternalDatasetRepository().upsert(
        [_dataset(_APPROVED_ID, date(2026, 9, 18)), _dataset(_UNAPPROVED_ID, None)]
    )
    yield
    with session_scope() as session:
        session.execute(
            delete(RegionalIndicatorOrm).where(
                RegionalIndicatorOrm.dataset_id.in_(_DATASET_IDS)
            )
        )
        session.execute(
            delete(ExternalDatasetOrm).where(ExternalDatasetOrm.dataset_id.in_(_DATASET_IDS))
        )


def test_upsert_rejects_indicator_for_unapproved_dataset():
    with pytest.raises(DatasetNotApprovedError, match=_UNAPPROVED_ID):
        SqlAlchemyRegionalIndicatorRepository().upsert([_indicator(_UNAPPROVED_ID, 100.0)])
    with session_scope() as session:
        rows = session.execute(
            select(RegionalIndicatorOrm).where(
                RegionalIndicatorOrm.dataset_id == _UNAPPROVED_ID
            )
        ).scalars()
        assert list(rows) == []


def test_duplicate_null_slice_rows_violate_unique_constraint():
    """industry_id·breakdown이 NULL이어도 중복은 차단된다 (UNIQUE … NULLS NOT DISTINCT)."""
    SqlAlchemyRegionalIndicatorRepository().upsert([_indicator(_APPROVED_ID, 112.4)])
    with pytest.raises(IntegrityError):
        with session_scope() as session:
            session.add(
                RegionalIndicatorOrm(
                    dataset_id=_APPROVED_ID,
                    region_code=_REGION,
                    industry_id=None,
                    period="202412",
                    indicator_key="test_card_amt_index",
                    breakdown=None,
                    value=999.0,
                    unit="지수",
                )
            )


def test_upsert_is_idempotent_and_updates_the_value():
    repository = SqlAlchemyRegionalIndicatorRepository()
    repository.upsert([_indicator(_APPROVED_ID, 112.4), _indicator(_APPROVED_ID, 98.0, "weekend")])
    repository.upsert([_indicator(_APPROVED_ID, 115.0), _indicator(_APPROVED_ID, 98.0, "weekend")])
    with session_scope() as session:
        rows = list(
            session.execute(
                select(RegionalIndicatorOrm.breakdown, RegionalIndicatorOrm.value)
                .where(RegionalIndicatorOrm.dataset_id == _APPROVED_ID)
                .order_by(RegionalIndicatorOrm.breakdown.asc().nulls_first())
            )
        )
    assert rows == [(None, 115.0), ("weekend", 98.0)]  # 재실행해도 2행, 값만 갱신
