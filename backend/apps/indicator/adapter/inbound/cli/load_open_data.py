"""공개 데이터 6종 → regional_indicator 적재 러너 (Driving Adapter, CLI).

data/raw/daegu_extra/ 의 공공데이터포털 파일(MANIFEST.md)과 브이월드 전통시장 API를 행정동 지표로 바꾼다.
전부 공개 자료라 센터 반출 심사 대상이 아니지만, 출처·산식·제한사항을 같은 external_dataset에 남긴다
(확보계획 §6 "목록·수치·출처가 함께 이동"). export_approved_on 은 공개 파일의 수령일이다.

데이터셋별 로더(Strategy) — 각 로더는 지표 목록을 돌려주고 CLI는 순서대로 업서트한다.
- open-traditional-market : 브이월드 LT_P_TRADSIJANG 좌표 → 행정동 시장 수
- open-nadeul-store       : 나들가게 GPS → 행정동 나들가게 수
- open-baeknyeon-store    : 백년가게 주소 → 브이월드 지오코더 → 행정동 백년가게 수
- open-onnuri-merchant    : 온누리 가맹점 소속 시장명 → 전통시장 행정동 → 행정동 가맹점 수 (시장명 미매칭은 제외)
- open-subway-ridership   : 역 주소 → 지오코더 → 행정동, 월별 승차·시간대별 승차(2026-01~07)

지오코딩 결과는 data/raw/daegu_extra/*_geocoded.csv 에 캐시한다 (재실행 시 API 호출 없음).

실행: python -m apps.indicator.adapter.inbound.cli.load_open_data [--only <dataset_id>,...]
"""

import argparse
import csv
import json
import re
import statistics
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import httpx
from sqlalchemy import delete, select

from apps.dataset.adapter.outbound.repositories.external_dataset_repository import (
    SqlAlchemyExternalDatasetRepository,
)
from apps.dataset.domain.entities.external_dataset_entity import ExternalDataset
from apps.indicator.adapter.outbound.orms.regional_indicator_orm import RegionalIndicatorOrm
from apps.indicator.adapter.outbound.repositories.regional_indicator_repository import (
    SqlAlchemyRegionalIndicatorRepository,
)
from apps.indicator.domain.entities.regional_indicator_entity import RegionalIndicator
from apps.master.adapter.outbound.orms.region_orm import RegionOrm
from core.matrix.grid_geo_region_index import RegionIndex
from core.matrix.grid_keymaker_secret_manager import get_settings
from core.matrix.grid_oracle_database_manager import session_scope

_REPO_ROOT = Path(__file__).resolve().parents[6]
_DATA_DIR = _REPO_ROOT / "data" / "raw" / "daegu_extra"
_DOWNLOADED_ON = date(2026, 9, 19)
_DAEGU_BBOX = "BOX(128.35,35.60,128.77,36.02)"
_VWORLD = "https://api.vworld.kr/req"

# 승하차 파일의 옛 역명 → 역 주소 파일의 현재 역명 (2호선 대공원→수성알파시티, 3호선 어린이회관→어린이세상)
STATION_ALIASES = {"대공원": "수성알파시티", "어린이회관": "어린이세상"}
# 역 주소 파일의 오타 — 지오코딩 전에 교정
_ADDRESS_FIXES = {"달구벌대호": "달구벌대로"}

HOUR_BANDS = {
    "time_05_10": range(5, 10),
    "time_10_14": range(10, 14),
    "time_14_18": range(14, 18),
    "time_18_24": range(18, 24),
}


# ---------- 순수 함수 ----------


def count_by_region(codes: list[str | None]) -> dict[str, int]:
    return dict(Counter(code for code in codes if code is not None))


def normalize_station_name(name: str) -> str:
    """'대곡(정부대구청사)'·'명덕1'(환승역 호선 번호) → '대곡'·'명덕'. 옛 역명은 현재 역명으로."""
    base = re.sub(r"\(.*?\)", "", name).strip()
    base = re.sub(r"\d+$", "", base)
    return STATION_ALIASES.get(base, base)


def normalize_address(address: str) -> str:
    """지오코더 입력 정리 — 괄호 동명 제거, '지하' 제거(브이월드가 지하 주소를 엉뚱한 지점으로 돌려준다, 2026-09-19 실측), 오타 교정."""
    cleaned = re.sub(r"\(.*?\)", "", address)
    cleaned = re.sub(r"지하\s*", "", cleaned)
    for wrong, right in _ADDRESS_FIXES.items():
        cleaned = cleaned.replace(wrong, right)
    return re.sub(r"\s+", " ", cleaned).strip()


