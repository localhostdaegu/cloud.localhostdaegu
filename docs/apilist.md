# API 연결 목록 — localhostdaegu 프로토타입

> 기준일: 2026-09-15 / 원천: `DAEGU_DATA_API_GUIDE.md` + `METABOLE_DAEGU_API_MIGRATION.md` 통합
> 원칙: **신규 발급 키 0개** — 전부 기존 `backend/.env` 키 재사용 + data.go.kr 활용신청 추가만
> 범례: P0 필수 / P1 권장 / P2 여력 시 / `[확인]` 실호출로 확정 필요

---

## 0. 환경변수 총람 (`backend/.env`)

```bash
DATA_GO_KR_API_KEY=       # 공공데이터포털 (§1)
RONE_API_KEY=             # 한국부동산원 R-ONE (§2)
ECOS_API_KEY=             # 한국은행 ECOS (§3)
BIZINFO_API_KEY=          # 기업마당 (§4)
YOUTHCENTER_API_KEY=      # 온통청년 (§5)
NAVER_NCP_API_KEY_ID=     # 네이버 뉴스 (§6)
NAVER_NCP_API_KEY=
VWORLD_API_KEY=           # 브이월드 (§7)
KOSIS_API_KEY=            # KOSIS (§8, P2)
SGIS_SERVICE_ID=          # SGIS 지오코딩 fallback (§9, P3)
SGIS_SECURITY_KEY=
FTC_FRANCHISE_API_KEY=    # 공정위 가맹 창업비용 (§10, P2) — data.go.kr 경유면 불필요 [확인]
GEMINI_API_KEY=           # LLM — RAG 해석·리포트 생성 (수치 계산 금지)

# 추가 설정
REGION=daegu
NAVER_NEWS_KEYWORDS_FILE=config/news_keywords_daegu.json

# 데이터 스토어 (로컬 기본값 — backend/.env에 채워져 있음)
DATABASE_URL=postgresql+psycopg://localhostdaegu:localhostdaegu@localhost:5437/localhostdaegu
REDIS_URL=redis://localhost:6381/0
NEO4J_URI=bolt://localhost:7689
NEO4J_AUTH=neo4j/localhostdaegu
```

제외 키(주석 처리): `SEOUL_OPEN_DATA_API_KEY`(서울 전용) · `CHILDCARE_API_KEY`(프로토타입 제외) · `TUNNEL_TOKEN`(배포 시)

---

## 1. 공공데이터포털 — www.data.go.kr

키: `DATA_GO_KR_API_KEY` (기존 발급분 그대로)

### 1-1. 지방행정 인허가 7업종 (행정안전부) — **P0, 개폐업 시계열의 진실 소스**

엔드포인트:

```
GET https://apis.data.go.kr/1741000/{slug}/{info|history}
```

공통 파라미터:

```
serviceKey, pageNo, numOfRows(max 100), returnType=json
cond[OPN_ATMY_GRP_CD::EQ]=3410000     ← 구·군별 루프 (§11 코드표)
cond[LCPMT_YMD::GTE]=20170101         ← 인허가일자 시작
cond[DAT_UPDT_PNT::GTE]=...           ← 증분 수집 커서
/history 전용: cond[BASE_DATE::EQ]=YYYYMMDD   ← 시점 스냅샷
```

| 업종 | slug | data.go.kr 데이터셋 ID |
|---|---|---|
| 일반음식점 | `general_restaurants` | 15154916 |
| 휴게음식점 | `rest_cafes` | 15154921 |
| 미용업 | `beauty_salons` | 15154918 |
| 체력단련장업 | `fitness_centers` | 15155077 |
| 당구장업 | `billiard_halls` | 15155011 |
| 노래연습장업 | `karaoke_rooms` | 15155135 |
| PC방 | `pc_bangs` | 15154951 |

