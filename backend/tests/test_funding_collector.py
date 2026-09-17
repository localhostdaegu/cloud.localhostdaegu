"""funding collector 실패 격리 검증 — 한 소스 실패가 다른 소스 수집·만료 갱신을 막지 않는다 (경계 Fake, DB·네트워크 미사용)."""

from datetime import date

from apps.funding.adapter.inbound.cli.funding_collector import collect
from apps.funding.app.ports.output.funding_program_port import (
    FundingProgramRepositoryPort,
    FundingSearchGatewayPort,
)
from apps.funding.domain.entities.funding_program_entity import FundingProgram

_TODAY = date(2026, 9, 18)


class FakeRepository(FundingProgramRepositoryPort):
    def __init__(self) -> None:
        self.upserted_batches: list[list[FundingProgram]] = []
        self.refreshed_on: list[date] = []

    def upsert(self, programs: list[FundingProgram]) -> tuple[int, int]:
        self.upserted_batches.append(programs)
        return len(programs), 0

    def refresh_expirations(self, today: date) -> int:
        self.refreshed_on.append(today)
        return 0

    def list_open(self, limit: int) -> list[FundingProgram]:
        return []


class FailingGateway(FundingSearchGatewayPort):
    def fetch_all(self) -> list[FundingProgram]:
        raise RuntimeError("원천 API 500")


class EmptyGateway(FundingSearchGatewayPort):
    def fetch_all(self) -> list[FundingProgram]:
        return []


def test_collect_isolates_source_failure_and_always_refreshes_expirations():
    repository = FakeRepository()

    failed = collect(repository, {"bizinfo": FailingGateway(), "youthcenter": EmptyGateway()}, _TODAY)

    assert failed == 1
    assert repository.upserted_batches == [[]]  # 앞 소스 실패 후에도 다음 소스 수집
    assert repository.refreshed_on == [_TODAY]  # 만료 갱신은 항상 실행


def test_collect_reports_zero_failures_when_all_sources_succeed():
    repository = FakeRepository()

    assert collect(repository, {"bizinfo": EmptyGateway(), "youthcenter": EmptyGateway()}, _TODAY) == 0
    assert repository.refreshed_on == [_TODAY]
