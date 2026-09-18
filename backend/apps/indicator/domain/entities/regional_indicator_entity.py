from dataclasses import dataclass


@dataclass
class RegionalIndicator:
    """반출 승인된 지역 지표 한 칸 — long format (dataset_id, 지역, 업종, 기간, 지표명, 슬라이스) → 값.

    확보계획 §3은 D1·D2의 반출 형태를 "센터가 승인하는 동등한 형식"으로만 규정한다.
    승인 결과가 컬럼 단위로 확정되지 않았으므로 지표별 전용 컬럼 대신 long format으로 받는다.

    기존 region_industry_metric(인허가 집계)과 **다른 테이블**이다. 확보계획 §6은 카드 소비 변화율을
    인허가 growth_rate에 덮어쓰는 것을 금지한다 — 출처가 다른 수치를 한 칸에 겹쳐 쓰지 않는다.
    """

    dataset_id: str  # external_dataset — 이 값의 산식·제한사항·승인 상태가 붙어 있는 곳
    region_code: str  # 행정동 10자리 (구·군 5자리를 넣지 않는다)
    period: str  # YYYYMM / YYYYQn / YYYY — 단위는 dataset이 규정
    indicator_key: str  # 측정값 이름: card_amt_index / living_pop_worker 등
    value: float
    unit: str  # 원 / 건 / % / 명 / 지수
    industry_id: str | None = None  # None = 업종 무관 지표 (생활인구 등)
    breakdown: str | None = None  # None = 슬라이스 없음 (weekend / time_09_13 / male_20s …)
