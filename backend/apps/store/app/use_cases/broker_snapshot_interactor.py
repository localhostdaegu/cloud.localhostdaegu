"""부동산중개업 스냅샷 수집 인터랙터 — 전량 업서트 + 스냅샷 소실 폐업 추정.

원천(getEBOfficeInfo)이 폐업 사무소를 제공하지 않으므로(sttusSeCode=3 totalCount 0 실확인),
폐업은 "이전 스냅샷에 있었으나 이번 스냅샷에 없음"으로 추정하고 관측일을 close_date로 기록한다.
최초 적재일에는 비교 기준(기존 행)이 없어 추정이 발동하지 않는다.
"""

from datetime import date
from itertools import batched

from apps.store.app.ports.input.broker_snapshot_use_case import BrokerSnapshotUseCase
from apps.store.app.ports.output.broker_snapshot_port import (
    BrokerGatewayPort,
    StoreSnapshotRepositoryPort,
)
from apps.store.app.use_cases.snapshot_support import (
    CLOSED_STATUS_CODE as _CLOSED_STATUS_CODE,
)
from apps.store.app.use_cases.snapshot_support import (
    CLOSED_STATUS_NAME as _CLOSED_STATUS_NAME,
)
from apps.store.app.use_cases.snapshot_support import carry_location
from apps.store.domain.entities.store_entity import Store

_CHUNK_SIZE = 500


class BrokerSnapshotInteractor(BrokerSnapshotUseCase):
    def __init__(
        self, repository: StoreSnapshotRepositoryPort, gateway: BrokerGatewayPort
    ) -> None:
        self._repository = repository
        self._gateway = gateway

    def ingest(
        self, industry_id: str, district_code: str, observed_on: date
    ) -> tuple[int, int]:
        prior_active = self._repository.active_store_ids(industry_id, district_code)
        locations = self._repository.existing_locations(industry_id, district_code)

        processed = 0
        seen: set[str] = set()
        for chunk in batched(
            self._gateway.iter_offices(industry_id, district_code), _CHUNK_SIZE
        ):
            stores = [carry_location(store, locations) for store in chunk]
            seen.update(store.store_id for store in stores)
            processed += self._repository.upsert(stores)

        # 스트림 완주 후에만 폐업 추정 — 수집 중 예외 시 부분 스냅샷으로 오판하지 않는다
        closed = self._repository.mark_closed(
            sorted(prior_active - seen),
            close_date=observed_on,
            status_code=_CLOSED_STATUS_CODE,
            status_name=_CLOSED_STATUS_NAME,
        )
        return processed, closed
