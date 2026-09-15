# localhostdaegu 백엔드 이식·구축 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Metabole(서울) 백엔드를 이 저장소로 이식하고 대구 어댑터로 전환해, 대구 8개 구·군의 인허가·상권 데이터가 적재되고 위험도·재무·금융매칭 API가 동작하는 백엔드를 만든다.

**Architecture:** 기존 Metabole 헥사고널 구조(core/matrix 인프라 매니저 + apps/ BC 12개)를 통째로 복사한 뒤, 서울 결합 지점(시드 데이터·bbox 상수·필터 3곳)만 대구로 교체한다. 신규 기능(Finance Engine·위험도·매칭·의도추출)은 순수 결정론 모듈로 추가하고 LLM은 수치를 만들지 않는다.

**Tech Stack:** Python 3.12+(원본 3.14) · FastAPI · SQLAlchemy 2.0(sync) · psycopg3 · Alembic · pgvector · httpx · pyproj/shapely · pytest

**Spec:** `docs/daegunavi.md` (기획서) + `docs/apilist.md` (API 소스·코드 목록) + Metabole 구조 조사 보고서(이 계획의 파일:라인 근거)

## Global Constraints

- 신규 발급 API 키 0개 — `backend/.env`의 기존 키만 사용 (값은 사용자가 채움)
- 백엔드 포트 **8300**, DB Postgres/pgvector **localhost:5437**, Redis 6381, Neo4j 7689(미사용)
- 대구 8개 구·군 (군위군 27720 제외)
- 대구 bbox: 위도 35.60~36.02, 경도 128.35~128.77 / 중심좌표 (128.60, 35.87)
- LLM은 수치 계산 금지 — 모든 점수·금액은 결정론 모듈
- 원본 저장소 `~/projects/cloud.beyondfacade`는 **읽기 전용** (절대 수정하지 않는다)
- `data/` 파일 경로는 `Path(__file__).resolve().parents[6]` = repo root 관례 유지 (디렉터리 깊이 동일하므로 수정 불요)
- 커밋은 태스크 단위. 서약: `.env`·`data/raw/` 대용량은 커밋 금지(.gitignore 확인)

## 원본 위치 참조 (읽기 전용)

- 백엔드: `~/projects/cloud.beyondfacade/backend/` (이하 "SRC")
- 수집 스크립트: `~/projects/cloud.beyondfacade/scripts/`
- 서울 결합 지점 전체 목록은 이 계획 각 태스크에 파일:라인으로 인라인됨

## 남는 것 / 버리는 것

| 이식 | 제외 |
|---|---|
| core/matrix 2파일, apps/{master,store,metric,funding,news,rag,rent,shock,convenience,tobacco}, migrations/ 12리비전, tests/ 45파일, main.py, requirements.txt, alembic.ini | apps/{ontology,dummy}(전부 0바이트), requirements-embed.txt(GPU 색인), academy 수집 실행(서울 전용 API — 코드는 남고 실행 안 함), 거리두기 수집(P2) |

**이 계획 범위 밖 (후속 계획):**
- RAG 색인·AI 리포트 생성(SSE `/analysis`) — 프론트 연동 시점(D-2)에 별도 계획
- 전통시장·온누리·백년가게·나들가게·대구교통공사 승하차 적재 — data.go.kr 활용신청 승인(당일) + 데이터셋 ID 확정 후 D-3 별도 계획 (apilist §1-6)
- 소진공 상가정보(15012005) 전업종 스냅샷 — Metabole에 전업종 수집기가 없어(편의점 sdsc2만) 신규 작성 필요, D-3 계획에 포함. 그 전까지 경쟁밀도는 인허가 store_count로 대체

---

### Task 1: 코드 이식 — 복사·의존성·테스트 그린

**Files:**
- Create: `backend/core/`, `backend/apps/`(10개 BC), `backend/migrations/`, `backend/tests/`, `backend/main.py`, `backend/requirements.txt`, `backend/alembic.ini` (전부 SRC에서 복사)
- Delete: `backend/apps/dummy/` (로컬 빈 스캐폴드 — SRC 것으로 대체하지 않고 제거)
- Modify: `backend/core/matrix/grid_keymaker_secret_manager.py`, `backend/main.py:19`

**Interfaces:**
- Produces: `core.matrix.grid_oracle_database_manager.get_engine/get_session/session_scope/OrmBase` — 이후 모든 태스크가 사용. `core.matrix.grid_keymaker_secret_manager.get_settings()` — Settings 객체.

- [ ] **Step 1: 복사 (ontology/dummy/venv/캐시 제외)**

```bash
cd /home/kimchungsik/projects/cloud.localhostdaegu
rm -rf backend/apps/dummy backend/core backend/apps  # 빈 스캐폴드 제거 (main.py·.env·Dockerfile·CLAUDE.md는 유지)
SRC=~/projects/cloud.beyondfacade/backend
rsync -a --exclude='__pycache__' --exclude='.venv' --exclude='apps/ontology' --exclude='apps/dummy' \
  --exclude='.env' --exclude='docs' \
  $SRC/core $SRC/apps $SRC/migrations $SRC/tests $SRC/alembic.ini $SRC/requirements.txt backend/
cp $SRC/main.py backend/main.py
```

- [ ] **Step 2: Settings 대구화 — 미사용 필수키를 optional로**

`backend/core/matrix/grid_keymaker_secret_manager.py` 수정:
- `seoul_open_data_api_key: str` → `seoul_open_data_api_key: str = ""` (대구판에서 학원 수집 안 함)
- `vworld_service_domain: str = "beyondfacade.cloud"` 는 **그대로 둔다** — 기존 VWORLD_API_KEY가 이 도메인으로 발급된 키이므로 키 재사용 시 도메인이 일치해야 함. 배포 시 localhostdaegu.cloud용 키를 새로 받으면 `.env`의 `VWORLD_SERVICE_DOMAIN`으로 덮어씀 `[확인]`
- 필드 추가: `region: str = "daegu"`