def normalize_market_name(name: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", name)


def match_market_region(merchant_market: str, region_by_market: dict[str, str]) -> str | None:
    """가맹점의 소속 시장명이 전통시장명으로 시작하면 그 시장의 행정동. 가장 긴 시장명 우선."""
    target = normalize_market_name(merchant_market)
    for market in sorted(region_by_market, key=len, reverse=True):
        if target.startswith(normalize_market_name(market)):
            return region_by_market[market]
    return None


def sum_hour_bands(row: dict[str, str]) -> dict[str, int]:
    out = {}
    for band, hours in HOUR_BANDS.items():
        out[band] = sum(int(row.get(f"{h:02d}시-{h + 1:02d}시", "0") or 0) for h in hours)
    return out


# ---------- 외부 호출 ----------


class VworldClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._params = {"key": settings.vworld_api_key, "domain": settings.vworld_service_domain, "format": "json"}
        self._client = httpx.Client(timeout=60.0)

    def traditional_markets(self) -> list[dict]:
        response = self._client.get(
            f"{_VWORLD}/data",
            params={**self._params, "service": "data", "request": "GetFeature", "data": "LT_P_TRADSIJANG",
                    "geomFilter": _DAEGU_BBOX, "size": "1000", "crs": "EPSG:4326"},
        ).json()["response"]
        if response["status"] != "OK":
            raise RuntimeError(f"브이월드 전통시장 조회 실패: {response.get('error')}")
        return response["result"]["featureCollection"]["features"]

    def geocode(self, address: str) -> tuple[float, float] | None:
        """도로명 → 지번 순으로 시도. 실패하면 None (0,0 으로 채우지 않는다)."""
        address = normalize_address(address)
        for addr_type in ("road", "parcel"):
            response = self._client.get(
                f"{_VWORLD}/address",
                params={**self._params, "service": "address", "request": "getcoord", "version": "2.0",
                        "crs": "EPSG:4326", "address": address, "type": addr_type},
            ).json()["response"]
            if response["status"] == "OK":
                point = response["result"]["point"]
                return float(point["x"]), float(point["y"])
        return None


def _geocode_cached(client: VworldClient, cache_path: Path, keyed_addresses: dict[str, str]) -> dict[str, tuple[float, float]]:
    """key → (lng, lat). 캐시 파일에 있는 key는 재호출하지 않는다."""
    cached: dict[str, tuple[float, float]] = {}
    if cache_path.exists():
        with cache_path.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row["lng"]:
                    cached[row["key"]] = (float(row["lng"]), float(row["lat"]))
    missing = {k: a for k, a in keyed_addresses.items() if k not in cached}
    failed = []
    for key, address in missing.items():
        point = client.geocode(address)
        if point is None:
            failed.append(key)
        else:
            cached[key] = point
    with cache_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["key", "address", "lng", "lat"])
        for key, address in keyed_addresses.items():
            lng, lat = cached.get(key, ("", ""))
            writer.writerow([key, address, lng, lat])
    if failed:
        print(f"  지오코딩 실패 {len(failed)}건 (제외): {failed[:5]}", flush=True)
    return cached


def _region_index() -> RegionIndex:
    with session_scope() as session:
        refs = session.execute(
            select(RegionOrm.region_code, RegionOrm.geometry_ref).where(RegionOrm.geometry_ref.is_not(None))
        ).all()
    return RegionIndex.from_refs(_REPO_ROOT, [tuple(r) for r in refs])


