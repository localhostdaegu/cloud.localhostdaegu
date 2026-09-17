"""지역×업종 연도별 지표 배치 러너 (Driving Adapter, CLI).

- 입력: store 테이블의 region_code 보유분만 읽는다 — 외부 API 호출 없음
- 산출: region_industry_metric (행정동×업종×연도 2019~원천 최신 기록 연도, 부분 연도 포함) 업서트 — 재실행 멱등
  (조회 기본 연도는 마지막 완결 연도 — apps/metric/domain/reporting_year.py)
- 일일 증분 크론(store-collector)의 assign_regions 후속 실행을 전제로 설계

실행: python -m apps.metric.adapter.inbound.cli.build_metrics
"""

from apps.metric.dependencies.region_industry_metric_dependencies import (
    get_region_industry_metric_use_case,
)

_FIRST_YEAR = 2019


def main() -> None:
    use_case = get_region_industry_metric_use_case()
    years = use_case.data_years(_FIRST_YEAR)
    if not years:
        print("store 원천 비어 있음 — 지표 업서트 생략")
        return
    processed = use_case.build(years)
    print(f"지표 업서트: {processed}건 (연도 {years[0]}~{years[-1]})")


if __name__ == "__main__":
    main()
