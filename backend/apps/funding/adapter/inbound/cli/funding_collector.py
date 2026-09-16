"""정책자금 공고 수집기 (Driving Adapter, CLI — 일 1회 크론 실행 대상).

기업마당 API 1회 호출로 전량(~1,500건) 수신 → program_id 업서트(멱등)
온통청년 API 대구 8구·군 순회(중분류 '창업', ~60건) → 업서트(멱등) → 만료 갱신.

실행: python -m apps.funding.adapter.inbound.cli.funding_collector
"""

from datetime import date

from apps.funding.adapter.outbound.gateways.bizinfo_gateway import BizinfoGateway
from apps.funding.adapter.outbound.gateways.youthcenter_gateway import YouthcenterGateway
from apps.funding.adapter.outbound.repositories.funding_program_repository import (
    SqlAlchemyFundingProgramRepository,
)
from apps.funding.app.use_cases.funding_program_interactor import (
    FundingProgramInteractor,
)


def main() -> None:
    repository = SqlAlchemyFundingProgramRepository()
    for name, gateway in (("bizinfo", BizinfoGateway()), ("youthcenter", YouthcenterGateway())):
        interactor = FundingProgramInteractor(repository=repository, gateway=gateway)
        inserted, updated = interactor.ingest()
        print(f"funding collector [{name}]: 신규 {inserted}건 / 갱신 {updated}건")
    expired = FundingProgramInteractor(repository=repository, gateway=BizinfoGateway()).refresh_expirations(date.today())
    print(f"funding collector: 신규 만료 {expired}건")


if __name__ == "__main__":
    main()