def _read_csv(name: str) -> list[dict[str, str]]:
    with (_DATA_DIR / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _counts_to_indicators(dataset_id: str, key: str, period: str, counts: dict[str, int], unit: str = "곳") -> list[RegionalIndicator]:
    return [
        RegionalIndicator(dataset_id=dataset_id, region_code=code, period=period, indicator_key=key, value=float(n), unit=unit)
        for code, n in sorted(counts.items())
    ]


# ---------- 로더 (Strategy) ----------


class OpenDataLoader(ABC):
    dataset: ExternalDataset

    def __init__(self, index: RegionIndex, vworld: VworldClient) -> None:
        self._index = index
        self._vworld = vworld

    @abstractmethod
    def load(self) -> list[RegionalIndicator]: ...


class TraditionalMarketLoader(OpenDataLoader):
    dataset = ExternalDataset(
        dataset_id="open-traditional-market", name="브이월드 전통시장 위치(LT_P_TRADSIJANG) — 대구",
        provider="소상공인시장진흥공단(브이월드 제공)", source_channel="open_api",
        period_start="202609", period_end="202609",
        aggregation_note="행정동 경계 안에 위치한 전통시장 점(Point) 수. 대구 bbox 조회 후 주소에 '대구'가 있는 것만",
        restriction_note="시장 규모(점포수)·매출을 나타내지 않는다. 시장 반경 상권 판정은 별도 계산이며 이 수치로 대체하지 않는다",
        export_approved_on=_DOWNLOADED_ON, approval_ref="공개 API — 반출 심사 대상 아님",
        source_url="https://api.vworld.kr/req/data?data=LT_P_TRADSIJANG", catalog_page=None,
    )
    market_region: dict[str, str] = {}  # 시장명 → 행정동 (온누리 로더가 재사용)

    def load(self) -> list[RegionalIndicator]:
        cache = _DATA_DIR / "market_points_vworld.geojson"
        if cache.exists():
            features = json.loads(cache.read_text(encoding="utf-8"))["features"]
        else:
            features = self._vworld.traditional_markets()
            cache.write_text(json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False), encoding="utf-8")
        daegu = [f for f in features if "대구" in ((f["properties"].get("adr_road") or "") + (f["properties"].get("adr_jibun") or ""))]
        codes = self._index.locate_many([f["geometry"]["coordinates"][0] for f in daegu], [f["geometry"]["coordinates"][1] for f in daegu])
        TraditionalMarketLoader.market_region = {f["properties"]["name"]: c for f, c in zip(daegu, codes) if c}
        print(f"  전통시장 대구 {len(daegu)}곳, 행정동 판정 {sum(c is not None for c in codes)}곳", flush=True)
        return _counts_to_indicators(self.dataset.dataset_id, "traditional_market_count", "202609", count_by_region(codes))


class NadeulStoreLoader(OpenDataLoader):
    dataset = ExternalDataset(
        dataset_id="open-nadeul-store", name="소상공인시장진흥공단_나들가게_GPS매장정보_20260908 — 대구",
        provider="소상공인시장진흥공단", source_channel="open_data",
        period_start="202609", period_end="202609",
        aggregation_note="매장 위도·경도가 행정동 경계 안에 있는 나들가게 수. 주소에 '대구'가 있는 행만",
        restriction_note="원천이 수기 수집(오차 가능 명시). 점포 규모·매출 없음. 동네 슈퍼 밀도의 참고값이며 골목상권 활력의 지표로 단정하지 않는다",
        export_approved_on=_DOWNLOADED_ON, approval_ref="공개 파일 — 반출 심사 대상 아님",
        source_url="https://www.data.go.kr/data/15122564/fileData.do", catalog_page=None,
    )

    def load(self) -> list[RegionalIndicator]:
        rows = [r for r in _read_csv("nadeul_gps.csv") if "대구" in r["매장주소"] and r["위도"] and r["경도"]]
        codes = self._index.locate_many([float(r["경도"]) for r in rows], [float(r["위도"]) for r in rows])
        print(f"  나들가게 대구 {len(rows)}곳, 행정동 판정 {sum(c is not None for c in codes)}곳", flush=True)
        return _counts_to_indicators(self.dataset.dataset_id, "nadeul_store_count", "202609", count_by_region(codes))


