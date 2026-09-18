"""수기 JSON 의 상담 메타데이터 → 엔티티 파싱 (DB·네트워크 없음).

전환계획 T3 가 data/manual/*.json 에 상담 메타데이터를 채우면 이 경로로 DB 까지 간다.
파싱이 없으면 JSON 에 적어도 product_consultation_metadata·product_procedure_step 은 0행으로 남는다.
"""

import json
from datetime import date
from pathlib import Path

from apps.product.adapter.inbound.cli.seed_finance_product import read_products
from apps.product.domain.entities.finance_product_entity import ConsultationMetadata, ProcedureStep

_BASE = {
    "product_id": "test-1",
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
}


def _write(tmp_path: Path, raw: dict) -> Path:
    (tmp_path / "imbank_products.json").write_text(json.dumps([raw], ensure_ascii=False))
    return tmp_path


def test_product_without_consultation_metadata_stays_unverified(tmp_path):
    """메타데이터가 없으면 미확인이다 — 추정으로 채우지 않는다(§10-3)."""
    (product,) = read_products(_write(tmp_path, dict(_BASE)))

    assert product.consultation is None
    assert product.procedure_steps == []


def test_consultation_metadata_is_parsed_into_entity(tmp_path):
    """§5-2 메타데이터 — 확인일은 date 로, 미확인 항목은 None 으로 보존한다."""
    raw = dict(_BASE)
    raw["consultation_metadata"] = {
        "bank_connection": "direct",
        "bank_connection_source_url": "https://example.org/notice",
        "business_registration_required": True,
        "verified_at": "2026-09-18",
        "prerequisites": [],
        "application_steps": [],
        "documents": [],
    }

    (product,) = read_products(_write(tmp_path, raw))

    assert product.consultation == ConsultationMetadata(
        bank_connection="direct",
        bank_connection_source_url="https://example.org/notice",
        business_registration_required=True,
        verified_at=date(2026, 9, 18),
    )


def test_missing_metadata_keys_stay_none_instead_of_false(tmp_path):
    """등록 필요 여부 미확인을 False 로 바꾸지 않는다(§4-2)."""
    raw = dict(_BASE)
    raw["consultation_metadata"] = {"bank_connection": "unverified"}

    (product,) = read_products(_write(tmp_path, raw))

    assert product.consultation == ConsultationMetadata(bank_connection="unverified")
    assert product.consultation.business_registration_required is None
    assert product.consultation.verified_at is None


def test_three_lists_become_ordered_procedure_steps(tmp_path):
    """선행절차·신청경로·준비서류의 상품별 순서를 1부터 보존한다(§10-3)."""
    raw = dict(_BASE)
    raw["consultation_metadata"] = {
        "bank_connection": "linked",
        "prerequisites": ["소진공 정책자금 지원대상 확인서 발급"],
        "application_steps": ["영업점 방문 상담", "서류 제출"],
        "documents": ["사업자등록증", "임대차계약서"],
    }

    (product,) = read_products(_write(tmp_path, raw))

    assert product.procedure_steps == [
        ProcedureStep("application_step", 1, "영업점 방문 상담"),
        ProcedureStep("application_step", 2, "서류 제출"),
        ProcedureStep("document", 1, "사업자등록증"),
        ProcedureStep("document", 2, "임대차계약서"),
        ProcedureStep("prerequisite", 1, "소진공 정책자금 지원대상 확인서 발급"),
    ]
