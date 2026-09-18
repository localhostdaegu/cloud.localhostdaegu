"""금융상품 시드 러너 (Driving Adapter, CLI).

data/manual/*.json 3파일 → finance_product 업서트(멱등). DB 가 정본이고 JSON 은 시드 입력이다(스펙 §2).
상담 메타데이터·절차는 JSON 에 아직 없으므로 이번 시드에서는 행이 생기지 않는다 — 미확인으로 남는다.
industry 마스터에 없는 업종 문자열을 만나면 리포지토리가 ValueError 로 실패시킨다(조용히 버리지 않는다).

실행: python -m apps.product.adapter.inbound.cli.seed_finance_product
"""

import json
from pathlib import Path

from apps.product.adapter.outbound.repositories.finance_product_repository import (
    SqlAlchemyFinanceProductRepository,
)
from apps.product.app.ports.output.finance_product_port import FinanceProductRepositoryPort
from apps.product.domain.entities.finance_product_entity import FinanceProduct

_MANUAL_DIR = Path(__file__).resolve().parents[6] / "data" / "manual"
_SOURCE_FILES = ("imbank_products.json", "dgsinbo_products.json", "daegu_youth_startup.json")

_JSON_FIELDS = (
    "product_id",
    "provider",
    "provider_type",
    "product_name",
    "target",
    "region",
    "business_age_min",
    "business_age_max",
    "owner_age_max",
    "loan_limit",
    "interest_rate",
    "guarantee_fee",
    "url",
    "source_url",
    "category",
)


def read_products(data_dir: Path = _MANUAL_DIR) -> list[FinanceProduct]:
    """수기 JSON 3파일을 엔티티로 읽는다. 누락 필드는 KeyError 로 즉시 드러낸다."""
    products: list[FinanceProduct] = []
    for source_file in _SOURCE_FILES:
        file_path = data_dir / source_file
        if not file_path.exists():
            continue
        for raw in json.loads(file_path.read_text()):
            products.append(
                FinanceProduct(
                    **{name: raw[name] for name in _JSON_FIELDS},
                    source_file=source_file,
                )
            )
    return products


def seed_all(
    repository: FinanceProductRepositoryPort | None = None,
    data_dir: Path = _MANUAL_DIR,
) -> tuple[int, int]:
    repository = repository or SqlAlchemyFinanceProductRepository()
    return repository.upsert(read_products(data_dir))


def main() -> None:
    inserted, updated = seed_all()
    print(f"finance product seed: 신규 {inserted}건 / 갱신 {updated}건", flush=True)


if __name__ == "__main__":
    main()