class BaeknyeonStoreLoader(OpenDataLoader):
    dataset = ExternalDataset(
        dataset_id="open-baeknyeon-store", name="소상공인시장진흥공단_전국 백년가게 지정리스트 현황 정보_20260820 — 대구",
        provider="소상공인시장진흥공단", source_channel="open_data",
        period_start="202608", period_end="202608",
        aggregation_note="업체주소를 브이월드 지오코더(도로명→지번)로 좌표화해 행정동 경계 안의 백년가게 수. 지오코딩 실패 업체는 제외",
        restriction_note="지정 리스트이며 현재 영업 여부·매출을 보장하지 않는다. 장수 점포 밀도의 참고값",
        export_approved_on=_DOWNLOADED_ON, approval_ref="공개 파일 — 반출 심사 대상 아님",
        source_url="https://www.data.go.kr/data/15132695/fileData.do", catalog_page=None,
    )

    def load(self) -> list[RegionalIndicator]:
        rows = [r for r in _read_csv("baeknyeon.csv") if r["업체주소"].startswith("대구")]
        points = _geocode_cached(self._vworld, _DATA_DIR / "baeknyeon_geocoded.csv", {r["연번"]: r["업체주소"] for r in rows})
        located = [points[r["연번"]] for r in rows if r["연번"] in points]
        codes = self._index.locate_many([p[0] for p in located], [p[1] for p in located])
        print(f"  백년가게 대구 {len(rows)}곳, 지오코딩 {len(located)}곳, 행정동 판정 {sum(c is not None for c in codes)}곳", flush=True)
        return _counts_to_indicators(self.dataset.dataset_id, "baeknyeon_store_count", "202608", count_by_region(codes))


class OnnuriMerchantLoader(OpenDataLoader):
    dataset = ExternalDataset(
        dataset_id="open-onnuri-merchant", name="소상공인시장진흥공단_전국 온누리상품권 가맹점 현황_20260731 — 대구",
        provider="소상공인시장진흥공단", source_channel="open_data",
        period_start="202607", period_end="202607",
        aggregation_note="소재지가 '대구'인 가맹점의 '소속 시장명'이 브이월드 전통시장명으로 시작하면 그 시장의 행정동으로 귀속해 센 가맹점 수. 시장명이 매칭되지 않는 가맹점(골목형상점가 등)은 제외",
        restriction_note="원천에 가맹점 주소가 없어(시도 단위) 시장명 매칭으로만 행정동을 정한다. 매칭 제외분이 있어 행정동별 총 가맹점 수가 아니다. 상품권 사용액·매출을 나타내지 않는다",
        export_approved_on=_DOWNLOADED_ON, approval_ref="공개 파일 — 반출 심사 대상 아님",
        source_url="https://www.data.go.kr/data/3060079/fileData.do", catalog_page=None,
    )

    def load(self) -> list[RegionalIndicator]:
        region_by_market = TraditionalMarketLoader.market_region
        if not region_by_market:
            raise RuntimeError("전통시장 로더를 먼저 실행해야 한다 (시장명→행정동 매핑)")
        rows = [r for r in _read_csv("onnuri.csv") if r["소재지"] == "대구"]
        codes = [match_market_region(r["소속 시장명(또는 상점가)"], region_by_market) for r in rows]
        matched = sum(c is not None for c in codes)
        print(f"  온누리 가맹점 대구 {len(rows)}곳, 시장명 매칭 {matched}곳({matched / len(rows):.0%}), 미매칭 제외 {len(rows) - matched}곳", flush=True)
        return _counts_to_indicators(self.dataset.dataset_id, "onnuri_merchant_count", "202607", count_by_region(codes))


