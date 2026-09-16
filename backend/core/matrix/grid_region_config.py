"""대구 지역 구성 — 서울 상수를 대체하는 단일 원천.
opn_authority_code는 2026-09-16 인허가 실호출로 8개 전부 확정 (docs/apilist.md §11)."""
from dataclasses import dataclass

REGION_NAME = "대구"
CSV_SIDO_PREFIX = "대구"          # 주민등록 CSV 행 필터 ("대구광역시 …")
SIDO_ADM_PREFIX = "27"            # 행안부 시도코드 (region_code·주민등록·인허가)
KOSTAT_SIDO_PREFIX = "22"         # 통계청 시도코드 — 브이월드 lt_c_cademd adm_cd 앞 2자리 (서울은 11로 동일해 구분 안 됐음)
LAT_RANGE = (35.60, 36.02)
LNG_RANGE = (128.35, 128.77)
MAP_CENTER = (128.60, 35.87)      # (lng, lat)

@dataclass(frozen=True)
class DistrictInfo:
    name: str
    opn_authority_code: str       # 인허가 OPN_ATMY_GRP_CD
    lawd_cd: str                  # 실거래가 LAWD_CD (= district_code)

DISTRICTS: dict[str, DistrictInfo] = {
    "27110": DistrictInfo("중구", "3410000", "27110"),
    "27140": DistrictInfo("동구", "3420000", "27140"),
    "27170": DistrictInfo("서구", "3430000", "27170"),
    "27200": DistrictInfo("남구", "3440000", "27200"),
    "27230": DistrictInfo("북구", "3450000", "27230"),
    "27260": DistrictInfo("수성구", "3460000", "27260"),
    "27290": DistrictInfo("달서구", "3470000", "27290"),
    "27710": DistrictInfo("달성군", "3480000", "27710"),
}
