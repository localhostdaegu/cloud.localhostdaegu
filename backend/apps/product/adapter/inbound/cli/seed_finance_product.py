"""금융상품 시드 러너 (Driving Adapter, CLI).

data/manual/*.json 3파일 → finance_product 업서트(멱등). DB 가 정본이고 JSON 은 시드 입력이다(스펙 §2).
상담 메타데이터·절차는 consultation_metadata 키가 있을 때만 읽는다. 없으면 미확인으로 남긴다(§10-3).
industry 마스터에 없는 업종 문자열을 만나면 리포지토리가 ValueError 로 실패시킨다(조용히 버리지 않는다).

실행: python -m apps.product.adapter.inbound.cli.seed_finance_product
"""

import json
from datetime import date
from pathlib import Path

from apps.product.adapter.outbound.repositories.finance_product_repository import (
    SqlAlchemyFinanceProductRepository,
)
from apps.product.app.ports.output.finance_product_port import FinanceProductRepositoryPort
from apps.product.domain.entities.finance_product_entity import (
    ConsultationMetadata,
    FinanceProduct,
    ProcedureStep,
)

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

# §5-2 리스트 3종 → product_procedure_step.step_type 판별자
_STEP_KINDS = (
    ("prerequisite", "prerequisites"),
    ("application_step", "application_steps"),
    ("document", "documents"),
)


def _to_consultation(raw: dict | None) -> ConsultationMetadata | None:
    """consultation_metadata 키가 없으면 미확인(None). 개별 항목 누락도 None 으로 남긴다 —
    등록 필요 여부를 False 로, 확인일을 오늘로 바꾸지 않는다(§4-2)."""
    if raw is None:
        return None
    verified_at = raw.get("verified_at")
    return ConsultationMetadata(
        bank_connection=raw["bank_connection"],
        bank_connection_source_url=raw.get("bank_connection_source_url"),
        business_registration_required=raw.get("business_registration_required"),
        verified_at=date.fromisoformat(verified_at) if verified_at else None,
    )


def _to_procedure_steps(raw: dict | None) -> list[ProcedureStep]:
    """상품별 순서를 종류마다 1부터 보존한다. 정렬 기준은 orm_mapper.to_entity 와 같게 두어
    JSON 읽기와 DB 왕복 결과가 같은 순서가 되게 한다."""
    if raw is None:
        return []
    return sorted(
        (
            ProcedureStep(step_type, order, description)
            for step_type, key in _STEP_KINDS
            for order, description in enumerate(raw.get(key) or (), start=1)
        ),
        key=lambda step: (step.step_type, step.step_order),
    )


def read_products(data_dir: Path = _MANUAL_DIR) -> list[FinanceProduct]:
    """수기 JSON 3파일을 엔티티로 읽는다. 누락 필드는 KeyError 로 즉시 드러낸다."""
    products: list[FinanceProduct] = []
    for source_file in _SOURCE_FILES:
        file_path = data_dir / source_file
        if not file_path.exists():
            continue
        for raw in json.loads(file_path.read_text()):
            metadata = raw.get("consultation_metadata")
            products.append(
                FinanceProduct(
                    **{name: raw[name] for name in _JSON_FIELDS},
                    source_file=source_file,
                    consultation=_to_consultation(metadata),
                    procedure_steps=_to_procedure_steps(metadata),
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
