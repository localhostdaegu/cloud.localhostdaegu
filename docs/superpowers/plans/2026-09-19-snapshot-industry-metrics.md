# 2026-09-19 — 편의점·어린이집 상권 지표 연결 (스냅샷 업종 지표 원천 Strategy)

## 배경

`region_industry_metric`은 `store` 테이블만 집계한다. 편의점(`convenience_store` 2,019, 소진공 스냅샷 — 개폐업 이력 없음)과
어린이집(`childcare_center` 986 + `childcare_center_stat` 986)은 별도 테이블이라 지표가 없고 화면에 "데이터 없음"으로 나온다.
오늘 담배소매업 인허가 이력 `tobacco_retailer` 33,804건(정상영업 6,221·폐업처리 23,819·지정취소 1,643·직권취소 1,934, 좌표 29,383, 행정동 29,383 기입,
지정일 1901~2026·폐업일 1968~2026)이 적재됐다. 담배소매인 지정은 편의점 개폐업의 대용 지표로 설계돼 있었다(docs/DAEGU_DATA_API_GUIDE.md).
어린이집은 인가일(`approved_on`, 1971~2026, 986/986)이 있고 폐지일(`abolished_on`)은 0건이다.

## Global Constraints

- 커밋 금지(파일만 수정). 작업 디렉토리 `/home/kimchungsik/projects/cloud.localhostdaegu`, worktree 없음.
- 백엔드 실행 `cd backend && PYTHONPATH=. .venv/bin/python -m ...`, 테스트 `cd backend && PYTHONPATH=. .venv/bin/pytest -q`(기준선 **577 passed / 1 skipped**; 학원 인터랙터 변경으로 9건 갱신됨 — 그대로 통과해야 함).
- 개발 DB: `docker exec localhostdaegu-db psql -U localhostdaegu -d localhostdaegu -Atc "..."`.
- 헥사고날·GoF 규약(`backend/CLAUDE.md`): 업종/원천별 분기는 `if/elif`가 아니라 **Strategy(원천별 클래스 + 레지스트리)**. cross-BC 접근은 어댑터 레이어에서만(metric 어댑터가 tobacco·childcare ORM을 import하는 것은 허용, `app/`·`domain/`은 금지).
- 숫자는 실측만. 답변·보고서·주석 한국어. API 키 노출 금지.
- 정직성: 편의점 지표는 **담배소매인 인허가 대용**임을 화면 라벨·문서에 드러낸다. 어린이집 폐업은 원천이 폐지분을 주지 않으므로 스냅샷 소실(last_seen 정지) 기반 추정임을 드러낸다.

### Task 1: 지표 원천 Strategy — 담배소매인→편의점, 어린이집 원천 → `region_industry_metric`

1. `backend/apps/metric/adapter/outbound/gateways/store_stats_gateway.py`의 `StoreStatsGateway`를 **원천 Strategy 합성**으로 바꾼다.
   - 포트 `StoreStatsPort`(`yearly_stats(years)`, `latest_record_date()`)는 그대로. 게이트웨이 내부에 `YearlyStatsSource`(ABC: `yearly_stats(session, years) -> list[YearlyStoreStat]`, `latest_record_date(session) -> date | None`)를 두고
     구현 3개를 레지스트리 리스트로 합성: `StoreTableSource`(기존 쿼리 그대로, 업종 = store.industry_id), `TobaccoProxySource`(industry_id **`convenience_store`**), `ChildcareSource`(industry_id **`childcare`**). 파일은 `gateways/stats_sources/` 하위로 나눠도 되고 한 파일이어도 된다(각 클래스 40줄 내외).
   - `TobaccoProxySource`: `tobacco_retailer`에서 `open = coalesce(designated_date, permit_date)`, `close = coalesce(close_date, cancel_date)`, `region_code IS NOT NULL`. 연도 말 영업 중·당해 개업·당해 폐업 계산과 **30일 이내 종료 제외 규칙(`SHORT_LIVED_MAX_DAYS`)을 store와 동일하게** 적용. `status_code`는 쓰지 않는다(폐업일이 진실).
   - `ChildcareSource`: `childcare_center`에서 `open = approved_on`, `close = coalesce(abolished_on, 소실일)`. 소실일 = 시설의 `last_seen_on`이 **그 구·군의 최신 관측일(max last_seen_on by district_code)보다 앞서면** `last_seen_on`(추정 폐원), 아니면 NULL. 오늘은 관측일이 하루뿐이라 소실 0건 — 규칙만 들어간다. 30일 규칙 동일 적용.
   - `latest_record_date` = 세 원천 최대값(NULL 무시).