- [ ] **Step 3: CORS 포트 교체**

`backend/main.py:19` — `allow_origins=["http://localhost:3200", ...]` → `["http://localhost:3300", "http://127.0.0.1:3300"]`

- [ ] **Step 4: venv 구성 + 설치**

```bash
cd backend
# python3.14 없으면 3.12+ 아무거나 (itertools.batched 때문에 3.12 미만 불가)
(command -v python3.14 || command -v python3.13 || command -v python3.12) | head -1
$(command -v python3.14 || command -v python3.13 || command -v python3.12) -m venv .venv
.venv/bin/pip install -r requirements.txt
```

- [ ] **Step 5: DB 비의존 테스트 그린 확인**

```bash
cd backend && .venv/bin/python -m pytest tests/ --deselect tests/test_core_matrix.py -q
```
Expected: PASS (실 DB 요구 테스트는 test_core_matrix.py 뿐 — Task 3 이후 전체 그린)

- [ ] **Step 6: Commit**

```bash
git add backend/ && git commit -m "feat: port Metabole backend (core, 10 BCs, migrations, tests)"
```

---

### Task 2: 대구 RegionConfig — 서울 상수 교체

**Files:**
- Create: `backend/core/matrix/grid_region_config.py`
- Test: `backend/tests/test_region_config.py`
- Modify: `backend/apps/master/adapter/inbound/cli/seed_master.py:48,53-61,90,97-100` / `backend/apps/master/adapter/outbound/gateways/vworld_boundary_gateway.py:16-23,30` / `backend/apps/master/adapter/inbound/cli/load_boundaries.py:109` / `backend/apps/master/adapter/inbound/cli/load_population.py:84` / `backend/apps/store/adapter/outbound/gateways/mois_permit_gateway.py:25-27` / `backend/apps/tobacco/adapter/inbound/cli/load_tobacco_retailer.py:39-41` / `backend/apps/rent/adapter/outbound/gateways/rone_gateway.py:18,87,91`

**Interfaces:**
- Produces: `core.matrix.grid_region_config.REGION_NAME("대구")`, `DISTRICTS: dict[str, DistrictInfo]` (district_code → name·opn_authority_code·lawd_cd), `LAT_RANGE`, `LNG_RANGE`, `SIDO_ADM_PREFIX("27")`, `CSV_SIDO_PREFIX("대구")`, `MAP_CENTER`

- [ ] **Step 1: 실패 테스트 작성** — `backend/tests/test_region_config.py`

```python
from core.matrix.grid_region_config import DISTRICTS, LAT_RANGE, LNG_RANGE, SIDO_ADM_PREFIX

def test_daegu_districts_eight_without_gunwi():
    assert len(DISTRICTS) == 8
    assert "27720" not in DISTRICTS          # 군위군 제외
    assert DISTRICTS["27110"].name == "중구"
    assert DISTRICTS["27110"].opn_authority_code == "3410000"

def test_daegu_bbox():
    assert LAT_RANGE == (35.60, 36.02)
    assert LNG_RANGE == (128.35, 128.77)
    assert SIDO_ADM_PREFIX == "27"
```

- [ ] **Step 2: 실행해 실패 확인** — `cd backend && .venv/bin/python -m pytest tests/test_region_config.py -q` → FAIL (ModuleNotFoundError)

- [ ] **Step 3: 구현** — `backend/core/matrix/grid_region_config.py`

```python
"""대구 지역 구성 — 서울 상수를 대체하는 단일 원천.
opn_authority_code는 LOCALDATA 체계 추정값 — 인허가 첫 실호출(Task 4)에서 확정 후 갱신."""
from dataclasses import dataclass

REGION_NAME = "대구"
CSV_SIDO_PREFIX = "대구"          # 주민등록 CSV 행 필터 ("대구광역시 …")
SIDO_ADM_PREFIX = "27"            # 통계청/행안부 시도코드
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
```

- [ ] **Step 4: 테스트 그린 확인** — 같은 명령 → PASS

- [ ] **Step 5: seed_master.py 대구화**

`backend/apps/master/adapter/inbound/cli/seed_master.py`:
- L53-61 `_OPN_AUTHORITY_CODES`(서울 25개구 딕셔너리) 삭제 → `from core.matrix.grid_region_config import DISTRICTS, CSV_SIDO_PREFIX` 후 DISTRICTS로 시드 (district_code·name·opn_authority_code)
- L48 `("academy", "seoul_academy", "OA-20528")` 소스 매핑 행 제거 (서울 전용 원천)
- L90 `if not head.startswith("서울"): continue` → `startswith(CSV_SIDO_PREFIX)`
- L97-100 어절 파싱의 시도 접두 전제("서울특별시 종로구 …")는 "대구광역시 중구 …"와 동일 구조 — 로직 유지, 주석만 갱신

- [ ] **Step 6: vworld 경계 게이트웨이 일반화**

`backend/apps/master/adapter/outbound/gateways/vworld_boundary_gateway.py`:
- L16-23 `_SEOUL_FILTER` (`adm_cd LIKE '11*'`) → `from core.matrix.grid_region_config import SIDO_ADM_PREFIX` 사용해 `f"adm_cd LIKE '{SIDO_ADM_PREFIX}*'"`
- L30 `fetch_seoul_admin_dongs()` → `fetch_admin_dongs()` 로 개명
- `backend/apps/master/adapter/inbound/cli/load_boundaries.py:109` 호출부 동일 개명

- [ ] **Step 7: 인구 CSV 필터** — `load_population.py:84` `startswith("서울")` → `startswith(CSV_SIDO_PREFIX)` (import 추가)

