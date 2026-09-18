"""external_dataset 엔티티 ↔ ORM 왕복 — 출처·산식·승인 상태 보존 (DB 불필요).

확보계획 §6 "목록·수치·출처가 함께 이동해야 한다" — 경계를 넘을 때 산식·제한사항이
떨어져 나가지 않는지, 미승인(export_approved_on=None)이 승인으로 둔갑하지 않는지 확인한다.
"""

from datetime import date

from apps.dataset.adapter.outbound.orm_mappers.external_dataset_orm_mapper import (
    to_entity,
    to_orm,
)
from apps.dataset.domain.entities.external_dataset_entity import ExternalDataset

# 확보계획 §3 D1 삼성카드 — 실제 반출본이 아닌 형식 확인용 합성 값
_APPROVED = ExternalDataset(
    dataset_id="dip-samsung-card-2024",
    name="동·업종별 소비 특성 결과표",
    provider="삼성카드",
    source_channel="dip_center",
    period_start="202401",
    period_end="202512",
    aggregation_note="동×업종×월 AMT 합계의 전년 동월 대비 변화율",
    restriction_note="점포당 매출로 환산 금지. 카드사 간 추이 연결 금지",
    export_approved_on=date(2026, 9, 18),
    approval_ref="DIP-2026-0001",
    source_url=None,
    catalog_page="18",
)

_UNAPPROVED = ExternalDataset(
    dataset_id="dip-skt-living-pop",
    name="동별 생활인구 결과표",
    provider="SK텔레콤",
    source_channel="dip_center",
    period_start="202401",
    period_end="202512",
    aggregation_note="동×시간대 평균 생활인구 (분모: 해당 월 일수)",
    restriction_note="시간대 합산을 방문자 수로 설명 금지",
    export_approved_on=None,
    approval_ref=None,
    source_url=None,
    catalog_page="54-58",
)


def test_orm_round_trip_preserves_every_field():
    assert to_entity(to_orm(_APPROVED)) == _APPROVED


def test_unapproved_dataset_stays_unapproved_across_the_boundary():
    assert to_entity(to_orm(_UNAPPROVED)).export_approved_on is None


def test_notes_survive_the_boundary():
    orm = to_orm(_APPROVED)
    assert orm.aggregation_note == _APPROVED.aggregation_note
    assert orm.restriction_note == _APPROVED.restriction_note
