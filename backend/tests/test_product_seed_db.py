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

    repository = SqlAlchemyFinanceProductRepository()
    repository.upsert(products)

    stored = {p.product_id: p for p in repository.list_all()}
    assert stored[products[0].product_id].category == ["cafe", "restaurant"]
    # [] 인 상품은 category 행 0건이지만 '전부 탈락'으로 복원된다
    empty_ids = [p.product_id for p in products if p.category == []]
    assert empty_ids, "category [] 표본이 data/manual 에 없음"
    assert stored[empty_ids[0]].category == []


def test_read_products_records_source_file():
    by_id = {p.product_id: p for p in read_products()}

    assert by_id["imbank-1"].source_file == "imbank_products.json"
    assert by_id["dgsinbo-1"].source_file == "dgsinbo_products.json"
    assert by_id["youth-1"].source_file == "daegu_youth_startup.json"
    assert len(by_id) == 12