- [ ] **Step 8: bbox 상수 일원화**

- `backend/apps/store/adapter/outbound/gateways/mois_permit_gateway.py:25-27` `_LAT_RANGE=(37.0,38.2)/_LNG_RANGE=(126.3,127.6)` → `grid_region_config`의 `LAT_RANGE/LNG_RANGE` import
- `backend/apps/tobacco/adapter/inbound/cli/load_tobacco_retailer.py:39-41` 동일 교체

- [ ] **Step 9: R-ONE 필터** — `backend/apps/rent/adapter/outbound/gateways/rone_gateway.py` L18 `_SEOUL = "서울"` → `from core.matrix.grid_region_config import REGION_NAME` 사용, L87·91의 `CLS_FULLNM` 접두 비교를 REGION_NAME 기반으로

- [ ] **Step 10: 기존 테스트 회귀 확인**

```bash
cd backend && .venv/bin/python -m pytest tests/ --deselect tests/test_core_matrix.py -q
```
Expected: PASS — 서울 기대값이 박힌 게이트웨이 테스트가 있으면 픽스처를 대구 값으로 갱신 (테스트 의도 유지, 기대값만 교체)

- [ ] **Step 11: Commit** — `git commit -m "feat: daegu region config replaces seoul constants"`

---

### Task 3: 인프라 기동 — DB·마이그레이션·마스터 시드

**Files:**
- Create: `data/raw/jumin/` (CSV 배치), `data/geojson/regions/*.json` (load_boundaries 산출)
- Modify: 없음 (실행 태스크)

**Interfaces:**
- Produces: 테이블 19개 스키마 + `district` 8행 + `region`(대구 행정동 ~140) + `industry_source_code`(7업종 slug) — Task 4 수집기가 이 시드를 조회해 돈다

- [ ] **Step 1: 데이터 스토어 기동** — `docker compose up -d db redis` → `docker compose ps` 로 healthy 확인
- [ ] **Step 2: 마이그레이션** — `cd backend && .venv/bin/python -m alembic upgrade head` → `alembic current` 가 `66a23fb0c6e9 (head)` 출력
- [ ] **Step 3: 주민등록 CSV 준비** — SRC의 `data/raw/jumin/*.csv` 확인: 전국 원본이면 그대로 `data/raw/jumin/`에 복사(파서가 대구 행만 읽음), 서울 필터본이면 jumin.mois.go.kr에서 "대구광역시 → 월간 → 전체읍면동현황" CSV 수동 다운로드 후 배치 **(사람 개입 지점 — 다운로드 필요 시 사용자에게 요청)**
- [ ] **Step 4: 시드 실행**

```bash
.venv/bin/python -m apps.master.adapter.inbound.cli.seed_master
.venv/bin/python -m apps.master.adapter.inbound.cli.load_boundaries   # 브이월드 WFS 대구 읍면동
.venv/bin/python -m apps.master.adapter.inbound.cli.load_population
```

- [ ] **Step 5: 시드 검증 쿼리**

```bash
.venv/bin/python - <<'EOF'
from sqlalchemy import text
from core.matrix.grid_oracle_database_manager import session_scope
with session_scope() as s:
    print("district:", s.execute(text("select count(*) from district")).scalar())      # = 8
    print("region:", s.execute(text("select count(*) from region")).scalar())          # ≈ 140±20
    print("slug:", s.execute(text("select count(*) from industry_source_code where source_system='mois_permit'")).scalar())  # = 7
EOF
```

- [ ] **Step 6: DB 테스트 포함 전체 그린** — `.venv/bin/python -m pytest tests/ -q` → PASS
- [ ] **Step 7: Commit** — `git add data/geojson && git commit -m "chore: daegu master seed + boundaries"` (CSV 원본은 .gitignore 확인 후 제외)

---

### Task 4: 인허가 수집 — OPN 코드 확정 → 전량 적재 → 지표 빌드

**Files:**
- Modify(조건부): `backend/core/matrix/grid_region_config.py` (OPN 코드 실값 반영), `docs/apilist.md` §11
- 실행: `apps.store...store_collector`, `apps.store...assign_regions`, `apps.metric...build_metrics`

**Interfaces:**
- Produces: `store` 테이블(대구 7업종 전량) + `region_industry_metric`(행정동×업종×연도 개폐업 지표) — 위험도 API(Task 7)와 프론트 코로플레스의 원천

- [ ] **Step 1: OPN_ATMY_GRP_CD 실값 확정 (1건 호출)**

```bash
cd backend && .venv/bin/python - <<'EOF'
import httpx, os
from core.matrix.grid_keymaker_secret_manager import get_settings
key = get_settings().data_go_kr_api_key
r = httpx.get("https://apis.data.go.kr/1741000/general_restaurants/info",
    params={"serviceKey": key, "pageNo": 1, "numOfRows": 5, "returnType": "json",
            "cond[OPN_ATMY_GRP_CD::EQ]": "3410000"}, timeout=30)
print(r.status_code, r.text[:800])
EOF
```
- 응답에 대구 중구 데이터가 오면 3410000 체계 확정. 빈 응답이면 `cond[ROAD_NM_ADDR::LIKE]=대구광역시 중구` 등으로 1건 조회해 응답의 `OPN_ATMY_GRP_CD` 실값을 읽고 `grid_region_config.DISTRICTS` 8개 값 + `docs/apilist.md` §11 갱신

