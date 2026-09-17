"""정책자금 공고 수집기 (Driving Adapter, CLI — 일 1회 크론 실행 대상).

기업마당 API 1회 호출로 전량(~1,500건) 수신 → program_id 업서트(멱등)
온통청년 API 전국 1회 조회 → 대구 구·군(군위 포함) 필터(중분류 '창업', ~60건) → 업서트(멱등) → 만료 갱신.
소스별 실패는 격리(로그) — 나머지 소스·만료 갱신은 항상 실행, 실패가 있으면 종료코드 1.

실행: python -m apps.funding.adapter.inbound.cli.funding_collector
"""

import sys
import traceback
from datetime import date

from apps.funding.adapter.outbound.gateways.bizinfo_gateway import BizinfoGateway
from apps.funding.adapter.outbound.gateways.youthcenter_gateway import YouthcenterGateway
from apps.funding.adapter.outbound.repositories.funding_program_repository import (
    SqlAlchemyFundingProgramRepository,
)
from apps.funding.app.ports.output.funding_program_port import (
    FundingProgramRepositoryPort,
    FundingSearchGatewayPort,
)
from apps.funding.app.use_cases.funding_program_interactor import (
    FundingProgramInteractor,
)


def collect(
    repository: FundingProgramRepositoryPort,
    gateways: dict[str, FundingSearchGatewayPort],
    today: date,
) -> int:
    """소스별 수집 → 만료 갱신. 실패한 소스 수를 반환한다."""
    interactors = {
        name: FundingProgramInteractor(repository=repository, gateway=gateway)
        for name, gateway in gateways.items()
    }
    failed = 0
    for name, interactor in interactors.items():
        try:
            inserted, updated = interactor.ingest()
            print(f"funding collector [{name}]: 신규 {inserted}건 / 갱신 {updated}건", flush=True)
        except Exception:
            failed += 1
            print(f"funding collector [{name}]: 실패", flush=True)
            traceback.print_exc()
    # 만료 갱신은 게이트웨이를 쓰지 않음 — 갱신용 게이트웨이를 새로 만들지 않고 기존 인터랙터 재사용
    expired = next(iter(interactors.values())).refresh_expirations(today)
    print(f"funding collector: 신규 만료 {expired}건", flush=True)
    return failed


def main() -> None:
    failed = collect(
        SqlAlchemyFundingProgramRepository(),
        {"bizinfo": BizinfoGateway(), "youthcenter": YouthcenterGateway()},
        date.today(),
    )
    if failed:
        print(f"funding collector: {failed}개 소스 실패", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