- 활용신청: **완료(기존)** — 파라미터만 대구로 교체
- 응답 핵심 컬럼: `BPLC_NM`, `LCPMT_YMD`, `CLSBIZ_YMD`, `DTL_SALS_STTS_NM`, `MNG_NO`, `ROAD_NM_ADDR`, `CRD_INFO_X/Y`, `BZSTAT_SE_NM`, `OPN_ATMY_GRP_CD`
- 좌표: `CRD_INFO_X/Y`는 EPSG:5174 → WGS84 변환 (서울 로직 재사용)
- ⚠️ 첫 호출 응답의 `OPN_ATMY_GRP_CD` 실값으로 §11 코드표 **반드시 확정** `[확인]`

### 1-2. 소진공 상가(상권)정보 — **P0, 현재 경쟁밀도·좌표**

- 데이터셋 ID: **15012005**
- 활용신청: 완료(기존)
- 파라미터: 시도코드 대구 `27` 또는 시군구코드 `27110…27720` `[파라미터명 확인]`
- 역할: 현재 스냅샷·좌표 (시계열은 1-1 인허가가 담당)
- 병행: 분기 전체 CSV(데이터셋 **15083033**)에서 대구 필터 → 시점 스냅샷 적재

### 1-3. 국토부 상업업무용 부동산 매매 실거래가 — **P1**

- 데이터셋 ID: **15126463** / 활용신청: 완료(기존)
- 파라미터:

```
LAWD_CD = 27110 | 27140 | 27170 | 27200 | 27230 | 27260 | 27290 | 27710 | 27720
DEAL_YMD = 201701 … 202608   (월 루프)
```

- ⚠️ 최근 1~2개월은 신고기한(30일) 때문에 미완결

### 1-4. 보조금24 — **P2**

- 데이터셋 ID: **15113968** / 활용신청: 완료(기존) / 변경 없음. 우선순위: 기업마당 > 보조금24

### 1-5. 거리두기 현황 — **P2**

- 데이터셋 ID: **15098772** / 활용신청: 완료(기존)
- 전국 단계 + 2020.2~11 수기 테이블 재사용. 대구 2020.2~3 특별 조치 기간 더미변수 추가 `[보도자료 수기]`

### 1-6. 신규 활용신청 필요 (자동승인 — 당일 가능, D-5에 신청)

| 데이터 | data.go.kr 검색 키워드 | 데이터셋 ID | 용도 |
|---|---|---|---|
| 전통시장 현황 (소진공) | `전통시장 현황` / `전통시장현황 표준데이터` | `[ID 확인]` | 전통시장 좌표·점포수 → "시장 반경 500m" 파생변수 |
| 온누리상품권 가맹점 (소진공) | `온누리상품권 가맹점` | `[ID 확인]` | 전통시장 상권 활성도 프록시 |
| 백년가게 현황 (소진공) | `백년가게` | `[ID 확인]` | 장수 점포 밀도 = 상권 안정성 |
| 나들가게 현황 (소진공) | `나들가게` | `[ID 확인]` | 동네 슈퍼 = 골목상권 지표 |
| 대구교통공사 역별 승하차 | `대구교통공사 승하차` / `대구도시철도 역별` | `[존재·ID 확인]` | 생활인구 프록시. 역→행정동 매핑 필요 |
| 대구광역시 주민등록인구및세대현황 | — | 3077757 | 구·군 단위 (행정동은 §12 파일이 우수) |
| (P2) 국토부 부동산 중개업정보 | — | 15123990 | 부동산중개업 대체 검토 |

---

## 2. 한국부동산원 R-ONE — www.reb.or.kr/r-one

키: `RONE_API_KEY` / **P0~P1** — 임대료·공실률·임대가격지수

- 기존 Metabole 어댑터 재사용: `apps/rent/.../rone_gateway.py`
- 통계표 ID: 서울과 동일 (`A_2024_002xx` / `T24…`) — `_TABLES` 그대로
- 대구 변경점: `CLS_FULLNM`이 `대구>권역>상권` 3계층 → 지역 필터에 `대구` 추가만
- ⚠️ 대구 상권 개수·빈티지별 불연속은 실호출 1회로 확인 `[확인]` — 상권 수가 적으면 구 단위 평균으로 강등

## 3. 한국은행 ECOS — ecos.bok.or.kr

키: `ECOS_API_KEY` / **P0** — 금리 스트레스 테스트 / **변경 없음**