class SubwayRidershipLoader(OpenDataLoader):
    dataset = ExternalDataset(
        dataset_id="open-subway-ridership", name="대구교통공사 역별 승차인원(월별 15060371·시간별 15002503) + 국가철도공단 역 주소(15041102)",
        provider="대구교통공사·국가철도공단", source_channel="open_data",
        period_start="202501", period_end="202607",
        aggregation_note="역 도로명주소를 지오코딩해 행정동에 귀속. subway_boarding_monthly = 행정동 안 역들의 월 승차인원 합(명). subway_boarding_daily_avg = 2026-01~07 일별 승차를 시간대(05-10·10-14·14-18·18-24)로 합산해 해당 월 일수로 나눈 일평균(명/일). 환승역(명덕1/2 등)은 한 역으로 합산",
        restriction_note="승차 기준(하차 미포함). 역 이용객은 행정동 생활인구·방문객 수가 아니며 상권 수요로 환산하지 않는다. 역이 없는 행정동은 행이 없다(0이 아니라 없음)",
        export_approved_on=_DOWNLOADED_ON, approval_ref="공개 파일 — 반출 심사 대상 아님",
        source_url="https://www.data.go.kr/data/15060371/fileData.do", catalog_page=None,
    )
    _HOURLY_YEAR = "2026"
    _MONTHLY_FROM = 202501

    def _station_regions(self) -> dict[str, str]:
        stations = _read_csv("stations.csv")
        points = _geocode_cached(self._vworld, _DATA_DIR / "stations_geocoded.csv", {r["역명"]: r["도로명주소"] for r in stations})
        names = [r["역명"] for r in stations if r["역명"] in points]
        codes = self._index.locate_many([points[n][0] for n in names], [points[n][1] for n in names])
        region_by_station = {normalize_station_name(n): c for n, c in zip(names, codes) if c}
        print(f"  역 {len(stations)}개, 지오코딩 {len(names)}개, 행정동 판정 {len(region_by_station)}개", flush=True)
        return region_by_station

    def load(self) -> list[RegionalIndicator]:
        region_by_station = self._station_regions()
        indicators: list[RegionalIndicator] = []
        unmatched: set[str] = set()
        # 월별 승차 — 가로 형식(역명이 컬럼)
        monthly = defaultdict(float)
        for row in _read_csv("subway_monthly.csv"):
            period = f"{row['년']}{int(row['월']):02d}"
            if int(period) < self._MONTHLY_FROM:
                continue
            for column, value in row.items():
                if column in ("년", "월") or not value:
                    continue
                code = region_by_station.get(normalize_station_name(column))
                if code is None:
                    unmatched.add(column)
                    continue
                monthly[(code, period)] += float(value)
        indicators += [
            RegionalIndicator(dataset_id=self.dataset.dataset_id, region_code=code, period=period,
                              indicator_key="subway_boarding_monthly", value=v, unit="명")
            for (code, period), v in sorted(monthly.items())
        ]
        # 시간대별 승차 — 일별 행을 월·행정동·시간대로 합산 후 일수로 나눔
        band_sum: dict[tuple[str, str, str], float] = defaultdict(float)
        days: dict[str, set[str]] = defaultdict(set)
        for row in _read_csv("subway_hourly.csv"):
            if row["승하차"] != "승차":
                continue
            code = region_by_station.get(normalize_station_name(row["역명"]))
            if code is None:
                unmatched.add(row["역명"])
                continue
            period = f"{self._HOURLY_YEAR}{int(row['월']):02d}"
            days[period].add(row["일"])
            for band, total in sum_hour_bands(row).items():
                band_sum[(code, period, band)] += total
        indicators += [
            RegionalIndicator(dataset_id=self.dataset.dataset_id, region_code=code, period=period,
                              indicator_key="subway_boarding_daily_avg", breakdown=band, value=round(v / len(days[period]), 1), unit="명/일")
            for (code, period, band), v in sorted(band_sum.items())
        ]
        if unmatched:
            print(f"  역명 미매칭(제외): {sorted(unmatched)}", flush=True)
        return indicators


_LOADERS: list[type[OpenDataLoader]] = [
    TraditionalMarketLoader, NadeulStoreLoader, BaeknyeonStoreLoader, OnnuriMerchantLoader, SubwayRidershipLoader,
]


def main() -> None:
    parser = argparse.ArgumentParser(description="공개 데이터 6종 → regional_indicator 적재")
    parser.add_argument("--only", help="쉼표 구분 dataset_id (기본 전부)")
    args = parser.parse_args()
    wanted = set(args.only.split(",")) if args.only else None

    index = _region_index()
    vworld = VworldClient()
    dataset_repo = SqlAlchemyExternalDatasetRepository()
    indicator_repo = SqlAlchemyRegionalIndicatorRepository()
    for loader_cls in _LOADERS:
        if wanted and loader_cls.dataset.dataset_id not in wanted and loader_cls is not TraditionalMarketLoader:
            continue
        print(f"[{loader_cls.dataset.dataset_id}]", flush=True)
        indicators = loader_cls(index, vworld).load()
        if wanted and loader_cls.dataset.dataset_id not in wanted:
            continue  # 온누리 매핑용 선행 실행 — 적재는 건너뜀
        dataset_repo.upsert([loader_cls.dataset])
        # 데이터셋 단위 교체 — 로더가 전체를 다시 계산하므로 이전 실행의 행이 남으면 안 된다
        with session_scope() as session:
            session.execute(delete(RegionalIndicatorOrm).where(RegionalIndicatorOrm.dataset_id == loader_cls.dataset.dataset_id))
        loaded = indicator_repo.upsert(indicators)
        keys = Counter(i.indicator_key for i in indicators)
        print(f"  적재 {loaded}행 — {dict(keys)}", flush=True)


if __name__ == "__main__":
    main()
