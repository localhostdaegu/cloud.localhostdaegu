"""consultation 경계 톨게이트 왕복 — orm_mapper(entity↔ORM), mapper(dto↔schema). DB 불필요."""

from datetime import date, datetime

from apps.consultation.adapter.inbound.api.schemas.consultation_schema import (
    ConsultationPlanRequest,
    ConsultationSessionCreateRequest,
)
from apps.consultation.adapter.inbound.mappers.consultation_mapper import (
    to_detail_response,
    to_plan_dto,
    to_plan_response,
    to_session_dto,
)
from apps.consultation.adapter.outbound.orm_mappers.consultation_orm_mapper import (
    apply_plan_to_orm,
    document_to_entity,
    document_to_orm,
    note_to_entity,
    note_to_orm,
    plan_to_entity,
    plan_to_orm,
    session_to_entity,
    session_to_orm,
)
from apps.consultation.app.dtos.consultation_dto import (
    ConsultationDetailDto,
    ConsultationNoteDto,
    ConsultationPlanDto,
    ConsultationSessionDto,
)
from apps.consultation.domain.entities.consultation_entity import (
    ConsultationDocument,
    ConsultationNote,
    ConsultationPlan,
    ConsultationSession,
    content_hash_of,
)

_NOW = datetime(2026, 9, 18, 10, 0, 0)

_PLAN_INPUT = dict(
    deposit=30_000_000,
    key_money=10_000_000,
    interior_cost=40_000_000,
    equipment_cost=20_000_000,
    monthly_rent=1_800_000,
    monthly_payroll=3_000_000,
    monthly_insurance=200_000,
    cost_ratio=0.35,
    fee_ratio=0.05,
    equity=60_000_000,
    desired_loan=50_000_000,
    loan_rate=0.045,
    expected_monthly_revenue=18_000_000,
)


def test_session_orm_mapper_round_trip_preserves_every_field():
    entity = ConsultationSession(
        session_id="abc",
        created_at=_NOW,
        updated_at=_NOW,
        region_code="2711059500",  # 행정동 10자리 (구·군 5자리가 아니다)
        industry_id="cafe",
        business_registered=False,
        business_age_months=0,
        planned_opening_date=date(2026, 12, 1),
        funds_needed_by=date(2026, 11, 1),
        owner_age=39,
        guarantee_status="in_progress",
        policy_confirmation_status="not_started",
        selected_plan_kind="current",
        change_reason="월세를 낮춘 점포로 비교",
    )

    assert session_to_entity(session_to_orm(entity)) == entity


def test_session_orm_mapper_keeps_unknown_fields_none():
    """미입력은 NULL로 남는다 — False·0으로 바뀌면 '모름'이라는 사실이 사라진다."""
    entity = ConsultationSession(session_id="abc", created_at=_NOW, updated_at=_NOW)

    restored = session_to_entity(session_to_orm(entity))

    assert restored.business_registered is None
    assert restored.business_age_months is None
    assert restored.owner_age is None
    assert restored.planned_opening_date is None
    assert restored.funds_needed_by is None
    assert restored.region_code is None
    assert restored.industry_id is None


def test_plan_orm_mapper_round_trip_preserves_inputs_and_snapshot():
    entity = ConsultationPlan(
        plan_id="p1",
        session_id="abc",
        plan_kind="baseline",
        computed_at=_NOW,
        reserve_months=6,
        operating_reserve=30_000_000,
        **_PLAN_INPUT,
    )

    assert plan_to_entity(plan_to_orm(entity)) == entity


def test_apply_plan_to_orm_keeps_row_identity():
    """멱등 upsert 갱신 — plan_id·session_id·plan_kind는 행의 식별자라 덮어쓰지 않는다."""
    stored = plan_to_orm(
        ConsultationPlan(
            plan_id="kept", session_id="abc", plan_kind="current", computed_at=_NOW, **_PLAN_INPUT
        )
    )
    incoming = ConsultationPlan(
        plan_id="new",
        session_id="abc",
        plan_kind="current",
        computed_at=_NOW,
        **{**_PLAN_INPUT, "monthly_rent": 2_500_000},
    )

    apply_plan_to_orm(incoming, stored)

    assert stored.plan_id == "kept"
    assert stored.monthly_rent == 2_500_000


def test_note_orm_mapper_round_trip():
    entity = ConsultationNote(
        session_id="abc", note_type="open_question", note_order=1, content="인테리어 견적 미확인"
    )

    assert note_to_entity(note_to_orm(entity)) == entity


def test_document_hash_is_sha256_of_markdown():
    """content_hash는 내용 변경 확인용 sha256이다 — 블록체인 앵커링이 아니다."""
    document = ConsultationDocument(
        document_id="d1",
        session_id="abc",
        plan_id="p1",
        purpose="handoff",
        generated_at=_NOW,
        content_markdown="# 상담자료",
    )

    assert document.content_hash == content_hash_of("# 상담자료")
    assert document_to_entity(document_to_orm(document)) == document


def test_create_request_maps_omitted_fields_to_none():
    request = ConsultationSessionCreateRequest()

    dto = to_session_dto(request)

    assert dto.business_registered is None
    assert dto.owner_age is None
    assert dto.guarantee_status == "unknown"
    assert dto.change_reason == ""


def test_create_request_distinguishes_false_from_omitted():
    dto = to_session_dto(
        ConsultationSessionCreateRequest(business_registered=False, business_age_months=0)
    )

    assert dto.business_registered is False
    assert dto.business_age_months == 0


def test_plan_request_maps_to_dto_with_zero_snapshot_when_omitted():
    dto = to_plan_dto("current", ConsultationPlanRequest(**_PLAN_INPUT))

    assert dto.plan_kind == "current"
    assert dto.deposit == 30_000_000
    assert dto.capex == 0  # 미제공 스냅샷 — 서버가 계산해 채우지 않는다
    assert dto.plan_id is None


def test_plan_dto_maps_to_response():
    response = to_plan_response(
        ConsultationPlanDto(plan_kind="baseline", plan_id="p1", computed_at=_NOW, **_PLAN_INPUT)
    )

    assert response.plan_id == "p1"
    assert response.plan_kind == "baseline"
    assert response.expected_monthly_revenue == 18_000_000


def test_detail_dto_maps_to_response_with_plans_and_notes():
    detail = ConsultationDetailDto(
        session=ConsultationSessionDto(session_id="abc", owner_age=None),
        plans=[ConsultationPlanDto(plan_kind="current", **_PLAN_INPUT)],
        notes=[ConsultationNoteDto(note_type="assumption", note_order=1, content="금리 기본값 사용")],
    )

    response = to_detail_response(detail)

    assert response.session.session_id == "abc"
    assert response.session.owner_age is None
    assert len(response.plans) == 1
    assert response.notes[0].content == "금리 기본값 사용"