- [ ] **Step 2: 전량 수집** — `.venv/bin/python -m apps.store.adapter.inbound.cli.store_collector` (7업종 × 8구·군, 증분 커서 `cond[DAT_UPDT_PNT::GTE]` — 초기 적재는 수 시간 가능, `run_in_background` + 로그 확인)
- [ ] **Step 3: 공간 조인** — `.venv/bin/python -m apps.store.adapter.inbound.cli.assign_regions` (shapely STRtree, 대구 geojson 사용)
- [ ] **Step 4: 지표 빌드** — `.venv/bin/python -m apps.metric.adapter.inbound.cli.build_metrics`
- [ ] **Step 5: 검증 게이트 (apilist §16)**

```bash
.venv/bin/python - <<'EOF'
from sqlalchemy import text
from core.matrix.grid_oracle_database_manager import session_scope
with session_scope() as s:
    rows = s.execute(text("select district_code, count(*) from store group by 1 order by 1")).all()
    print(rows)                                    # 8개 구·군 모두 count > 0
    bbox = s.execute(text("""select avg((lat between 35.60 and 36.02 and lng between 128.35 and 128.77)::int)
                             from store where lat is not null""")).scalar()
    print("bbox_ok_ratio:", bbox)                  # ≥ 0.95
    print("metrics:", s.execute(text("select count(*) from region_industry_metric")).scalar())  # > 0
EOF
```

- [ ] **Step 6: API 스모크** — `.venv/bin/uvicorn main:app --port 8300 &` 후

```bash
curl -s "http://localhost:8300/health"
curl -s "http://localhost:8300/regions/geojson" | head -c 300
curl -s "http://localhost:8300/metrics?industry=general_restaurants&year=2025" | head -c 300
curl -s "http://localhost:8300/stores?region=27110xxxxx" | head -c 300   # region 코드는 Step 5에서 확인한 실값
```

- [ ] **Step 7: Commit** — `git commit -m "feat: daegu permit collection + metrics verified"`

---

### Task 5: 나머지 P0 수집 가동 — funding·news·금리·rent + 크론 스크립트

**Files:**
- Create: `scripts/news-poller.sh`, `scripts/store-collector.sh`, `scripts/funding-collector.sh`, `scripts/interest-rate-collector.sh` (SRC `scripts/` 복사 후 수정), `logs/` (.gitignore 확인)
- Modify: `scripts/store-collector.sh` — 파이프라인에서 `academy_collector`(서울 전용)·`broker_collector`(P2) 단계 제거 → store → assign_regions → build_metrics 3단으로

**Interfaces:**
- Produces: `funding_program`(전국 공고), `news_article`(대구 키워드), `interest_rate`(ECOS 2계열), `rent_price`(R-ONE 대구 행)

- [ ] **Step 1: 스크립트 복사·수정** — SRC 4개 셸 복사, 내부 `BACKEND_DIR` 경로를 이 저장소로, store 파이프라인 3단 축소
- [ ] **Step 2: funding 1회 실행** — `bash scripts/funding-collector.sh` → `funding_program` count ≈ 1,500
- [ ] **Step 3: news 폴링 즉시 가동** — 키워드는 district 테이블에서 자동 생성(`{구·군명} 상권`)이므로 시드만으로 대구 전환됨. `bash scripts/news-poller.sh` 1회 실행 후 crontab 등록:

```
10 * * * * /home/kimchungsik/projects/cloud.localhostdaegu/scripts/news-poller.sh
20 4 * * * /home/kimchungsik/projects/cloud.localhostdaegu/scripts/store-collector.sh
10 5 * * * /home/kimchungsik/projects/cloud.localhostdaegu/scripts/funding-collector.sh
```

- [ ] **Step 4: 금리·임대료** — `bash scripts/interest-rate-collector.sh` → `interest_rate` 행 존재 + `rent_price`에 대구 행 존재 확인. **R-ONE 대구 상권 수를 여기서 확인** — 상권 단위 행이 희소하면 기획서 §10 미결 5(구 단위 평균 강등) 결정 보고
- [ ] **Step 5: Commit** — `git add scripts/ && git commit -m "feat: daegu collectors + cron scripts"`

---

### Task 6: Finance Engine — BEP·Runway·Funding Gap·스트레스 (신규, 순수 결정론)

**Files:**
- Create: `backend/apps/finance/domain/engine.py`, `backend/apps/finance/adapter/inbound/api/v1/finance_router.py`, `backend/apps/finance/adapter/inbound/api/schemas/finance_schema.py`
- Test: `backend/tests/test_finance_engine.py`
- Modify: `backend/main.py` (라우터 등록)

**Interfaces:**
- Consumes: 없음 (순수 함수 — DB 미접근. 금리는 요청 파라미터로 받고, 프론트가 `/shocks` 금리 API에서 채워 넘김)
- Produces: `POST /finance/simulate` → `FinanceResult{scenarios: [SimulationScenario×3], funding_gap, capex, monthly_fixed}` / 도메인 함수 `simulate(inp: FinanceInput) -> FinanceResult`

- [ ] **Step 1: 실패 테스트 작성** — `backend/tests/test_finance_engine.py`