| 통계표 코드 | 내용 |
|---|---|
| `722Y001` | 기준금리 |
| `121Y006` | 예금은행 가중평균 대출금리 |

## 4. 기업마당 — www.bizinfo.go.kr

키: `BIZINFO_API_KEY` / **P0** — 지원사업 공고 → Funding Gap 해결 수단 (RAG 문서 적재)

- 기존 JSON 실호출 어댑터 재사용
- 대구 필터: `hashtags`에 `대구` 포함 + 기관명 `대구광역시`·`대구신용보증재단`·`대구테크노파크`·`대구경북디자인진흥원`
- 추출 필드: 공고명·사업개요·신청기간·소관기관·수행기관·지원대상·hashtags·지역·업종·지원유형 (LLM 구조화 추출 재사용)

## 5. 온통청년 — www.youthcenter.go.kr

키: `YOUTHCENTER_API_KEY` / **P2** — 청년(예비·초기창업)일 때만

- 지역 파라미터 대구 `27` `[파라미터명 확인]`
- 대구시 청년창업 지원사업이 여기서 잡힘. 누락분은 수기 JSON(`daegu_youth_startup.json`)으로 보완

## 6. 네이버 뉴스 검색 — openapi.naver.com

키: `NAVER_NCP_API_KEY_ID` / `NAVER_NCP_API_KEY` / **P1** — 상권 이슈 컨텍스트

- 엔드포인트: `GET https://openapi.naver.com/v1/search/news.json`
- 키워드 세트 교체 (`config/news_keywords_daegu.json`): `동성로 상권`, `서문시장`, `칠성시장`, `대구 자영업`, `대구 소상공인`, `대구로`, `iM뱅크 소상공인` 등
- ⚠️ **소급 불가** — D-5(9/15)부터 즉시 폴링 가동

## 7. 브이월드 — www.vworld.kr

키: `VWORLD_API_KEY` / **P1** — 배경지도·읍면동 경계·주소 검색

- WFS: 레이어 `lt_c_ademd_info` — 대구 읍면동 ~140개 → 1회 호출(1,000피처 한도 내)
- 타일·검색 API 변경 없음
- ⚠️ 지오코더 결과 저장 금지 약관 — 대량 캐싱 불가, 좌표 있는 원천 우선

## 8. KOSIS — kosis.kr

키: `KOSIS_API_KEY` / **P2** — 외국인주민 현황 대구 필터. MVP 필수 아님
- (P0 후보) **소상공인 실태조사 — 업종별 원가율**: 재료비율·인건비율·임차료율·영업이익률 → Finance Engine의 `industry_cost_benchmark`. KOSIS 통계표에서 추출, 없으면 중기부/소진공 발표자료 수기 입력 `[통계표 ID 확인]`

## 9. SGIS — sgis.kostat.go.kr

키: `SGIS_SERVICE_ID` + `SGIS_SECURITY_KEY` / **P3, fallback 전용**

- 용도: 지오코딩 fallback — 담배소매업 등 파일 소스에 좌표가 없을 때 소량 변환, 행정경계 보조
- 브이월드/공간 매핑 이슈 발생 시에만 사용. 평시 호출 없음

## 10. 공정거래위원회 가맹사업 정보공개서 — franchise.ftc.go.kr

**P2** — "예산 N만원이면 어떤 업종?" 역매칭 기능 채택 시에만 (redoceanmap에서 검증된 기능)

- 내용: 브랜드별 창업비용(가맹금·인테리어 등) → 업종별 창업비용 중앙값 산출
- 수급: 공공데이터포털 내 공정위 가맹정보 API 존재 여부 `[확인]`, 없으면 정보공개서 열람 데이터 파일 적재 (redoceanmap은 월 1회 자동 적재로 운용)
- 산출 Feature: `startup_cost_median` (업종별) → 사용자 예산 필터

## 10-1. 금융감독원 금융상품 한눈에 — finlife.fss.or.kr

키: `FSS_FINLIFE_API_KEY` / **P1** — 대출상품 금리를 공식 데이터로 서빙 (할루시네이션 방지)

