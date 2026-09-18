from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

# FK 대상 테이블이 메타데이터에 항상 존재하도록 보장
import apps.dataset.adapter.outbound.orms.external_dataset_orm  # noqa: F401
import apps.master.adapter.outbound.orms.industry_orm  # noqa: F401
import apps.master.adapter.outbound.orms.region_orm  # noqa: F401
from core.matrix.grid_oracle_database_manager import OrmBase


class RegionalIndicatorOrm(OrmBase):
    """반출 승인된 지역 지표 — long format (docs/erd.md, population_stat 전례).

    **long format을 택한 근거:** 확보계획 §3은 D1·D2 반출 형태를 "센터가 승인하는 동등한 형식"으로만
    규정하며 승인 결과가 컬럼 단위로 확정되지 않았다. 지표별 전용 테이블을 지금 만들면 승인 형태가
    다를 때 마이그레이션을 다시 짜야 한다. long format은 D3~D5·후속 반출까지 마이그레이션 없이 받는다.

    **region_industry_metric과 분리하는 근거:** 확보계획 §6이 카드 소비 변화율을 인허가 growth_rate에
    덮어쓰는 것을 금지한다. 테이블을 나누면 구조적으로 보장된다.

    **적재 규칙:** dataset_id가 가리키는 external_dataset.export_approved_on이 NULL이면 적재할 수 없다.
    리포지토리 upsert가 검사한다 (설계 스펙 §3-2).
    """

    __tablename__ = "regional_indicator"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "region_code",
            "industry_id",
            "period",
            "indicator_key",
            "breakdown",
            # PG15+ — 업종 무관(industry_id NULL)·슬라이스 없음(breakdown NULL) 행도 중복을 차단한다.
            # 기본 동작(NULLS DISTINCT)이면 같은 지표가 조용히 여러 번 쌓여 값이 갈린다.
            postgresql_nulls_not_distinct=True,
        ),
        # 지표×기간 단면 조회 (예: 전 행정동의 202412 card_amt_index)
        Index("ix_regional_indicator_key_period", "indicator_key", "period"),
        # 선택한 동·업종의 지표 묶음 조회
        Index("ix_regional_indicator_region_industry", "region_code", "industry_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("external_dataset.dataset_id"))
    region_code: Mapped[str] = mapped_column(ForeignKey("region.region_code"))
    industry_id: Mapped[str | None] = mapped_column(
        ForeignKey("industry.industry_id")
    )  # NULL = 업종 무관 지표 (생활인구 등)
    period: Mapped[str]  # YYYYMM / YYYYQn / YYYY — dataset이 단위를 규정
    indicator_key: Mapped[str]  # card_amt_index / living_pop_worker 등
    breakdown: Mapped[str | None]  # weekend / time_09_13 / male_20s … (NULL = 슬라이스 없음)
    value: Mapped[float]
    unit: Mapped[str]  # 원 / 건 / % / 명 / 지수
