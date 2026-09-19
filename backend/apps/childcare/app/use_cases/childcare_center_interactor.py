"""어린이집 시설 인터랙터 — 스냅샷 수집(구·군 단위 전량 멱등 업서트).

convenience 전례대로 관측과 해석을 분리한다: 소실 시설을 폐원으로 판정하지 않고
last_seen_on 정지로만 남긴다.
"""

from datetime import date

from apps.childcare.app.ports.input.childcare_center_use_case import ChildcareSnapshotUseCase
from apps.childcare.app.ports.output.childcare_center_port import (
    ChildcareGatewayPort,
    ChildcareSnapshotRepositoryPort,
)


class ChildcareSnapshotInteractor(ChildcareSnapshotUseCase):
    def __init__(
        self,
        repository: ChildcareSnapshotRepositoryPort,
        gateway: ChildcareGatewayPort,
    ) -> None:
        self._repository = repository
        self._gateway = gateway

    def ingest(self, district_code: str, observed_on: date) -> int:
        return self._repository.upsert(self._gateway.fetch_centers(district_code), observed_on)
