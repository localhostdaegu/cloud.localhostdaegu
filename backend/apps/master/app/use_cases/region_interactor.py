from collections.abc import Callable

from apps.master.app.dtos.childcare_capacity_dto import ChildcareCapacityDto
from apps.master.app.dtos.region_dto import (
    RegionDto,
    RegionSummaryDto,
    SummaryCardDto,
)
from apps.master.app.ports.input.region_use_case import RegionUseCase
from apps.master.app.ports.output.childcare_capacity_port import ChildcareCapacityPort
from apps.master.app.ports.output.region_port import (
    RegionBoundaryReaderPort,
    RegionMetricSummaryPort,
    RegionRepositoryPort,
)
from apps.master.domain.errors import RegionNotFoundError

_COORD_PRECISION = 5  # 소수 5자리 ≈ 1.1m — 지도 표시용 (원본 파일은 원 정밀도 유지)
_NO_DATA = "데이터 없음"
# (개업 − 폐업) ÷ 전년 말 점포 수 — 매출 성장으로 읽히지 않게 "성장률"이라 부르지 않는다(이어받기 §0-2)
_GROWTH_LABEL = "점포 증감률"
_STORE_COUNT_LABEL = "점포수"

# Strategy (GoF) — 업종별 첫 카드 라벨. if/elif 업종 분기 대신 테이블 디스패치.
# 원천이 업종과 다른 업종은 라벨에 그 사실을 드러낸다 — 화면이 원천을 감추지 않게 한다.
_STORE_COUNT_LABELS = {
    "convenience_store": "점포수(담배소매인 기준)",  # 편의점 전용 인허가가 없어 담배소매인 지정을 대용으로 쓴다
    "childcare": "어린이집 수",
}
_CLOSURE_LABEL = "폐업률"
# 원천이 폐업분을 주지 않는 스냅샷 업종 — 폐업은 스냅샷 소실로만 추정하므로 라벨에 드러낸다
_CLOSURE_LABELS = {
    "academy": "폐업률(추정)",
    "real_estate": "폐업률(추정)",
    "childcare": "폐업률(추정)",
}


def _round_coords(node: float | list) -> float | list:
    if isinstance(node, list):
        return [_round_coords(child) for child in node]
    return round(node, _COORD_PRECISION)


def _percent(rate: float | None) -> str:
    return _NO_DATA if rate is None else f"{rate * 100:.1f}%"


def _signed_percent(rate: float | None) -> str:
    if rate is None:
        return _NO_DATA
    return f"{'+' if rate >= 0 else ''}{rate * 100:.1f}%"  # 음수 부호는 포맷이 붙인다


class _NoChildcareCapacity(ChildcareCapacityPort):
    """Null Object — 정원 포트 없이 구성한 경로(geojson 전용)에서 None 검사를 없앤다."""

    def region_summary(self, region_code: str) -> ChildcareCapacityDto | None:
        return None


def _childcare_cards(
    capacity: ChildcareCapacityPort, region_code: str
) -> list[SummaryCardDto]:
    """인구구조형 업종 전용 — 수요(현원)와 공급(정원)을 점포수 대신 직접 보여준다."""
    summary = capacity.region_summary(region_code)
    if summary is None:
        return []
    waiting = "미공개" if summary.waiting_count is None else f"{summary.waiting_count}명"
    return [
        SummaryCardDto(
            label="정원 대비 현원",
            value=f"{summary.child_count}/{summary.capacity} ({_percent(summary.occupancy_rate)})",
            grade="fact",
        ),
        SummaryCardDto(label="입소대기", value=waiting, grade="fact"),
    ]


def _no_extra_cards(capacity: ChildcareCapacityPort, region_code: str) -> list[SummaryCardDto]:
    return []


# Strategy (GoF) — 업종별 추가 카드. if industry == ... 분기 대신 테이블 디스패치
_EXTRA_CARDS: dict[str, Callable[[ChildcareCapacityPort, str], list[SummaryCardDto]]] = {
    "childcare": _childcare_cards,
}


class RegionInteractor(RegionUseCase):
    def __init__(
        self,
        repository: RegionRepositoryPort,
        boundary_reader: RegionBoundaryReaderPort,
        # geojson 전용 구성(기존 테스트)이 지표 포트 없이 구성하도록 기본 None
        metric_summary: RegionMetricSummaryPort | None = None,
        childcare_capacity: ChildcareCapacityPort | None = None,
    ) -> None:
        self._repository = repository
        self._boundary_reader = boundary_reader
        self._metric_summary = metric_summary
        self._childcare_capacity = childcare_capacity or _NoChildcareCapacity()

    def myself(self) -> RegionDto:
        return RegionDto(region_code="myself", name="region BC 배선 검증")

    def geojson(self) -> dict:
        features = []
        for region in self._repository.list_regions():
            if region.geometry_ref is None:
                continue
            source = self._boundary_reader.read_feature(region.geometry_ref)
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": source["geometry"]["type"],
                        "coordinates": _round_coords(source["geometry"]["coordinates"]),
                    },
                    # name은 파일 properties(adm_nm/emd_kor_nm 혼재)가 아니라 DB에서
                    "properties": {"region_code": region.region_code, "name": region.name},
                }
            )
        return {"type": "FeatureCollection", "features": features}

    def summary(
        self, region_code: str, industry_id: str, year: int | None = None
    ) -> RegionSummaryDto:
        region = self._repository.find(region_code)
        if region is None:
            raise RegionNotFoundError(region_code)
        snapshot = self._metric_summary.fetch(region_code, industry_id, year)
        count_label = _STORE_COUNT_LABELS.get(industry_id, _STORE_COUNT_LABEL)
        closure_label = _CLOSURE_LABELS.get(industry_id, _CLOSURE_LABEL)
        if snapshot is None:
            cards = [
                SummaryCardDto(label=label, value=_NO_DATA, grade="fact")
                for label in (count_label, closure_label, _GROWTH_LABEL)
            ]
        else:
            cards = [
                SummaryCardDto(label=count_label, value=f"{snapshot.store_count}개", grade="fact"),
                SummaryCardDto(label=closure_label, value=_percent(snapshot.closure_rate), grade="fact"),
                SummaryCardDto(label=_GROWTH_LABEL, value=_signed_percent(snapshot.growth_rate), grade="fact"),
            ]
        cards += _EXTRA_CARDS.get(industry_id, _no_extra_cards)(
            self._childcare_capacity, region_code
        )
        return RegionSummaryDto(
            region_code=region.region_code,
            name=region.name,
            industry_id=industry_id,
            cards=cards,
        )