```python
from apps.finance.domain.engine import FinanceInput, simulate

BASE = FinanceInput(
    deposit=20_000_000, key_money=0, interior_cost=30_000_000, equipment_cost=10_000_000,
    monthly_rent=2_000_000, monthly_payroll=6_000_000, monthly_insurance=500_000,
    cost_ratio=0.40, fee_ratio=0.03,
    equity=50_000_000, desired_loan=20_000_000, loan_rate=0.045,
    expected_monthly_revenue=20_000_000,
)

def test_capex_and_fixed():
    r = simulate(BASE)
    assert r.capex == 60_000_000                       # 보증금+권리금+인테리어+설비
    # 고정비 = 월세 + 이자(2천만×4.5%/12=75,000) + 보험 + 인건비
    assert r.monthly_fixed == 2_000_000 + 75_000 + 500_000 + 6_000_000

def test_bep_revenue():
    r = simulate(BASE)
    assert abs(r.bep_revenue - r.monthly_fixed / (1 - 0.43)) < 1   # 고정비/(1-변동비율)

def test_three_scenarios_and_payback():
    r = simulate(BASE)
    assert [s.name for s in r.scenarios] == ["비관", "기준", "낙관"]
    pess, base, opt = r.scenarios
    assert pess.monthly_revenue == 12_000_000          # 기준 × 0.6
    assert opt.monthly_revenue == 32_000_000           # 기준 × 1.6
    assert base.operating_profit == int(20_000_000 * (1 - 0.43)) - r.monthly_fixed
    assert base.payback_months == round(r.capex / base.operating_profit, 1)

def test_funding_gap_and_runway():
    r = simulate(BASE)
    # 필요총액 = capex + 운전자금(고정비×6개월). 부족 = 필요총액 - (자기자본+희망대출), 음수면 0
    need = r.capex + r.monthly_fixed * 6
    assert r.funding_gap == max(0, need - (50_000_000 + 20_000_000))
    pess = r.scenarios[0]
    if pess.operating_profit < 0:                       # 적자 시나리오만 runway 유한
        cash = 50_000_000 + 20_000_000 - r.capex
        assert pess.runway_months == round(cash / -pess.operating_profit, 1)

def test_interest_stress():
    r = simulate(BASE)
    assert r.stress[0].rate_delta == 0.01 and r.stress[1].rate_delta == 0.02
    assert r.stress[0].monthly_fixed > r.monthly_fixed  # 금리 +1%p → 고정비 증가
```

- [ ] **Step 2: 실행해 실패 확인** — `pytest tests/test_finance_engine.py -q` → FAIL (import error)
- [ ] **Step 3: 구현** — `backend/apps/finance/domain/engine.py`

```python
"""재무 시뮬레이션 결정론 엔진 — 부트캠프 과제 계산식 계승.
CAPEX=보증금+권리금+인테리어+설비 / OPEX고정=월세+이자+보험+인건비 /
변동비=매출×(원가율+수수료율) / BEP매출=고정비/(1-변동비율) /
시나리오 비관·기준·낙관 = 기준 × 0.6 / 1.0 / 1.6"""
from dataclasses import dataclass, field

_SCENARIO_MULTIPLIERS = (("비관", 0.6), ("기준", 1.0), ("낙관", 1.6))
_WORKING_CAPITAL_MONTHS = 6
_STRESS_DELTAS = (0.01, 0.02)

@dataclass(frozen=True)
class FinanceInput:
    deposit: int; key_money: int; interior_cost: int; equipment_cost: int
    monthly_rent: int; monthly_payroll: int; monthly_insurance: int
    cost_ratio: float; fee_ratio: float
    equity: int; desired_loan: int; loan_rate: float
    expected_monthly_revenue: int

@dataclass(frozen=True)
class SimulationScenario:
    name: str; monthly_revenue: int; variable_cost: int
    operating_profit: int; payback_months: float | None; runway_months: float | None

@dataclass(frozen=True)
class StressResult:
    rate_delta: float; monthly_fixed: int; base_operating_profit: int

@dataclass(frozen=True)
class FinanceResult:
    capex: int; monthly_fixed: int; bep_revenue: int; funding_gap: int
    scenarios: list[SimulationScenario] = field(default_factory=list)
    stress: list[StressResult] = field(default_factory=list)

def _monthly_interest(principal: int, rate: float) -> int:
    return int(principal * rate / 12)

def _fixed(inp: FinanceInput, rate: float) -> int:
    return inp.monthly_rent + _monthly_interest(inp.desired_loan, rate) + inp.monthly_insurance + inp.monthly_payroll

def simulate(inp: FinanceInput) -> FinanceResult:
    capex = inp.deposit + inp.key_money + inp.interior_cost + inp.equipment_cost
    fixed = _fixed(inp, inp.loan_rate)
    var_ratio = inp.cost_ratio + inp.fee_ratio
    bep_revenue = int(fixed / (1 - var_ratio))
    available_cash = inp.equity + inp.desired_loan - capex
    need = capex + fixed * _WORKING_CAPITAL_MONTHS
    funding_gap = max(0, need - (inp.equity + inp.desired_loan))

    scenarios = []
    for name, mult in _SCENARIO_MULTIPLIERS:
        revenue = int(inp.expected_monthly_revenue * mult)
        variable = int(revenue * var_ratio)
        profit = int(revenue * (1 - var_ratio)) - fixed
        payback = round(capex / profit, 1) if profit > 0 else None      # 영업이익 ≤ 0 → 회수 불가
        runway = round(available_cash / -profit, 1) if (profit < 0 and available_cash > 0) else None
        scenarios.append(SimulationScenario(name, revenue, variable, profit, payback, runway))

    base_revenue_profit = lambda f: int(inp.expected_monthly_revenue * (1 - var_ratio)) - f
    stress = [StressResult(d, _fixed(inp, inp.loan_rate + d), base_revenue_profit(_fixed(inp, inp.loan_rate + d)))
              for d in _STRESS_DELTAS]
    return FinanceResult(capex, fixed, bep_revenue, funding_gap, scenarios, stress)
```

- [ ] **Step 4: 테스트 그린 확인** — PASS 될 때까지 수정 (테스트가 정의한 산식이 진실)
- [ ] **Step 5: 라우터·스키마 작성 + main.py 등록**

`finance_schema.py`: `FinanceInput`/`FinanceResult`를 미러링한 Pydantic 모델 (`SimulateRequest`, `SimulateResponse`). `finance_router.py`:

```python
from fastapi import APIRouter
from apps.finance.adapter.inbound.api.schemas.finance_schema import SimulateRequest, SimulateResponse
from apps.finance.domain.engine import FinanceInput, simulate

router = APIRouter(prefix="/finance", tags=["finance"])

@router.get("/myself")
def myself() -> dict:
    return {"app": "finance", "status": "wired"}

@router.post("/simulate", response_model=SimulateResponse)
def run_simulation(req: SimulateRequest) -> SimulateResponse:
    return SimulateResponse.from_result(simulate(FinanceInput(**req.model_dump())))
```

`main.py`에 `app.include_router(finance_router)` 추가.

- [ ] **Step 6: API 스모크** — `curl -s -X POST http://localhost:8300/finance/simulate -H 'content-type: application/json' -d '{...BASE 값...}'` → 200 + scenarios 3개
- [ ] **Step 7: Commit** — `git commit -m "feat: deterministic finance engine (BEP/runway/funding-gap/stress)"`

---

### Task 7: 위험도 스코어 API — metric 앱 확장

**Files:**
- Create: `backend/apps/metric/domain/risk.py`, `backend/apps/metric/app/use_cases/risk_interactor.py`
- Test: `backend/tests/test_metric_risk.py`
- Modify: `backend/apps/metric/adapter/inbound/api/v1/region_industry_metric_router.py` (엔드포인트 추가)

**Interfaces:**
- Consumes: `region_industry_metric` 테이블 (closure_rate·store_count·growth_rate, Task 4 산출)
- Produces: `GET /metrics/risk?region_code=&industry=&year=` → `{score: 0~100, grade: "red|yellow|green", components: {closure, density, growth}}` / 도메인 함수 `risk_score(closure_pct, density_pct, growth_pct) -> RiskScore`

- [ ] **Step 1: 실패 테스트** — `backend/tests/test_metric_risk.py`

```python
from apps.metric.domain.risk import risk_score

def test_weights_sum():
    # 대구 조정 산식: 폐업률 0.4 + 경쟁밀도 0.4 + 신규진입 급증 0.2 (백분위 0~1 입력)
    # (부트캠프 원식의 매출감소·프랜차이즈포화 축은 카드매출 부재로 로드맵 — docs/daegunavi.md §8)
    s = risk_score(closure_pct=1.0, density_pct=1.0, growth_pct=1.0)
    assert s.score == 100

def test_grade_bands():
    assert risk_score(0.9, 0.9, 0.9).grade == "red"       # ≥ 70
    assert risk_score(0.5, 0.5, 0.5).grade == "yellow"    # 40~69
    assert risk_score(0.1, 0.1, 0.1).grade == "green"     # < 40

def test_components_reported():
    s = risk_score(0.8, 0.2, 0.5)
    assert s.components == {"closure": 32.0, "density": 8.0, "growth": 10.0}
```

- [ ] **Step 2: 실패 확인** → FAIL
- [ ] **Step 3: 구현** — `backend/apps/metric/domain/risk.py`

```python
from dataclasses import dataclass

_W_CLOSURE, _W_DENSITY, _W_GROWTH = 0.4, 0.4, 0.2

@dataclass(frozen=True)
class RiskScore:
    score: float; grade: str; components: dict[str, float]

def risk_score(closure_pct: float, density_pct: float, growth_pct: float) -> RiskScore:
    c = round(closure_pct * _W_CLOSURE * 100, 1)
    d = round(density_pct * _W_DENSITY * 100, 1)
    g = round(growth_pct * _W_GROWTH * 100, 1)
    total = round(c + d + g, 1)
    grade = "red" if total >= 70 else ("yellow" if total >= 40 else "green")
    return RiskScore(total, grade, {"closure": c, "density": d, "growth": g})
```

- [ ] **Step 4: 그린 확인** → PASS
- [ ] **Step 5: 인터랙터 + 엔드포인트** — `risk_interactor.py`: 최신 연도 `region_industry_metric`을 업종별로 읽어 각 region의 closure_rate·store_count(밀도)·growth_rate를 **동일 업종 전체 region 대비 백분위**로 변환 후 `risk_score` 호출. 라우터에 `GET /metrics/risk` 추가 — region_code 지정 시 단건, 미지정 시 전체 region 랭킹(사용자 흐름 B유형 "업종별 위험도 랭킹"의 원천).
- [ ] **Step 6: API 스모크** — `curl "http://localhost:8300/metrics/risk?industry=general_restaurants"` → region별 score 배열
- [ ] **Step 7: Commit** — `git commit -m "feat: risk score API (closure/density/growth percentile model)"`

---

### Task 8: 금융상품 매칭 — 수기 JSON + 매칭 API

**Files:**
- Create: `data/manual/imbank_products.json`, `data/manual/dgsinbo_products.json`, `data/manual/daegu_youth_startup.json` (초기엔 각 2~3개 상품 스텁 — 실값은 사용자가 상품 페이지 보고 보강), `backend/apps/matching/domain/matcher.py`, `backend/apps/matching/adapter/outbound/gateways/manual_product_gateway.py`, `backend/apps/matching/adapter/inbound/api/v1/matching_router.py`
- Test: `backend/tests/test_matching.py`
- Modify: `backend/main.py` (라우터 등록)

**Interfaces:**
- Consumes: Task 6의 funding_gap 값 (요청 파라미터로)
- Produces: `GET /matching?funding_gap=&category=&business_age_months=&owner_age=` → 우선순위 정렬 상품 리스트. JSON 스키마(apilist §13): `product_id, provider, provider_type("guarantee"|"bank"|"policy"), product_name, target, region, business_age_min, business_age_max, category(list|null=전업종), owner_age_max(null 가능), loan_limit, interest_rate, guarantee_fee, url`

- [ ] **Step 1: 실패 테스트** — `backend/tests/test_matching.py`

