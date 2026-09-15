"""주민등록 연령별 인구 적재 검증 — 헤더 파싱·행 필터·코드 매칭·멱등 업서트."""

from sqlalchemy import func, select

from apps.master.adapter.inbound.cli.load_population import (
    find_age_file,
    load_all,
    parse_age_columns,
    parse_population_records,
)
from apps.master.adapter.outbound.orms.population_stat_orm import PopulationStatOrm
from core.matrix.grid_oracle_database_manager import session_scope

# 실 CSV 헤더 축약 표본 (연령별202604_202606 실컬럼 형식 그대로)
_HEADER = [
    "행정구역",
    "2019년12월_계_총인구수",
    "2019년12월_계_연령구간인구수",
    "2019년12월_계_0~4세",
    "2019년12월_계_100세 이상",
    "2019년11월_남_0~4세",  # 다른 월 — 제외 대상
    "2019년12월_남_총인구수",
    "2019년12월_남_0~4세",
    "2019년12월_남_100세 이상",
    "2019년12월_여_총인구수",
    "2019년12월_여_0~4세",
    "2019년12월_여_100세 이상",
]

_ROWS = [
    _HEADER,
    # 시 총계·자치구·타 시도 — 모두 적재 대상 아님
    ["대구광역시  (2700000000)", "9", "9", "1", "0", "9", "5", "1", "0", "4", "1", "0"],
    ["대구광역시 중구 (2711000000)", "9", "9", "1", "0", "9", "5", "1", "0", "4", "1", "0"],
    ["경기도 수원시 장안구 파장동(4111151500)", "9", "9", "1", "0", "9", "5", "1", "0", "4", "1", "0"],
    # 행정동 (region 존재) — 적재 대상, 천단위 콤마 파싱
    ["대구광역시 수성구 범어1동(2726052000)", "9", "9", "3", "1", "9", "5", "2,001", "1", "4", "1,002", "0"],
    # 행정동 (region 부재 — 폐지동) — 스킵 + 보고 대상
    ["대구광역시 동구 신천동(2714052000)", "9", "9", "1", "0", "9", "5", "1", "0", "4", "1", "0"],
]


def test_parse_age_columns_selects_target_period_gender_bands():
    cols = parse_age_columns(_HEADER, "201912")
    # 남/여 연령구간만 — 계·총인구수·연령구간인구수·다른 월은 제외
    assert cols == {
        7: ("M", 0, 4),
        8: ("M", 100, None),
        10: ("F", 0, 4),
        11: ("F", 100, None),
    }


def test_parse_population_records_filters_dong_rows_and_reports_skips():
    records, skipped = parse_population_records(iter(_ROWS), "201912", {"2726052000"})
    assert skipped == {"2714052000"}  # 폐지동 — region 미매칭 보고
    assert set(records) == {
        ("2726052000", "M", 0, 4, 2001),
        ("2726052000", "M", 100, None, 1),
        ("2726052000", "F", 0, 4, 1002),
        ("2726052000", "F", 100, None, 0),
    }


def test_find_age_file_locates_quarter_containing_period():
    path = find_age_file(period="202606")
    assert "202604_202606" in path.name


def test_load_latest_period_is_idempotent_and_full_coverage():
    load_all(periods=["202606"])
    load_all(periods=["202606"])  # 두 번 실행해도 중복 없이 동일해야 한다

    with session_scope() as session:
        rows = session.execute(
            select(func.count(), func.count(func.distinct(PopulationStatOrm.region_code)))
            .select_from(PopulationStatOrm)
            .where(PopulationStatOrm.period == "202606")
        ).one()
        assert rows == (144 * 2 * 21, 144)  # 행정동 144 × 남녀 2 × 5세구간 21

        # 실 CSV 교차검증 — 범어1동 2026-06 남 0~4세 (원본 424)
        value = session.execute(
            select(PopulationStatOrm.population).where(
                PopulationStatOrm.region_code == "2726051000",
                PopulationStatOrm.period == "202606",
                PopulationStatOrm.gender == "M",
                PopulationStatOrm.age_from == 0,
            )
        ).scalar()
        assert value == 424
