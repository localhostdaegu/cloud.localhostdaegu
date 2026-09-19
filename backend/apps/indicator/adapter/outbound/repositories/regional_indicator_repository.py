from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from apps.dataset.adapter.outbound.orms.external_dataset_orm import ExternalDatasetOrm
from apps.indicator.adapter.outbound.orm_mappers.regional_indicator_orm_mapper import (
    CONFLICT_KEY,
    to_entity,
    to_values,
)
from apps.indicator.adapter.outbound.orms.regional_indicator_orm import RegionalIndicatorOrm
from apps.indicator.app.ports.output.regional_indicator_port import (
    RegionalIndicatorRepositoryPort,
)
from apps.indicator.domain.entities.regional_indicator_entity import RegionalIndicator
from apps.indicator.domain.errors import DatasetNotApprovedError, DatasetNotFoundError
from core.matrix.grid_oracle_database_manager import session_scope

_UPSERT_BATCH = 4000  # 8컬럼 × 4000 = 32,000 파라미터 < psycopg 한도 65,535 (tobacco 로더 전례)


class SqlAlchemyRegionalIndicatorRepository(RegionalIndicatorRepositoryPort):
    def upsert(self, indicators: list[RegionalIndicator]) -> int:
        if not indicators:
            return 0
        with session_scope() as session:
            # 승인 검사가 먼저다 — 한 건이라도 미승인이면 배치 전체를 적재하지 않는다.
            # 확보계획 §5-2·§7: 심사 전 수치는 확보로도, 서비스 표시로도 취급하지 않는다.
            _assert_export_approved(session, {i.dataset_id for i in indicators})
            values = [to_values(indicator) for indicator in indicators]
            for start in range(0, len(values), _UPSERT_BATCH):
                statement = insert(RegionalIndicatorOrm).values(values[start : start + _UPSERT_BATCH])
                session.execute(
                    statement.on_conflict_do_update(
                        # NULLS NOT DISTINCT 유니크 인덱스를 중재자로 삼는다 — 업종/슬라이스가
                        # NULL인 행도 같은 지표로 인식돼 새 행이 쌓이지 않고 값만 갱신된다
                        index_elements=list(CONFLICT_KEY),
                        set_={
                            "value": statement.excluded.value,
                            "unit": statement.excluded.unit,
                        },
                    )
                )
        return len(values)

    def myself(self) -> RegionalIndicator:
        return RegionalIndicator(
            dataset_id="myself",
            region_code="2711051700",
            period="202609",
            indicator_key="myself",
            value=1.0,
            unit="곳",
        )

    def find_by_region(self, region_code: str) -> list[RegionalIndicator]:
        with session_scope() as session:
            orms = session.execute(
                select(RegionalIndicatorOrm).where(RegionalIndicatorOrm.region_code == region_code)
            ).scalars()
            return [to_entity(orm) for orm in orms]


def _assert_export_approved(session: Session, dataset_ids: set[str]) -> None:
    """미등록·미승인 데이터셋을 걸러낸다 — 출처 없는 수치, 심사 전 수치의 적재를 막는다."""
    approved_on = dict(
        session.execute(
            select(ExternalDatasetOrm.dataset_id, ExternalDatasetOrm.export_approved_on).where(
                ExternalDatasetOrm.dataset_id.in_(dataset_ids)
            )
        ).all()
    )
    if missing := sorted(dataset_ids - approved_on.keys()):
        raise DatasetNotFoundError(f"external_dataset에 없는 데이터셋: {', '.join(missing)}")
    if unapproved := sorted(key for key, value in approved_on.items() if value is None):
        raise DatasetNotApprovedError(
            f"반출 미승인 데이터셋에는 지표를 적재할 수 없다: {', '.join(unapproved)}"
        )
