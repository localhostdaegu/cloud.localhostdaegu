"""학원·교습소 수집기 (Driving Adapter, CLI).

- 원천: 서울 열린데이터광장 OA-20528 (neisAcademyInfo) — 현행 스냅샷 전량, 매 실행 멱등 재수집
- 적재: store 업서트(industry_id=academy) + academy_course 재적재(delete+insert)
- 실행: python -m apps.store.adapter.inbound.cli.academy_collector
- 가드: 원천이 서울 전용이라 대구 구성(REGION_NAME)에서는 수집 없이 종료 — 서울 학원이 동명 구(중구·동구 등)로
  대구 구 코드에 잘못 매핑되는 것을 막는다. 대구 학원 원천 확보 시 교체 (모듈은 보존)
"""

import sys

from sqlalchemy import select

from apps.master.adapter.outbound.orms.district_orm import DistrictOrm
from apps.store.adapter.outbound.gateways.seoul_academy_gateway import SeoulAcademyGateway
from apps.store.adapter.outbound.repositories.academy_course_repository import (
    SqlAlchemyAcademyCourseRepository,
)
from apps.store.adapter.outbound.repositories.store_repository import (
    SqlAlchemyStoreRepository,
)
from apps.store.app.use_cases.academy_course_interactor import AcademyCourseInteractor
from core.matrix.grid_oracle_database_manager import session_scope
from core.matrix.grid_region_config import REGION_NAME

_SOURCE_REGION = "서울"  # OA-20528 제공 지역


def main() -> None:
    if REGION_NAME != _SOURCE_REGION:
        sys.exit(
            f"academy collector: {REGION_NAME} 학원 원천 없음 — {_SOURCE_REGION} 열린데이터(OA-20528) 전용이라 실행 중단"
        )
    with session_scope() as session:
        district_codes = dict(
            session.execute(select(DistrictOrm.name, DistrictOrm.district_code)).all()
        )

    gateway = SeoulAcademyGateway(district_codes=district_codes)
    interactor = AcademyCourseInteractor(
        store_repository=SqlAlchemyStoreRepository(),
        course_repository=SqlAlchemyAcademyCourseRepository(),
        gateway=gateway,
    )
    stores, courses = interactor.ingest()
    print(
        f"academy collector: 점포 {stores}건 업서트, 교습과정 {courses}건 재적재"
        f" (API {gateway.call_count}회 호출)",
        flush=True,
    )
    if gateway.skipped_districts:
        print(f"academy collector: 구 미매칭 스킵 {gateway.skipped_districts}", flush=True)


if __name__ == "__main__":
    main()
