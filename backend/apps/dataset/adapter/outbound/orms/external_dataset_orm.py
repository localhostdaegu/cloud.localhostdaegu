from datetime import date

from sqlalchemy.orm import Mapped, mapped_column

from core.matrix.grid_oracle_database_manager import OrmBase


class ExternalDatasetOrm(OrmBase):
    """외부 반출 데이터셋의 출처·기간·산식·제한사항 — 지표의 provenance 저장소 (docs/erd.md).

    **이 테이블의 존재 이유가 aggregation_note·restriction_note의 NOT NULL이다.**
    확보계획 §6은 "목록·수치·출처가 함께 이동해야 한다"고 규정한다. 산식과 제한사항을 nullable로 두면
    출처 없는 지표를 넣는 경로가 생기고, 화면에 뜬 숫자가 무엇을 센 값인지 되짚을 수 없게 된다.
    비워 둘 수 없게 만들어 구조로 강제한다.

    export_approved_on이 NULL이면 미승인 데이터셋이다. 센터 심사 전 결과를 서비스에 노출하지 않기 위한
    신호이며, regional_indicator 적재 경로가 이 컬럼을 검사한다 (설계 스펙 §3-2 적재 규칙).
    D1 삼성카드·D2 SKT는 현재 **미신청·미확보**다 — 테이블 존재를 데이터 확보로 표현하지 않는다.
    """

    __tablename__ = "external_dataset"

    dataset_id: Mapped[str] = mapped_column(primary_key=True)  # 예: dip-samsung-card-2024
    name: Mapped[str]
    provider: Mapped[str]  # 원 제공기관: 삼성카드 / SK텔레콤 / 행정안전부
    source_channel: Mapped[str]  # dip_center / open_api / manual
    period_start: Mapped[str]  # YYYYMM
    period_end: Mapped[str]  # YYYYMM
    aggregation_note: Mapped[str]  # NOT NULL — 산식·집계 정의 (센터 승인 문구 그대로)
    restriction_note: Mapped[str]  # NOT NULL — 확보계획 §3의 "하지 않을 것"
    export_approved_on: Mapped[date | None]  # 반출 승인일. NULL = 미승인 (적재 금지 신호)
    approval_ref: Mapped[str | None]  # 반출요청서·심사 식별자
    source_url: Mapped[str | None]
    catalog_page: Mapped[str | None]  # 데이터 설명서 쪽수 (예: "18", "54-58")