```python
from apps.matching.domain.matcher import match_products

PRODUCTS = [
    {"product_id": "dgsinbo-1", "provider_type": "guarantee", "loan_limit": 30_000_000,
     "category": None, "business_age_min": 0, "business_age_max": None, "owner_age_max": None},
    {"product_id": "imbank-1", "provider_type": "bank", "loan_limit": 50_000_000,
     "category": ["general_restaurants"], "business_age_min": 0, "business_age_max": None, "owner_age_max": None},
    {"product_id": "youth-1", "provider_type": "policy", "loan_limit": 20_000_000,
     "category": None, "business_age_min": 0, "business_age_max": 12, "owner_age_max": 39},
]

def test_priority_order_guarantee_bank_policy():
    out = match_products(PRODUCTS, funding_gap=10_000_000, category="general_restaurants",
                         business_age_months=0, owner_age=30)
    assert [p["product_id"] for p in out] == ["dgsinbo-1", "imbank-1", "youth-1"]

def test_filters_apply():
    out = match_products(PRODUCTS, funding_gap=10_000_000, category="rest_cafes",
                         business_age_months=24, owner_age=45)
    # imbank-1은 업종 불일치, youth-1은 업력·연령 초과 → 보증만 남음
    assert [p["product_id"] for p in out] == ["dgsinbo-1"]

def test_limit_filter():
    out = match_products(PRODUCTS, funding_gap=40_000_000, category="general_restaurants",
                         business_age_months=0, owner_age=30)
    assert "dgsinbo-1" not in [p["product_id"] for p in out]   # 한도 3천 < 부족 4천
```

- [ ] **Step 2: 실패 확인** → FAIL
- [ ] **Step 3: 구현** — `matcher.py`

```python
_PRIORITY = {"guarantee": 0, "bank": 1, "policy": 2}   # 보증 연계 → 은행 → 정책자금

def match_products(products: list[dict], funding_gap: int, category: str,
                   business_age_months: int, owner_age: int | None) -> list[dict]:
    def ok(p: dict) -> bool:
        if p["loan_limit"] is not None and p["loan_limit"] < funding_gap: return False
        if p["category"] is not None and category not in p["category"]: return False
        if p["business_age_min"] is not None and business_age_months < p["business_age_min"]: return False
        if p["business_age_max"] is not None and business_age_months > p["business_age_max"]: return False
        if p["owner_age_max"] is not None and (owner_age is None or owner_age > p["owner_age_max"]): return False
        return True
    return sorted((p for p in products if ok(p)), key=lambda p: _PRIORITY[p["provider_type"]])
```

- [ ] **Step 4: 그린 확인** → PASS
- [ ] **Step 5: 게이트웨이 + 라우터** — `manual_product_gateway.py`: `data/manual/*.json` 3파일을 읽어 스키마 검증 후 합침(`Path(__file__).resolve().parents[6] / "data" / "manual"`). 라우터: 쿼리 파라미터 4개 → matcher 호출. `main.py` 등록. `data/manual/` JSON 스텁 3파일 작성 — **필드는 스키마 완전 준수, 값은 `"[확인] imbank.co.kr에서 실값 기입"` 마커** (기획서 §9 D-2 태스크가 실값 보강)
- [ ] **Step 6: API 스모크** — `curl "http://localhost:8300/matching?funding_gap=20000000&category=rest_cafes&business_age_months=0&owner_age=32"` → 200 + 정렬된 배열
- [ ] **Step 7: Commit** — `git commit -m "feat: financial product matching (guarantee>bank>policy)"`

---

### Task 9: 의도 추출 API — 채팅 한 문장 → 지역·업종·예산

**Files:**
- Create: `backend/apps/intent/domain/parser.py`, `backend/apps/intent/domain/landmarks.py`, `backend/apps/intent/adapter/inbound/api/v1/intent_router.py`
- Test: `backend/tests/test_intent_parser.py`
- Modify: `backend/main.py` (라우터 등록)

**Interfaces:**
- Consumes: `district`·`region` 테이블 (동/구 명칭 사전 — 라우터 계층에서 주입), `industry_source_code` slug
- Produces: `POST /intent {text}` → `{intent_type: "A|B|C", district_code?, region_name?, industry_slug?, budget_krw?, missing: []}` — 프론트 ⓪①단계가 이 응답으로 URL 상태를 만든다

- [ ] **Step 1: 실패 테스트** — `backend/tests/test_intent_parser.py`

```python
from apps.intent.domain.parser import parse_intent

# 사전은 순수 함수 인자 — DB 없이 테스트
DONGS = {"대신동": "27110", "상동": "27260", "중동": "27260", "성내1동": "27110"}
GUS = {"중구": "27110", "수성구": "27260", "달서구": "27290"}

def test_type_a_full():
    r = parse_intent("수성구 들안길에 카페 차리고 싶어, 예산 5천", DONGS, GUS)
    assert r.intent_type == "A"
    assert r.district_code == "27260"           # 들안길 → 랜드마크 별칭 → 수성구
    assert r.industry_slug == "rest_cafes"      # 카페 → 휴게음식점
    assert r.budget_krw == 50_000_000           # "5천" → 5,000만원

def test_type_b_region_only():
    r = parse_intent("서문시장 근처에서 장사하고 싶은데", DONGS, GUS)
    assert r.intent_type == "B"
    assert r.district_code == "27110"           # 서문시장 → 대신동 → 중구
    assert "industry" in r.missing

def test_type_c_budget_only():
    r = parse_intent("예산 5천이면 뭐 할 수 있어?", DONGS, GUS)
    assert r.intent_type == "C"
    assert r.budget_krw == 50_000_000
    assert "region" in r.missing

def test_budget_variants():
    assert parse_intent("3억으로", DONGS, GUS).budget_krw == 300_000_000
    assert parse_intent("7000만원 있어", DONGS, GUS).budget_krw == 70_000_000
```

- [ ] **Step 2: 실패 확인** → FAIL
- [ ] **Step 3: 구현**

