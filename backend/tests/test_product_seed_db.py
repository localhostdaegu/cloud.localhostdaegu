"""finance_product 시드 → DB → 로더 왕복 (실제 Repository/DB, 스펙 §2-1~§2-5).

⚠ alembic 리비전은 작업 D 담당이다. 테이블이 생기기 전까지 이 파일은 실패한다.
"""

import pytest
from sqlalchemy import delete

from apps.matching.adapter.outbound.gateways.manual_product_gateway import (
    load_all_products,
)
from apps.product.adapter.inbound.cli.seed_finance_product import read_products, seed_all
from apps.product.adapter.outbound.orms.finance_product_category_orm import (
    FinanceProductCategoryOrm,
)
from apps.product.adapter.outbound.orms.finance_product_orm import FinanceProductOrm
from apps.product.adapter.outbound.orms.product_consultation_metadata_orm import (
    ProductConsultationMetadataOrm,
)
from apps.product.adapter.outbound.orms.product_procedure_step_orm import (
    ProductProcedureStepOrm,
)
from apps.product.adapter.outbound.repositories.finance_product_repository import (
    SqlAlchemyFinanceProductRepository,
)
from core.matrix.grid_oracle_database_manager import session_scope


def _cleanup() -> None:
    with session_scope() as session:
        session.execute(delete(FinanceProductCategoryOrm))
        session.execute(delete(ProductConsultationMetadataOrm))
        session.execute(delete(ProductProcedureStepOrm))
        session.execute(delete(FinanceProductOrm))


@pytest.fixture
def clean_products():
    _cleanup()
    load_all_products.cache_clear()
    yield
    _cleanup()
    load_all_products.cache_clear()


def test_seed_is_idempotent_and_roundtrips_through_list_all(clean_products):
    repository = SqlAlchemyFinanceProductRepository()

    inserted, updated = seed_all(repository)
    assert (inserted, updated) == (12, 0)

    again = seed_all(repository)
    assert again == (0, 0)  # 재실행 멱등 — 내용 동일이면 갱신 0건

    stored = {p.product_id: p for p in repository.list_all()}
    assert stored == {p.product_id: p for p in read_products()}


def test_loader_reads_db_and_matches_the_json_payload(clean_products):
    """시드 전(JSON 폴백)과 시드 후(DB)의 GET /matching 입력이 같아야 한다."""
    before = sorted(load_all_products(), key=lambda p: p["product_id"])
    load_all_products.cache_clear()

    seed_all(SqlAlchemyFinanceProductRepository())
    after = sorted(load_all_products(), key=lambda p: p["product_id"])

    assert after == before


def test_seed_fails_on_industry_id_missing_from_master(clean_products):
    """industry 에 없는 업종 문자열은 조용히 버리지 않고 시드를 실패시킨다 (스펙 §2-2)."""
    products = read_products()
    products[0].category = ["not_an_industry"]

    with pytest.raises(ValueError, match="not_an_industry"):
        SqlAlchemyFinanceProductRepository().upsert(products)


def test_seed_writes_category_rows_for_known_industry(clean_products):
    products = read_products()
    products[0].category = ["cafe", "restaurant"]
    # '해당 업종 없음'([])은 합성 표본으로 검증한다 — 운영 JSON 에 이 상태가 남아 있는지에
    # 기대면 데이터가 바뀔 때 3상태 보존이 조용히 검증되지 않는다(실제로 그렇게 됐다).
    products[1].category = []

    repository = SqlAlchemyFinanceProductRepository()
    repository.upsert(products)

    stored = {p.product_id: p for p in repository.list_all()}
    assert stored[products[0].product_id].category == ["cafe", "restaurant"]
    # [] 인 상품은 category 행 0건이지만 '전부 탈락'으로 복원된다
    assert stored[products[1].product_id].category == []


def test_read_products_records_source_file():
    by_id = {p.product_id: p for p in read_products()}

    assert by_id["imbank-1"].source_file == "imbank_products.json"
    assert by_id["dgsinbo-1"].source_file == "dgsinbo_products.json"
    assert by_id["youth-1"].source_file == "daegu_youth_startup.json"
    assert len(by_id) == 12


def test_consultation_metadata_reaches_db_and_comes_back(clean_products, tmp_path):
    """전환계획 T3 전제 — JSON 의 상담 메타데이터가 자식 2테이블까지 가고 그대로 복원된다.
    이 경로가 없으면 T3 가 원문을 조사해 JSON 에 적어도 두 테이블은 0행으로 남는다."""
    import json
    from datetime import date

    (tmp_path / "imbank_products.json").write_text(
        json.dumps(
            [
                {
                    "product_id": "test-consult-1",
                    "provider": "테스트 기관",
                    "provider_type": "bank",
                    "product_name": "합성 테스트 상품",
                    "target": "테스트",
                    "region": "대구",
                    "business_age_min": 0,
                    "business_age_max": None,
                    "category": None,
                    "owner_age_max": None,
                    "loan_limit": 10_000_000,
                    "interest_rate": None,
                    "guarantee_fee": None,
                    "url": "https://example.org",
                    "source_url": "https://example.org",
                    "consultation_metadata": {
                        "bank_connection": "direct",
                        "bank_connection_source_url": "https://example.org/notice",
                        "business_registration_required": True,
                        "verified_at": "2026-09-18",
                        "prerequisites": ["소진공 확인서 발급"],
                        "application_steps": ["영업점 방문 상담"],
                        "documents": ["사업자등록증"],
                    },
                }
            ],
            ensure_ascii=False,
        )
    )

    repository = SqlAlchemyFinanceProductRepository()
    assert seed_all(repository, tmp_path) == (1, 0)

    (stored,) = repository.list_all()
    assert stored.consultation.bank_connection == "direct"
    assert stored.consultation.business_registration_required is True
    assert stored.consultation.verified_at == date(2026, 9, 18)
    assert [(s.step_type, s.step_order, s.description) for s in stored.procedure_steps] == [
        ("application_step", 1, "영업점 방문 상담"),
        ("document", 1, "사업자등록증"),
        ("prerequisite", 1, "소진공 확인서 발급"),
    ]

    with session_scope() as session:
        assert session.query(ProductConsultationMetadataOrm).count() == 1
        assert session.query(ProductProcedureStepOrm).count() == 3
