from dataclasses import dataclass
from datetime import date


@dataclass
class ExternalDataset:
    """외부 반출 데이터셋의 출처·집계 정의 — 지표(regional_indicator)가 매달리는 근거 단위.

    확보계획 §6 "목록·수치·출처가 함께 이동해야 한다" — 수치만 들어오고 산식·제한사항이
    떨어져 나가는 경로를 만들지 않는다. aggregation_note·restriction_note는 선택 항목이 아니다.

    export_approved_on이 None이면 **미승인**이다. 설명서에 이름이 있다는 것은 확보의 첫 단계일 뿐이며
    (확보계획 §7), 승인 전 데이터셋에는 지표를 적재할 수 없다 (indicator BC 적재 규칙).
    """

    dataset_id: str  # 결정적 슬러그 (예: "dip-samsung-card-2024") — 재반출 시에도 동일 키
    name: str
    provider: str  # 원 제공기관: 삼성카드 / SK텔레콤 / 행정안전부
    source_channel: str  # dip_center / open_api / manual
    period_start: str  # YYYYMM
    period_end: str  # YYYYMM
    aggregation_note: str  # 산식·집계 정의 (센터 승인 문구 그대로)
    restriction_note: str  # 제한사항 — 확보계획 §3의 "하지 않을 것"을 보존
    export_approved_on: date | None = None  # 반출 승인일. None = 미승인
    approval_ref: str | None = None  # 반출요청서·심사 식별자
    source_url: str | None = None
    catalog_page: str | None = None  # 데이터 설명서 쪽수 (예: "18", "54-58")
