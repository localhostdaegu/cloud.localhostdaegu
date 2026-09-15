from core.matrix.grid_region_config import DISTRICTS, LAT_RANGE, LNG_RANGE, SIDO_ADM_PREFIX


def test_daegu_districts_eight_without_gunwi():
    assert len(DISTRICTS) == 8
    assert "27720" not in DISTRICTS          # 군위군 제외
    assert DISTRICTS["27110"].name == "중구"
    assert DISTRICTS["27110"].opn_authority_code == "3410000"


def test_daegu_bbox():
    assert LAT_RANGE == (35.60, 36.02)
    assert LNG_RANGE == (128.35, 128.77)
    assert SIDO_ADM_PREFIX == "27"
