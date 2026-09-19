"""학원·교습소 스냅샷 수집 인터랙터 — 전량 업서트 + 좌표 이월 + 스냅샷 소실 폐업 추정.

NEIS 원천은 현행 스냅샷만 주고(폐원분·좌표 없음), 전국 1회 조회라 구·군 단위가 아닌 업종 전체가 한 스냅샷이다.
"""

from datetime import date
from itertools import batched

from apps.store.app.ports.input.academy_course_use_case import AcademyIngestUseCase
from apps.store.app.ports.output.academy_course_port import (
    AcademyCourseRepositoryPort,
    AcademyGatewayPort,
)
from apps.store.app.ports.output.broker_snapshot_port import StoreSnapshotRepositoryPort
from apps.store.app.use_cases.snapshot_support import (
    CLOSED_STATUS_CODE,
    CLOSED_STATUS_NAME,
    carry_location,
)

_CHUNK_SIZE = 500
_INDUSTRY_ID = "academy"


class AcademyCourseInteractor(AcademyIngestUseCase):
    def __init__(
        self,
        store_repository: StoreSnapshotRepositoryPort,
        course_repository: AcademyCourseRepositoryPort,
        gateway: AcademyGatewayPort,
    ) -> None:
        self._store_repository = store_repository
        self._course_repository = course_repository
        self._gateway = gateway

    def ingest(self, observed_on: date) -> tuple[int, int, int]:
        prior_active = self._store_repository.active_store_ids(_INDUSTRY_ID)
        locations = self._store_repository.existing_locations(_INDUSTRY_ID)

        stores = courses = 0
        seen: set[str] = set()
        for chunk in batched(self._gateway.iter_academies(), _CHUNK_SIZE):
            carried = [carry_location(record.store, locations) for record in chunk]
            seen.update(store.store_id for store in carried)
            # store를 먼저 커밋해야 course의 FK(store_id)가 성립한다
            stores += self._store_repository.upsert(carried)
            courses += self._course_repository.replace_for_stores(
                {record.store.store_id: record.courses for record in chunk}
            )

        # 스트림 완주 후에만 폐업 추정 — 수집 중 예외 시 부분 스냅샷으로 오판하지 않는다
        closed = self._store_repository.mark_closed(
            sorted(prior_active - seen),
            close_date=observed_on,
            status_code=CLOSED_STATUS_CODE,
            status_name=CLOSED_STATUS_NAME,
        )
        return stores, courses, closed
