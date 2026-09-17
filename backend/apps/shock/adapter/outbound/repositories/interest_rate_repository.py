from sqlalchemy import select

from apps.shock.adapter.outbound.orm_mappers.interest_rate_orm_mapper import to_entity
from apps.shock.adapter.outbound.orms.interest_rate_orm import InterestRateOrm
from apps.shock.app.ports.output.interest_rate_port import InterestRateRepositoryPort
from apps.shock.domain.entities.interest_rate_entity import InterestRate
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyInterestRateRepository(InterestRateRepositoryPort):
    def find_latest(self, rate_type: str) -> InterestRate | None:
        with session_scope() as session:
            orm = session.execute(
                select(InterestRateOrm)
                .where(InterestRateOrm.rate_type == rate_type)
                .order_by(InterestRateOrm.period.desc())  # YYYYMM 문자열 — 사전순 = 시간순
                .limit(1)
            ).scalar_one_or_none()
            return to_entity(orm) if orm else None
