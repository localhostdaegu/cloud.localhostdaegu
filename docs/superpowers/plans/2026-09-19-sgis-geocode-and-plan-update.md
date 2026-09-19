# 2026-09-19 — SGIS 지오코딩으로 학원·부동산 지표 연결 + 제안서(docs/plan) 갱신

## 배경

오늘 편의점 2,019·부동산중개업 4,629·어린이집 986·학원 8,002(교습과정 21,646)건을 처음 적재했다.
학원·부동산 `store` 행은 원천에 좌표가 없어 `lat/lng`·`region_code`가 NULL → `build_metrics`(region_code 보유분만 집계)에 잡히지 않아
상권 지표는 여전히 인허가 7업종뿐이다. 어린이집 15건은 원천 좌표 오류(서울시청 자리표시자 9·경산/영천 4·구 밖 2)로 region 미기입.
제안서 `docs/plan/plan.md`와 부록(차트·라이선스·drawio)은 "4종 등록만, 수집 전" 상태를 서술한다.

## Global Constraints

- **커밋 금지.** 서브에이전트는 파일만 수정하고 커밋하지 않는다(사용자가 커밋 시점을 정한다). `docs/plan/`은 git-ignored.
- 작업 디렉토리: `/home/kimchungsik/projects/cloud.localhostdaegu` (worktree 없이 현재 트리에서 — 미커밋 변경이 많아 worktree는 오늘 작업을 담지 못한다).
- 백엔드 실행: `cd backend && PYTHONPATH=. .venv/bin/python -m ...`, 테스트 `cd backend && PYTHONPATH=. .venv/bin/pytest -q` (테스트 DB `localhostdaegu_test` 자동 사용).
- 개발 DB 확인: `docker exec localhostdaegu-db psql -U localhostdaegu -d localhostdaegu -Atc "..."`.
- 외부 API 키는 `backend/.env`에 있다. **키 값을 로그·보고서·코드·문서에 절대 쓰지 않는다.** 게이트웨이 예외는 `core.matrix.grid_http_error_translator.translate_http_errors()`로 감싼다.
- 헥사고날 규약(`backend/CLAUDE.md`): 게이트웨이는 `adapter/outbound/gateways`, CLI는 `adapter/inbound/cli`, 포트는 `app/ports/output`. 단일 사용 추상화는 만들지 않는다.
- 숫자는 실측만 쓴다. 추정치·기대치를 실측처럼 적지 않는다.
- 답변·보고서·문서는 한국어.

### Task 1: SGIS 지오코딩 — store.address 컬럼, 지오코딩 CLI, 학원·부동산 지표 연결, 어린이집 좌표 보정

**실측된 SGIS 사양 (2026-09-19, 컨트롤러가 직접 호출해 확인)**

- 기존 도메인 `sgisapi.kostat.go.kr`은 302로 `https://sgisapi.mods.go.kr`로 이전됐다. **새 도메인을 쓴다.**
- 인증: `GET https://sgisapi.mods.go.kr/OpenAPI3/auth/authentication.json?consumer_key=<SGIS_SERVICE_ID>&consumer_secret=<SGIS_SECURITY_KEY>`
  → `{"errCd":0,"errMsg":"Success","result":{"accessToken":"...","accessTimeout":"<epoch ms>"}}` (토큰 4시간).
- 지오코딩: `GET https://sgisapi.mods.go.kr/OpenAPI3/addr/geocode.json?accessToken=&address=<주소>&pagenum=0&resultcount=1`
  → `result.resultdata[0]` 의 `x`,`y`는 **EPSG:5179(UTM-K)** 문자열. `pyproj.Transformer.from_crs("EPSG:5179","EPSG:4326",always_xy=True)`로 (lng, lat) 변환.
  검증 예: "대구광역시 달서구 와룡로 70" → x 1093700.96, y 1760716.28 → (128.4965, 35.8024). `sido_nm`/`sgg_nm`도 온다(구 교차검증에 사용 가능).
  실패·무결과는 `errCd != 0` 또는 `resultdata` 빈 배열. 권고 한도 일 5만 회 — 대상 약 12,650건.
- 설정: `core/matrix/grid_keymaker_secret_manager.py` Settings에 `sgis_service_id: str = ""`, `sgis_security_key: str = ""` 추가 (`.env` 변수명 `SGIS_SERVICE_ID`, `SGIS_SECURITY_KEY` 이미 존재).

**구현 항목**

