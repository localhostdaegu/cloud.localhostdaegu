"""승인 결과표 CSV → regional_indicator 적재 러너 (Driving Adapter, CLI).

- 원천: DIP 센터가 **반출 승인한** 결과표 CSV (확보계획 §5-1 요청 묶음 A·B).
  D1 삼성카드·D2 SKT는 현재 미신청·미확보다 — 이 CLI는 승인본이 도착했을 때 쓰는 통로이며,
  실행 가능하다는 사실이 데이터 확보를 뜻하지 않는다.
- 컬럼: region_code,industry_id,period,indicator_key,breakdown,value,unit
  dataset_id는 CLI 인자다 — CSV 한 파일이 반출 결과표 하나(= 하나의 산식·기간·제한사항)에 대응한다.
  파일마다 dataset_id를 박아 두면 재반출본에서 값만 갈아끼울 때 출처가 어긋난다.
- 빈 문자열: industry_id·breakdown만 NULL(업종 무관·슬라이스 없음)로 해석한다.
  value가 비면 0으로 채우지 않고 거부한다 — 확보계획 §6 "누락·비공개를 0으로 바꾸지 않는다".
- 멱등: 자연키 업서트. 미승인 데이터셋이면 리포지토리가 적재를 거부한다(설계 스펙 §3-2).

실행: python -m apps.indicator.adapter.inbound.cli.load_regional_indicator <csv> --dataset-id <slug>
"""

import argparse
import csv
from pathlib import Path

from apps.indicator.adapter.outbound.repositories.regional_indicator_repository import (
    SqlAlchemyRegionalIndicatorRepository,
)
from apps.indicator.app.ports.output.regional_indicator_port import (
    RegionalIndicatorRepositoryPort,
)
from apps.indicator.domain.entities.regional_indicator_entity import RegionalIndicator

# 값이 반드시 있어야 하는 컬럼 — 비면 스킵도, 0 대체도 하지 않고 적재를 세운다
_REQUIRED_COLUMNS = ("region_code", "period", "indicator_key", "value", "unit")


def _optional(value: str | None) -> str | None:
    """빈 문자열·공백은 NULL — 업종 무관 지표와 슬라이스 없는 행을 표현한다."""
    stripped = (value or "").strip()
    return stripped or None


def parse_indicator(row: dict[str, str], dataset_id: str) -> RegionalIndicator:
    """CSV 1행 → 엔티티. 필수 컬럼이 비면 ValueError."""
    if missing := [name for name in _REQUIRED_COLUMNS if not (row.get(name) or "").strip()]:
        raise ValueError(f"필수 컬럼이 비어 있다(0으로 대체하지 않는다): {', '.join(missing)}")
    return RegionalIndicator(
        dataset_id=dataset_id,
        region_code=row["region_code"].strip(),
        industry_id=_optional(row.get("industry_id")),
        period=row["period"].strip(),
        indicator_key=row["indicator_key"].strip(),
        breakdown=_optional(row.get("breakdown")),
        value=float(row["value"].strip()),
        unit=row["unit"].strip(),
    )


def load_csv(
    path: Path, dataset_id: str, repository: RegionalIndicatorRepositoryPort
) -> int:
    """결과표 CSV 전량을 읽어 업서트하고 적재 행 수를 반환한다.

    전량을 먼저 파싱한 뒤 한 번에 넘긴다 — 뒷행의 파싱 실패가 앞행만 들어간 반쪽 적재로 남지 않게.
    """
    with open(path, encoding="utf-8-sig", newline="") as source:
        indicators = [parse_indicator(row, dataset_id) for row in csv.DictReader(source)]
    return repository.upsert(indicators)


def main() -> None:
    parser = argparse.ArgumentParser(description="승인된 지역 지표 결과표 CSV 적재")
    parser.add_argument("csv_path", type=Path, help="반출 승인된 결과표 CSV 경로")
    parser.add_argument(
        "--dataset-id", required=True, help="external_dataset.dataset_id (승인된 데이터셋 슬러그)"
    )
    args = parser.parse_args()
    loaded = load_csv(args.csv_path, args.dataset_id, SqlAlchemyRegionalIndicatorRepository())
    print(f"regional_indicator 적재 완료: {loaded}행 ({args.dataset_id})", flush=True)


if __name__ == "__main__":
    main()