- 전 은행권(iM뱅크 포함) 정기예금·적금·**개인신용대출·주택담보·전세대출** 상품·금리 공시 API
- 활용: 매칭 결과의 은행 상품 카드에 **실공시 금리** 표기, iM뱅크 상품 금리 검증
- 한계: 가계 금융상품 위주 — **소상공인·개인사업자 전용 상품 커버리지 약함** `[확인]` → 소상공인 상품은 수기 JSON(§13) 유지 + finlife는 금리 보강용
- ⚠️ **신규 키 발급 필요** (무료·즉시) — "신규 키 0개" 원칙의 유일한 예외, P1이므로 여력 시
- 참고: 토스 API는 결제용이라 불필요. iM뱅크(DGB) 오픈API는 제휴 심사 필요 → **제안서 로드맵 기재용** (은행 연계 어필 포인트)

---

## 11. 지역 코드 참조표 (파라미터 값)

대구 9개 구·군 (프로토타입은 군위군 제외 8개):

| 구·군 | `LAWD_CD` (실거래가) | `OPN_ATMY_GRP_CD` (인허가) `[확인]` |
|---|---|---|
| 중구 | 27110 | 3410000 |
| 동구 | 27140 | 3420000 |
| 서구 | 27170 | 3430000 |
| 남구 | 27200 | 3440000 |
| 북구 | 27230 | 3450000 |
| 수성구 | 27260 | 3460000 |
| 달서구 | 27290 | 3470000 |
| 달성군 | 27710 | 3480000 |
| 군위군 | 27720 | `[확인]` |

- 행정동 코드 prefix: `27` / DIP `HCODE`도 행안부 행정동 코드 체계
- 대구 bbox 검증: 경도 128.35~128.77, 위도 35.60~36.02 (좌표 변환 후 95% 이상 포함)

---

## 12. API 아님 — 파일 다운로드

### D-데이터허브 (data.daegu.go.kr) — 로그인·키 불필요

> 목록 페이지가 JS 렌더링이라 크롤링 비권장. 직접검색으로 URL 확보 → 다운로드 → `data/raw/daegu_*/` + MANIFEST.md(SHA256)

| 데이터 | 확인 경로 | 용도 |
|---|---|---|
| 26년07월 대구광역시 담배소매업 | `dataSetId=DMI_0000119426` | 편의점 프록시. 좌표 없으면 SGIS 지오코딩 소량 |
| 먹거리골목 업소정보 | 직접검색 `먹거리골목` | 대구 특화 골목상권 정의 (안지랑곱창·동인동찜갈비·평화시장닭똥집·들안길) |
| 대규모점포 | 직접검색 `대규모점포` | 대형마트·백화점 반경 = 상권 흡수 위험 (운영 중만) |
| 개별공시지가 | 직접검색 `개별공시지가` | 임대료 보완 (필지 → 격자 평균) |
| 삶의지표 > 물가·산업동향 | `/open/status/economyList.do` | 제안서 근거 수치 (수기 인용) |

### 기타 파일

| 데이터 | 출처 | 처리 |
|---|---|---|
| 주민등록 인구 (행정동) | jumin.mois.go.kr → 대구광역시 → 월간 → 전체읍면동현황 CSV | 기존 전국 파일 있으면 대구 필터만 |
| s4u 서비스인구 (SKT) | s4u.daegu.go.kr — **웹 조회만 가능, API 아님** | 대표 상권 5~10곳 화면값 → `data/manual/service_pop_sample.json` ("센터 반출 전 임시값" 라벨) |

---

## 13. API 아님 — 수기 JSON (`data/manual/`) — 금융 매칭의 원천

| 파일 | 내용 | 출처 | 필드 |
|---|---|---|---|
| `imbank_products.json` | iM뱅크 소상공인·개인사업자·청년창업 대출 5~10개 | imbank.co.kr 상품 페이지 `[확인]` | name, target(업력·업종·신용), limit, rate_range, collateral, url |
| `dgsinbo_products.json` | 대구신용보증재단 보증상품 | 대구신보 홈페이지 `[확인]` | name, target, limit, fee_rate, url |
| `daegu_youth_startup.json` | 대구 청년창업 지원사업 (온통청년 누락 보완) | 대구시·대구청년센터 | 기업마당 스키마 동일 |
| `daegu_pay.json` | 대구로페이 가맹 조건·인센티브 | 대구로 앱/대구시 | — |
| `service_pop_sample.json` | s4u 화면 수기 입력 | s4u.daegu.go.kr | dong, resident, worker, visitor |