1. `store` 테이블에 `address` 컬럼(nullable String) 추가 — Alembic 마이그레이션(down_revision `d2e3f4a5b6c7`), `StoreOrm`, `Store` 엔티티(`address: str | None = None` 기본값 — 기존 생성부 무수정), `store_orm_mapper` 양방향.
2. 게이트웨이가 주소를 채운다: `molit_broker_gateway._to_store` → `address=item.get("rdnmadr")`(도로명, 공란이면 None). `neis_academy_gateway._to_record` → `address=FA_RDNMA`. 각 게이트웨이 테스트에 address 단언 1개씩 추가.
3. SGIS 지오코딩 게이트웨이 `apps/store/adapter/outbound/gateways/sgis_geocode_gateway.py`: 토큰 발급(만료 전 재사용)·주소→(lng,lat)|None. 주소 정규화는 `apps/indicator/adapter/inbound/cli/load_open_data.normalize_address` 재사용(괄호 제거·지하 제거). `call_count` 보고. 픽스처 기반 단위 테스트(실호출 없음): 정상 변환, 무결과 None, errCd≠0 예외.
4. 지오코딩 CLI `apps/store/adapter/inbound/cli/geocode_stores.py`:
   - 대상: `store.lat IS NULL AND address IS NOT NULL` (옵션 `--industry academy|real_estate`, `--limit N`).
   - **캐시 필수**: `data/cache/sgis_geocode.csv`(git-ignored, 컬럼 `address,lng,lat`; 실패는 빈 값으로 기록해 재호출 방지) — 재수집 시 `store` 업서트가 `session.merge`로 lat/lng를 None으로 되돌리므로, 이 CLI를 재실행하면 캐시만으로(API 0회) 좌표가 복원돼야 한다.
   - 결과: `store.lat/lng` UPDATE(청크 1,000). 대구 범위 밖 좌표(`core.matrix.grid_region_config.LAT_RANGE/LNG_RANGE`)는 기입하지 않고 건수 보고.
   - 출력: 대상/성공/실패/범위밖/API 호출 수.
5. 실행 순서(개발 DB): `broker_collector`(9회)·`academy_collector`(9회) 재실행으로 address 채움 → `geocode_stores` → `assign_regions`(신규분) → `build_metrics`.
   기대: `region_industry_metric`에 `academy`·`real_estate` 행이 생긴다. 실측 건수(지오코딩 성공/실패, region 기입, metric 행 수 by industry)를 보고서에 표로.
6. 어린이집 좌표 오류 15건: `childcare_center` 중 `region_code IS NULL` 행을 address로 SGIS 지오코딩해 `lat/lng`를 덮어쓰고, 이어서 `apps.childcare.adapter.inbound.cli.childcare_collector.assign_regions()`를 호출해 region 기입. 구현은 `geocode_stores.py`에 `--childcare` 옵션으로 넣거나 childcare CLI에 서브커맨드로 — 판단해서 한 곳에. 원천 재수집 시 좌표가 다시 오류값으로 덮이는 문제는 **캐시 우선 재적용**으로 같은 방식 해결(보고서에 명시).
7. 크론 `scripts/store-collector.sh`는 수정하지 않는다(학원·부동산은 수동 스냅샷). 단 `docs/handoff.md`에 "학원·부동산 재수집 후 geocode_stores → assign_regions → build_metrics 순" 운영 절차 3줄 추가.
8. 프론트 확인(선택, 코드 수정 금지): 백엔드가 8300에 떠 있으면 `curl -s 'http://localhost:8300/api/v1/...'`로 academy 지표가 나오는지 1건 확인해 보고. 엔드포인트는 `frontend/src` 또는 `backend/apps/metric/adapter/inbound/api`에서 찾는다. 안 떠 있으면 건너뛰고 보고.
9. 전체 테스트 통과(`pytest -q`, 현재 512 passed / 1 skipped 기준선).

**보고서에 반드시**: 실행한 명령과 출력 요약, 최종 건수 표(업종별 store 좌표 보유/region 보유, metric 행 수), 실패 주소 유형 상위 5개, 소요 시간, SGIS 호출 총수.

### Task 2: 제안서 `docs/plan` 갱신 — 신규 적재·지표 연결 반영, 과거 서술 정정

Task 1의 보고서(`.superpowers/sdd/2026-09-19-sgis-geocode-and-plan-update/task-1-report.md`)의 실측 숫자를 단일 원천으로 쓴다. 숫자를 추정하지 않는다. 개발 DB를 직접 조회해도 된다.

**수정 대상과 규칙**

