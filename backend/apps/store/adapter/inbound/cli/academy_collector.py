"""학원·교습소 수집기 (Driving Adapter, CLI).

- 원천: 나이스 교육정보 개방포털 acaInsTiInfo(대구교육청 D10) — 현행 스냅샷 전량, 매 실행 멱등 재수집
  (2026-09-19 서울 열린데이터 OA-20528에서 교체 — 서울 게이트웨이 모듈은 파싱 보조 함수 원천으로 보존)
- 적재: store 업서트(industry_id=academy, 좌표·행정동 이월) + academy_course 재적재(delete+insert)
  + 스냅샷 소실 폐업(추정) — 원천이 폐원분을 주지 않아 broker 전례를 따른다
- 호출: 1회 1,000건 × 9페이지 = 9회/스냅샷
- 실행: python -m apps.store.adapter.inbound.cli.academy_collector
"""

from datetime import date

from sqlalchemy import select

from apps.master.adapter.outbound.orms.district_orm import DistrictOrm
from apps.store.adapter.outbound.gateways.neis_academy_gateway import NeisAcademyGateway
from apps.store.adapter.outbound.repositories.academy_course_repository import (
    SqlAlchemyAcademyCourseRepository,
)
from apps.store.adapter.outbound.repositories.store_repository import (
    SqlAlchemyStoreRepository,
)
from apps.store.app.use_cases.academy_course_interactor import AcademyCourseInteractor
from core.matrix.grid_oracle_database_manager import session_scope


def main() -> None:
    with session_scope() as session:
        district_codes = dict(
            session.execute(select(DistrictOrm.name, DistrictOrm.district_code)).all()
        )

    gateway = NeisAcademyGateway(district_codes=district_codes)
    interactor = AcademyCourseInteractor(
        store_repository=SqlAlchemyStoreRepository(),
        course_repository=SqlAlchemyAcademyCourseRepository(),
        gateway=gateway,
    )
    stores, courses, closed = interactor.ingest(date.today())
    print(
        f"academy collector: 점포 {stores}건 업서트, 교습과정 {courses}건 재적재, 폐업(추정) {closed}건"
        f" (API {gateway.call_count}회 호출)",
        flush=True,
    )
    if gateway.skipped_districts:
        print(f"academy collector: 구 미매칭 스킵 {gateway.skipped_districts}", flush=True)


if __name__ == "__main__":
    main()
