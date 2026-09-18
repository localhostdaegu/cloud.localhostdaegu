"""승인 결과표 CSV → regional_indicator 엔티티 파싱·ORM 왕복 (DB 불필요).

CSV 컬럼은 region_code,industry_id,period,indicator_key,breakdown,value,unit이며
dataset_id는 CLI 인자다 — 한 파일이 한 반출 결과표에 대응하기 때문이다.
빈 문자열은 NULL(업종 무관·슬라이스 없음)이고, 값 누락은 0이 아니다(확보계획 §6).
"""

from pathlib import Path

import pytest

from apps.indicator.adapter.inbound.cli.load_regional_indicator import (
    load_csv,
    parse_indicator,
)
from apps.indicator.adapter.outbound.orm_mappers.regional_indicator_orm_mapper import (
    to_entity,
    to_orm,
)
from apps.indicator.domain.entities.regional_indicator_entity import RegionalIndicator

_DATASET = "dip-samsung-card-2024"

# 합성 픽스처 — 센터 D1·D2는 미신청·미확보라 실제 반출값이 아니다
_CSV = (
    "region_code,industry_id,period,indicator_key,breakdown,value,unit\n"
    "2711059500,cafe,202412,card_amt_index,weekend,112.4,지수\n"
    "2711059500,,202412,living_pop_worker,time_09_13,8321.5,명\n"
)


def test_parse_indicator_reads_every_column():
    row = {
        "region_code": "2711059500",
        "industry_id": "cafe",
        "period": "202412",
        "indicator_key": "card_amt_index",
        "breakdown": "weekend",
        "value": "112.4",
        "unit": "지수",
    }
    assert parse_indicator(row, _DATASET) == RegionalIndicator(
        dataset_id=_DATASET,
        region_code="2711059500",
        industry_id="cafe",
        period="202412",
        indicator_key="card_amt_index",
        breakdown="weekend",
        value=112.4,
        unit="지수",
    )


def test_blank_industry_and_breakdown_become_null():
    row = {
        "region_code": "2711059500",
        "industry_id": "",
        "period": "202412",
        "indicator_key": "living_pop_worker",
        "breakdown": "  ",
        "value": "8321.5",
        "unit": "명",
    }
    indicator = parse_indicator(row, _DATASET)
    assert indicator.industry_id is None  # 생활인구 등 업종 무관 지표
    assert indicator.breakdown is None


def test_blank_value_is_rejected_not_zeroed():
    row = {
        "region_code": "2711059500",
        "industry_id": "",
        "period": "202412",
        "indicator_key": "living_pop_worker",
        "breakdown": "",
        "value": "",
        "unit": "명",
    }
    with pytest.raises(ValueError, match="value"):
        parse_indicator(row, _DATASET)


def test_orm_round_trip_preserves_null_slices():
    indicator = RegionalIndicator(
        dataset_id=_DATASET,
        region_code="2711059500",
        industry_id=None,
        period="202412",
        indicator_key="living_pop_worker",
        breakdown=None,
        value=8321.5,
        unit="명",
    )
    assert to_entity(to_orm(indicator)) == indicator


def test_load_csv_stamps_the_cli_dataset_id_on_every_row(tmp_path: Path):
    path = tmp_path / "dip_card_context.csv"
    path.write_text(_CSV, encoding="utf-8")
    captured: list[list[RegionalIndicator]] = []

    class _RecordingRepository:
        def upsert(self, indicators: list[RegionalIndicator]) -> int:
            captured.append(indicators)
            return len(indicators)

    assert load_csv(path, _DATASET, _RecordingRepository()) == 2
    assert [i.dataset_id for i in captured[0]] == [_DATASET, _DATASET]
    assert [i.industry_id for i in captured[0]] == ["cafe", None]