1. `docs/plan/plan.md` — 다음 서술을 실제 상태로 바꾼다. "수집 전"·"등록만"·"미수집"·"지표 7종(등록 11종)" 류 표현 전부. 현재 알려진 위치: 47행(주 대상 7개 업종), 58행(인허가 7업종 집계 — 이 수치는 7업종 기준 그대로 유지하되 '7업종 기준'임을 명시), 85행(① 지도 상권 진단 근거), 96~99행(업종 유형 표의 상태 열), 107행("지금 프로토타입에서 동작하는 것과 아닌 것" 문단 — 지표 산출 업종 수를 실측으로), 156행(데이터셋 행 — 편의점·부동산·학원·어린이집 건수 추가), 184·186행(경쟁 비교표 데이터 규모·업종), 241행(SWOT W③), 267행(연간 대상자 상한 — 7업종 기준 유지, 표기만), 358행(5-5 지표 행), 371행(5-6 구현하지 않은 것 — 해당 항목 삭제 또는 잔여 한계로 재서술), 403행(5-9 data-inventory 설명 — 묶음 수·합계 갱신). `grep -n` 으로 다시 전수 확인할 것.
   - 지표가 실제로 붙은 업종만 "지표 있음"으로 쓴다. 편의점(`convenience_store` 별도 테이블)·어린이집(`childcare_center`)은 `region_industry_metric`에 없으므로 "수집 완료(건수), 상권 지표 미연결(후속)"로 정확히 구분한다. 학원·부동산은 Task 1 결과에 따라 "지표 연결"로.
   - 어린이집은 정원·현원(가동률) 직접 관측 데이터가 이제 실재함을 §1-4 문단에 한 문장으로 반영(986곳, 기준일).
   - 학원 원천은 NEIS 교육정보 개방포털(대구교육청), 부동산은 브이월드 NED(국토부 중개업 15123990), 편의점은 소진공 상가정보, 어린이집은 어린이집정보공개포털. 서울 관련 잔재 표현이 있으면 제거.
   - 수집 일자 2026-09-19. 뉴스·공고 등 크론 증감 수치는 손대지 않는다(요청 범위 밖). 단 차트 설명(403행)과 차트 본문은 일치시킨다.
2. `docs/plan/data-inventory.png/.svg` 재생성: 스크립트 `/tmp/claude-1000/-home-kimchungsik-projects-cloud-localhostdaegu/bcd369f3-2f22-484c-97dc-100503e8071c/scratchpad/make_charts.py`(그림 2 부분만 실행하도록 복사·수정, 그림 1은 재생성하지 않는다)와 같은 폴더의 venv `vizenv/bin/python`(matplotlib·Noto Sans CJK 확인)을 쓴다. 없으면 `python3 -m venv` 새로 만들고 matplotlib 설치. 디자인(색·눈금·주석 박스 형태)은 유지하고 데이터 행만 갱신: 인허가 7업종 161,141 → "점포 이력 · 인허가 7업종 + 학원·부동산" 합계와 분리 표기 중 택1(라벨에 구성 명시), 학원 교습과정 21,646, 편의점 2,019, 어린이집 986(+현황 986), 나머지는 개발 DB 현재값. 합계 주석 갱신. 스크립트 사본은 `docs/plan/make_charts.py`로 저장해 다음 갱신이 재현되게 한다.
3. `docs/plan/licenses.md` DATA 표: 소진공 상가정보(data.go.kr API, 공공데이터 이용약관), 브이월드 NED 중개업정보(15123990), NEIS 교육정보 개방포털 학원교습소정보(이용약관 페이지 확인 — 확인 못 하면 "미확인"으로 적는다), 어린이집정보공개포털 API(개발계정 승인제), SGIS 지오코딩(통계청 SGIS 오픈API 약관 — 결과 저장 조건을 확인해 적는다; 확인 못 하면 "미확인·확인 필요"로) 행 추가. 인허가 행은 그대로.
4. `docs/plan/tech-flow.drawio`: "원천(인허가 161,141 · 인구 48,174) · 지표(...)" 문구와 "행안부 인허가 7업종" 문구를 실제 원천 목록으로 갱신(XML 텍스트 치환, `&amp;` 등 이스케이프 유지). 편집 후 `python3 -c "import xml.etree.ElementTree as ET; ET.parse('docs/plan/tech-flow.drawio')"` 로 파싱 확인. `user-flow.drawio`의 "(인허가 161,141건 집계, 연도 선택)"은 지도 화면이 실제로 읽는 지표 범위에 맞춰 판단(학원·부동산 지표가 붙었으면 "점포 이력 N건" 으로).
5. `docs/jekyll.md` 2026-09-19 항목 맨 아래에 새 소제목 하나로 오늘 후반 작업(SGIS 지오코딩·지표 연결·제안서 갱신)을 실측 수치와 미결 항목 포함해 추가(하루 단위·최신 우선 규약). `docs/handoff.md`는 Task 1이 손댔으면 중복 추가하지 않는다.
6. 마지막에 `grep -n "수집 전\|등록만\|미수집\|서울" docs/plan/plan.md docs/plan/licenses.md` 결과가 의도한 잔여 문구뿐임을 보고서에 붙인다.

**보고서에 반드시**: 바꾼 행 목록(파일:행 → 요지), 차트 재생성 명령과 합계, 확인하지 못한 라이선스 항목.
