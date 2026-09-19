from sqlalchemy import func, select

from apps.rent.adapter.outbound.orm_mappers.rent_price_orm_mapper import to_entity
from apps.rent.adapter.outbound.orms.rent_price_orm import RentPriceOrm
from apps.rent.app.ports.output.rent_price_port import RentPriceRepositoryPort
from apps.rent.domain.entities.rent_price_entity import RentPrice
from core.matrix.grid_oracle_database_manager import session_scope


class SqlAlchemyRentPriceRepository(RentPriceRepositoryPort):
    def find_latest(self) -> list[RentPrice]:
        # YYYYQn 문자열 — 사전순 = 시간순. 빈 테이블이면 max가 NULL → 0행
        latest_period = select(func.max(RentPriceOrm.period)).scalar_subquery()
        with session_scope() as session:
            orms = session.execute(
                select(RentPriceOrm).where(RentPriceOrm.period == latest_period)
            ).scalars()
            return [to_entity(orm) for orm in orms]