2. `industry_source_code` 시드(`backend/apps/master/adapter/inbound/cli/seed_master.py`)에 `("convenience_store", "mois_permit_tobacco", "기타_담배소매업")` 추가(멱등 시드 재실행: `python -m apps.master.adapter.inbound.cli.seed_master`). 어린이집 행은 이미 있다.
3. 화면 라벨 정직성: `backend/apps/master/app/use_cases/region_interactor.py` `summary()`의 "점포수" 카드 라벨을 업종별 오버라이드 dict(Strategy 테이블)로 — `convenience_store` → `"점포수(담배소매인 기준)"`, `childcare` → `"어린이집 수"`. 나머지 업종은 그대로. 프론트 `frontend/src/shared/industries.ts`의 `INDUSTRY_LABELS.convenience_store`는 `"편의점 (담배소매인 기준)"`으로. (LLM 리포트가 쓰는 `industry.name`은 바꾸지 않는다 — 대신 `apps/analysis/domain/report_text.py`의 지표 해석 프롬프트에 "편의점 지표는 담배소매인 지정 현황을 대용으로 쓴 값"임을 업종이 convenience_store일 때만 한 문장 덧붙인다; if 분기 대신 업종→주석 dict.)
4. 테스트: 원천 Strategy 각각 **실 테스트 DB**로 (기존 `tests/test_metric_*`·`test_region_industry_metric*` 스타일 확인 후 같은 방식) — 담배 프록시 개업/폐업/연말 영업 중 카운트 1건씩, 어린이집 소실 추정(구 최신 관측일보다 앞선 last_seen_on → close), 30일 규칙 적용, 합성 게이트웨이가 세 원천을 합친다, latest_record_date 최대값. 라벨 오버라이드 단위 테스트 1건. 프론트 라벨 변경은 기존 vitest가 깨지면 그 테스트만 갱신(`cd frontend && npx vitest run src/shared`).
5. 실행: `seed_master` → `build_metrics` → 검증 쿼리: `select industry_id, count(*), count(distinct region_code) from region_industry_metric group by 1` (convenience_store·childcare 행이 생겨야 함), 2025년 편의점 개업/폐업 합, 어린이집 2025 store_count 합. 실서버(8300, 이미 떠 있음)에서 `curl 'http://localhost:8300/metrics/risk?industry=convenience_store&year=2025'`·`childcare` 응답 건수 확인(서버는 옛 코드일 수 있음 — 그 경우 "재기동 필요"라고만 보고, 재기동하지 않는다).
6. 전체 pytest 통과. 보고서에 실측 표(업종별 metric 행·행정동 수, 2025 개업/폐업, 담배 대용의 한계: 담배소매인 ≠ 편의점 — 슈퍼·마트 포함)를 적는다.

### Task 2: 어린이집 정원·현원 카드 — 리포트·지도 패널 컨텍스트

1. master BC에 출력 포트 `ChildcareCapacityPort`(`region_summary(region_code) -> ChildcareCapacityDto | None`: 운영 중 시설 수, 정원 합, 현원 합, 가동률, 입소대기 합(전부 공란이면 None), 기준일)를 `apps/master/app/ports/output/`에 추가하고, 어댑터 `apps/master/adapter/outbound/gateways/childcare_capacity_gateway.py`가 `childcare_center` × `childcare_center_stat`(시설별 최신 base_date, 구·군 최신 관측일에 관측된 시설, region_code 일치)로 계산. Metabole 전례 `ChildcareRegionSummary.of()`(cloud.beyondfacade `apps/childcare/domain/entities/childcare_center_stat_entity.py`)의 합산 규칙을 따른다.
2. `region_interactor.summary()`가 `industry_id == "childcare"`일 때 카드 2개를 뒤에 덧붙인다: `"정원 대비 현원"` = `"{현원}/{정원} ({가동률}%)"`, `"입소대기"` = `"{n}명"` 또는 `"미공개"`. 업종 분기는 위 3항의 업종→추가카드 Strategy 테이블에 넣는다(childcare만 항목이 있음). 의존성 주입은 `apps/master/dependencies/`의 composition root.
3. 이 카드는 `MarketDataGateway`(analysis)가 그대로 `MetricCard`로 넘기므로 리포트 LLM 지표 해석에 자동으로 들어간다 — 별도 수정 없음을 확인만.
4. 테스트: 가동률 합산 규칙(정원 0 → None, 대기 전부 공란 → None) 순수 함수 테스트 + 실 DB 게이트웨이 테스트 1건 + summary 카드 추가 테스트 1건.
5. 실측: 개발 DB에서 어린이집이 많은 행정동 1곳(예: 2771025600 다사읍 62곳)의 카드 값을 보고서에.

### Task 3: 문서

- `docs/handoff.md` 운영 절차에 "편의점 지표 = 담배소매인 대용(`tobacco_retailer`, 파일 재확보 시 `load_tobacco_retailer` 재실행 → `build_metrics`)", "어린이집 폐원 = 스냅샷 소실 추정" 2줄.
- `docs/jekyll.md` 2026-09-19 항목에 소제목 하나로 Task 1·2 실측(행 수·2025 개업/폐업·카드 예시·한계) 기록(최신 우선 — 섹션 맨 위).
- `docs/plan/plan.md`(git-ignored)의 "편의점·어린이집은 상권 지표 미연결" 서술(§1-4 107행, §2 표, SWOT W③, §5-5·5-6 잔여 한계 등 `grep -n "미연결\|데이터 없음\|편의점 2,019"`로 전수)을 "연결(편의점은 담배소매인 대용, 어린이집은 인가일 기준·폐원 추정)"로 정정. 숫자는 Task 1 보고서 실측. 19행 과제요약은 500자 이내 유지(현재 491자).