`landmarks.py` — 대구 특화 별칭 테이블 (지역성 카드):

```python
"""랜드마크 → (대표 행정동, district_code). 시연 입력이 바로 먹히는 대구 별칭 사전."""
LANDMARKS: dict[str, tuple[str, str]] = {
    "서문시장": ("대신동", "27110"), "동성로": ("성내1동", "27110"), "약령시": ("성내2동", "27110"),
    "칠성시장": ("칠성동", "27230"), "평화시장": ("신암동", "27140"), "동대구역": ("신암동", "27140"),
    "안지랑": ("대명동", "27200"), "앞산": ("대명동", "27200"),
    "들안길": ("상동", "27260"), "수성못": ("두산동", "27260"), "알파시티": ("고산동", "27260"),
    "동인동": ("동인동", "27110"), "두류": ("두류동", "27290"), "계명대": ("신당동", "27290"),
    "경북대": ("산격동", "27230"),
}
INDUSTRY_SYNONYMS: dict[str, str] = {
    "카페": "rest_cafes", "커피": "rest_cafes", "디저트": "rest_cafes",
    "음식점": "general_restaurants", "식당": "general_restaurants", "고깃집": "general_restaurants",
    "곱창": "general_restaurants", "찜갈비": "general_restaurants", "치킨": "general_restaurants",
    "미용실": "beauty_salons", "헬스장": "fitness_centers", "체육관": "fitness_centers",
    "당구장": "billiard_halls", "노래방": "karaoke_rooms", "피시방": "pc_bangs", "PC방": "pc_bangs",
}
```

`parser.py`:

```python
import re
from dataclasses import dataclass, field
from apps.intent.domain.landmarks import LANDMARKS, INDUSTRY_SYNONYMS

_BUDGET = re.compile(r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(억|천만|천|만)?\s*원?")

@dataclass(frozen=True)
class Intent:
    intent_type: str
    district_code: str | None = None
    region_name: str | None = None
    industry_slug: str | None = None
    budget_krw: int | None = None
    missing: list[str] = field(default_factory=list)

def _parse_budget(text: str) -> int | None:
    m = _BUDGET.search(text.replace(",", ""))
    if not m: return None
    num, unit = float(m.group(1)), m.group(2)
    scale = {"억": 100_000_000, "천만": 10_000_000, "천": 10_000_000, "만": 10_000}.get(unit)
    if scale is None: return None                      # 단위 없는 맨숫자는 무시 (오탐 방지)
    return int(num * scale)

def parse_intent(text: str, dongs: dict[str, str], gus: dict[str, str]) -> Intent:
    district, region_name = None, None
    for name, (dong, code) in LANDMARKS.items():       # 랜드마크 우선
        if name in text: district, region_name = code, dong; break
    if district is None:
        for dong, code in dongs.items():
            if dong in text: district, region_name = code, dong; break
    if district is None:
        for gu, code in gus.items():
            if gu in text: district = code; break
    industry = next((slug for word, slug in INDUSTRY_SYNONYMS.items() if word in text), None)
    budget = _parse_budget(text)

    missing = [k for k, v in (("region", district), ("industry", industry), ("budget", budget)) if v is None]
    if district and industry: itype = "A"
    elif district: itype = "B"
    else: itype = "C"
    return Intent(itype, district, region_name, industry, budget, missing)
```

- [ ] **Step 4: 그린 확인** → PASS (`수성구 들안길` 케이스: 랜드마크 "들안길"이 먼저 걸려 27260 — 구명과 일치 확인)
- [ ] **Step 5: 라우터** — `POST /intent`: DB에서 dongs(`region.name→district_code`)·gus(`district.name→code`) 로드(요청당 1쿼리, lru_cache 5분) 후 `parse_intent` 호출. `main.py` 등록. **LLM 폴백은 이번 범위 제외** — missing이 있으면 프론트가 칩으로 되물음 (기획서 ①)
- [ ] **Step 6: API 스모크** — `curl -s -X POST localhost:8300/intent -d '{"text":"서문시장 근처 카페, 예산 5천"}' -H 'content-type: application/json'` → `{"intent_type":"A","district_code":"27110",...}`
- [ ] **Step 7: Commit** — `git commit -m "feat: intent parser (landmark/industry/budget dictionaries)"`

---

### Task 10 (선택, P1): 담배소매업 파일 적재 — 편의점 프록시

Metabole tobacco 앱은 서울 아카이브 CSV 전용. 대구 전환:

- [ ] D-데이터허브 `dataSetId=DMI_0000119426` (26년07월 대구 담배소매업) 수동 다운로드 → `data/raw/tobacco_retail_daegu/` **(사람 개입 지점)**
- [ ] `load_tobacco_retailer.py`의 입력 경로·컬럼 매핑을 대구 파일 헤더에 맞춰 수정 (bbox는 Task 2에서 이미 대구화). 좌표 컬럼 없으면 SGIS 지오코딩 소량 — 그마저 없으면 이 태스크 스킵하고 convenience 앱(소진공 API, 지역 무관)만 사용
- [ ] 적재 후 count > 0 확인, Commit

---

### 최종 검증 게이트 (전체 완료 판정)

- [ ] `pytest tests/ -q` 전체 그린 (DB 포함)
- [ ] `GET /health`, `/regions/geojson`, `/metrics`, `/metrics/risk`, `/stores`, `/funding`, `/shocks` 모두 200
- [ ] `POST /finance/simulate`, `/intent`, `GET /matching` 모두 200 + 스키마 정합
- [ ] apilist §16: 인허가 8구·군 count>0 · bbox ≥95% · 매칭 3케이스 상품 ≥1건
- [ ] `docs/jekyll.md` 개발로그에 당일 실측 기록 (수집 건수·소요시간·미결)