정규화 스키마(금융상품 공통): `product_id, provider, product_name, target, region, business_age_min/max, category, credit_condition, loan_limit, interest_rate, guarantee_fee, repayment_months, grace_months, documents, source_url, effective_from/to`

### 13-1. 정적 벤치마크·룰 (Finance Engine 입력 — API 아님)

| 항목 | 원천 | 처리 |
|---|---|---|
| 업종별 원가율 (`industry_cost_benchmark`) | 소상공인 실태조사 (KOSIS §8 / 중기부·소진공 발표) | 재료비율·인건비율·임차료율·영업이익률 — 업종별 정적 테이블 |
| 인건비 벤치마크 | 최저임금 고시 (2026년 적용값) | MVP fallback: 최저임금 × 인원 + 사용자 직접입력 우선 |
| 세금/보험 룰 | 부가세·종합소득세·원천세·4대보험 요율, 카드수수료(2~3%)·배달수수료(10~15%) | **Rule 기반 결정론 계산 — LLM 계산 금지** |

---

## 14. 프로토타입 제외 → 본선 로드맵 (DIP 빅데이터활용센터)

> 알파시티 센터 내 분석 후 **결과값만 반출**. 9/28 멘토링(장소=DIP) 당일 반출 스크립트(`scripts/dip_center/`, pandas 단독) 실행 계획.

| 데이터 | 기간 | 반출 집계 |
|---|---|---|
| 삼성카드 / KB국민 / 현대카드 | 2017~2025 (카드사별 상이) | `sales_monthly` (행정동×업종중분류×월, 카드사 구간별 지수화) |
| SKT 생활인구 | 2020.01~2026.07 | `service_pop_monthly` (행정동×월×거주/직장/방문) |
| 대구로 주문 | 2022~2023 | `delivery_share` (행정동×업종×월) |
| 신보 기업 재무 | 2023 | 업종 벤치마크만 (개별 신용평가 사용 금지) |
| 소블럭 shp (8-1) | — | `BLOCK_CD` ↔ 행정동 매핑 — 현대카드·SKT 생활인구의 BLOCK_CD 변환용 (`DMM_BLOCK.shp`, `대구_BLOCK_좌표.CSV`) |
| (P3) 신한카드 관광지 소비 | 2021.01~2024.10 | 동성로·서문시장·수성못·들안길·안지랑 등 핵심상권 Deep Dive 전용 — 메인 소비지표는 삼성카드 |

어댑터 슬롯: 프로토타입 `NullSalesSource`(개폐업률 대체) / `ProxyPopulationSource`(주민등록+승하차) → 본선 전 `DipSalesSource` / `DipPopulationSource` 교체.

---

## 15. D-5 즉시 실행 체크리스트

- [ ] data.go.kr 활용신청 5종: 전통시장·온누리·백년가게·나들가게·대구교통공사 승하차 (§1-6)
- [ ] 네이버 뉴스 대구 키워드 폴링 **즉시 가동** (소급 불가)
- [ ] 인허가 대구 1건 실호출 → `OPN_ATMY_GRP_CD` 실값 확정 → §11 갱신
- [ ] R-ONE 대구 상권 목록 1회 호출 → 상권 수·빈티지 확인

## 16. 검증 게이트 (수집 완료 판정 기준)

- [ ] 인허가: 구·군별 건수 > 0, `CLSBIZ_YMD` 파싱률 확인, 좌표 변환 후 대구 bbox(§11) 내 비율 ≥ 95%
- [ ] 실거래가: 9개 `LAWD_CD` × 최근 12개월 응답 성공률
- [ ] 전통시장: 대구 내 시장 수가 시 공식 통계(약 100여 개)와 대략 일치 `[확인]`
- [ ] 금융 매칭 API: 임의 분석 결과 3케이스에 대해 상품 ≥ 1건 반환
