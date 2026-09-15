# Metabole Daegu — API / Data Migration Plan

> 목적: 기존 **Metabole(서울)** 코드베이스를 최대한 재사용하면서,  
> **대구 소상공인·골목상권 디지털 금융 해커톤용**으로 데이터 소스를 재구성한다.
>
> 핵심 원칙:
> 1. **Metabole Core / Domain 로직은 최대한 유지**
> 2. **서울 전용 Adapter만 대구 Adapter로 교체**
> 3. 공공 API는 실서비스 Backend에 연결
> 4. DIP 민간데이터(삼성카드/SKT/대구로 등)는 별도 수급·가공 후 Feature Store 형태로 연결
> 5. LLM은 수치 계산을 하지 않고, **Deterministic Engine 결과를 해석**
>
> 기준 자료:
> - 기존 Metabole API 수급 계획
> - 공공데이터포털(data.go.kr)
> - D-데이터허브(data.daegu.go.kr)
> - 「대구 빅데이터 활용센터 활용 가능 데이터 설명서 (2026.09)」

---

## 0. 목표 서비스

기존 질문:

> **“이 지역에서 이 업종으로 창업해도 될까?”**

대구/금융 특화 질문:

> **“이 위치에서 이 업종으로 창업하면, 내 자본으로 얼마나 버틸 수 있고 부족한 자금은 얼마인가?”**

최종 분석 흐름:

```text
입지 선택
  ↓
300m 상권환경
  ↓
생활인구 / 소비 / 경쟁 / 개폐업
  ↓
예상 시장규모 / 생존위험
  ↓
임대료 / 인건비 / 원가 / 대출
  ↓
BEP / Runway / Funding Gap
  ↓
정책자금 / 보증 / 금융상품 추천
```

---

# 1. 기존 Metabole에서 그대로 살릴 API

## 1.1 행정안전부 지방행정 인허가 — P0

### 역할
- 개업 이력
- 폐업 이력
- 영업상태
- 업종별 생존기간
- 1년 / 3년 / 5년 생존율
- 지역별 신규진입 / 폐업률

### 기존 구현
공공데이터포털로 2026-04-16 통합.

주요 업종 예시:

| 업종 | data.go.kr ID | slug |
|---|---:|---|
| 일반음식점 | 15154916 | `general_restaurants` |
| 휴게음식점 | 15154921 | `rest_cafes` |
| 미용업 | 15154918 | `beauty_salons` |
| 체력단련장업 | 15155077 | `fitness_centers` |
| 당구장업 | 15155011 | `billiard_halls` |
| 노래연습장업 | 15155135 | `karaoke_rooms` |
| PC방 | 15154951 | `pc_bangs` |

### 엔드포인트 패턴

```text
https://apis.data.go.kr/1741000/{업종슬러그}/{info|history}
```

### 핵심 필드

```text
BPLC_NM
LCPMT_YMD
CLSBIZ_YMD
DTL_SALS_STTS_CD
DTL_SALS_STTS_NM
MNG_NO
LOTNO_ADDR
ROAD_NM_ADDR
CRD_INFO_X
CRD_INFO_Y
BZSTAT_SE_NM
OPN_ATMY_GRP_CD
DAT_UPDT_PNT
```

### 대구판 변경
기존 서울 자치구 필터를 **대구광역시 행정구역 코드**로 교체.

### 구현 추천

```text
apps/licensing/
  domain/
  ports/
  adapters/
    data_go_kr.py
```

기존 Adapter를 그대로 유지하고 지역 필터만 config화.

```python
REGION = "DAEGU"
```

---

## 1.2 소상공인시장진흥공단 상가(상권)정보 — P0

### data.go.kr ID

```text
15012005
```

### 역할
- 현재 영업 중 점포
- 경쟁업체
- 업종 밀도
- 반경 300m / 500m 경쟁점포
- 좌표 기반 공간분석

### 주의
이 데이터는 **현재 스냅샷** 역할로 사용한다.

```text
LOCALDATA = 과거 개폐업
소진공 상가정보 = 현재 경쟁구조
```

### 대구판 변경
없음. 지역 조건만 대구로 변경.

### 신규 Feature

```text
competitor_count_300m
competitor_count_500m
same_category_density
store_per_visitor
category_diversity
```

---

## 1.3 한국부동산원 R-ONE — P0/P1

### 역할
- 상업용 부동산 임대료
- 공실률
- 임대가격지수
- 지역 평균 월세 수준

### 기존 환경변수

```bash
RONE_API_KEY=
```

### 기존 구현 상태
Metabole에서 이미 실호출 및 적재 구현 완료.

```text
apps/rent/
rent_price table
```

### 이번 서비스 역할 변경

기존:

```text
상권 임대료 참고
```

대구판:

```text
사용자 입력 실제 월세
vs
지역 평균 임대료
```

Feature:

```text
rent_burden_index
vacancy_rate
regional_rent_index
```

> 실제 개별 상가 월세 실거래 공공 API는 없음.
> 실제 월세/보증금은 사용자 입력값을 우선 사용.

---

## 1.4 한국은행 ECOS — P0/P1

### 기존 환경변수

```bash
ECOS_API_KEY=
```

### 사용 통계

```text
722Y001  기준금리
121Y006  예금은행 가중평균 대출금리
```

### 역할
- 금융비용 계산
- 대출 스트레스 테스트
- 금리 상승 시 Runway 변화

### Feature

```text
base_rate
avg_loan_rate
interest_cost
interest_stress_1p
interest_stress_2p
```

### 예시

```text
현재 Runway = 9.4개월
금리 +1%p = 8.8개월
금리 +2%p = 8.2개월
```

---

## 1.5 기업마당 지원사업 공고 — P0

### 기존 환경변수

```bash
BIZINFO_API_KEY=
```

### 기존 호출
기존 Metabole에서 JSON 실호출 검증 완료.

### 역할
기존:

```text
정부지원사업 검색
```

대구판:

```text
Funding Gap 해결 수단 추천
```

### 추출 필드

```text
공고명
사업개요
신청기간
소관기관
수행기관
지원대상
hashtags
지역
업종
지원유형
```

### 필터 예시

```text
지역 = 대구
대상 = 소상공인 / 예비창업자
업종 = 사용자 업종
상태 = 모집중
```

### 구현
RAG용 Document Store로 적재.

---

## 1.6 브이월드 — P1

### 기존 환경변수

```bash
VWORLD_API_KEY=
```

### 역할
- 배경지도
- 읍면동 경계
- 주소/지역 검색
- 지도 UX

### 주의
브이월드 Geocoder 결과는 저장 제한 이슈가 있으므로,
**좌표 DB 구축용으로 대량 캐싱하지 않는다.**

좌표가 있는 원천데이터 우선 사용.

---

## 1.7 주민등록 인구 — P1

### 기존 상태
기존 Metabole에서 전국 읍면동 단위 CSV 확보 및 적재 구조 존재.

### 역할
SKT 생활인구와 비교하는 **거주 기반 baseline**.

Feature:

```text
registered_population
service_population
daytime_population_ratio
visitor_dependency
```

예:

```text
주민등록인구 12,000
SKT 생활인구 31,000
→ 외부 유입형 상권
```

---

# 2. 조건부로 살릴 기존 API

## 2.1 온통청년 — P2

기존 환경변수:

```bash
YOUTHCENTER_API_KEY=
```

조건:

```text
청년 + 예비창업 / 초기창업
```

일 때만 사용.

역할:

```text
청년 창업지원
청년 정책자금
청년 보조사업
```

---

## 2.2 보조금24 — P2

data.go.kr ID:

```text
15113968
```

기업마당에서 못 잡는 공공혜택 보완.

우선순위:

```text
기업마당 > 보조금24
```

---

## 2.3 KOSIS — P2

기존 환경변수:

```bash
KOSIS_API_KEY=
```

역할:
- 지역경제
- 가구
- 외국인주민
- 사업체통계
- 인구통계 보완

MVP에서는 필수 아님.

---

## 2.4 SGIS — P3 / Fallback

역할:
- 행정경계
- 지오코딩 fallback
- 통계지리

브이월드 또는 공간 매핑 이슈 발생 시 사용.

---

## 2.5 국토부 상업업무용 부동산 매매 실거래가 — P2

data.go.kr ID:

```text
15126463
```

역할:

```text
상업용 부동산 매매가격 참고
```

이번 금융 MVP에서 월세보다 중요도 낮음.

---

## 2.6 네이버 검색/뉴스 — P3

기존 환경변수:

```bash
NAVER_NCP_API_KEY_ID=
NAVER_NCP_API_KEY=
```

역할:
- 지역 이벤트
- 상권 이슈
- 외부 충격
- 뉴스 기반 Context

MVP에서는 비활성화 가능.

---

# 3. 서울 전용 데이터 — 제거 / 교체

| 기존 서울 데이터 | 처리 | 대구 대체 |
|---|---|---|
| 서울시 상권분석 추정매출 | 제거 | 삼성카드 소비 |
| 서울 생활인구 | 제거 | SKT 생활인구 |
| 서울 지하철 | 제거 | 대구 도시철도 |
| 서울 학원·교습소 | 제거 | 필요 시 대구 교육 데이터 |
| 서울신보 보증상품 | 제거 | 대구신용보증재단 |
| 서울 상권영역 | 제거 | DIP Grid + 대구 행정동 |

---

# 4. 신규 대구 핵심 데이터

> 중요: 아래 DIP 데이터는 일반 Open API라고 가정하지 않는다.
> 데이터 활용센터 이용/반출 정책에 따라 **사전 집계 Feature 또는 정적 파일 적재** 방식으로 구현한다.

---

## 4.1 삼성카드 소비 데이터 — 신규 P0

### 기간

```text
2024.01 ~ 2025.12
```

### 공간

```text
대구 전역
행정동 단위
```

### 주요 컬럼

```text
기준년월
가맹점_광역시도
가맹점_시군구
가맹점_행정동
내외지인
성별
연령대
직업군
업종명_대분류
업종명_중분류
WEEK_GROUP
WEEKEND_GROUP
CNT
AMT
```

### 내외지인

```text
01 = 대구 거주
02 = 경북 거주
03 = 대구/경북 외 거주
```

### Feature

```text
category_sales
category_transactions
avg_ticket = AMT / CNT
weekday_sales_ratio
weekend_sales_ratio
local_customer_ratio
gyeongbuk_customer_ratio
outside_customer_ratio
age_segment_share
gender_share
occupation_share
```

### 핵심 파생변수

```text
Opportunity Index
= 업종 소비액 / 동일업종 점포수
```

---

## 4.2 SKT 생활인구 — 신규 P0

### 기간

```text
2020.01 ~ 2026.07
```

### 핵심 구분

```text
H = 거주인구
W = 직장인구
V = 방문인구
```

### 공간 단위
- 행정동
- 소블록
- 좌표 포함

### 제공 정보
- 성별
- 연령
- 00~23시
- 유입지역
- 외국인 국적

### 핵심 Feature

```text
resident_population
worker_population
visitor_population
hourly_visitor_population
age_segment_population
visitor_ratio
worker_ratio
day_night_population_ratio
```

### 소비 결합

```text
Consumption Efficiency
= 카드 소비액 / 방문인구
```

---

## 4.3 DIP 100m / 300m / 500m 공간 데이터셋 — 신규 P0

### 추천 기본 단위

```text
300m
```

> 100m/500m도 보유하되, MVP default는 300m.

### 포함 가능 데이터 예시
- 소상공인 상가정보
- 대규모점포
- 병원
- 약국
- 주차장
- CCTV
- 건축물
- 공시지가
- 체육시설
- 취약계층 인구

### 핵심 Feature

```text
same_category_store_count_300m
all_store_count_300m
parking_count_300m
large_retail_count_300m
hospital_count_300m
public_land_price_mean_300m
building_density_300m
```

### 구조

```text
point
  ↓
grid_300m
  ↓
administrative_dong
  ↓
district
  ↓
Daegu
```

---

## 4.4 대구 도시철도 — P1

가능하면 최신 공공데이터포털 자료 사용.

Feature:

```text
station_distance
daily_boarding
daily_alighting
peak_hour_population
subway_accessibility_score
```

역세권인 경우만 가중치 적용.

---

## 4.5 대구로 — 외식업 P0 / 일반업종 P3

### 제공
- 고객
- 가맹점
- 주문일시
- 결제
- 할인
- 조리대기
- 취소
- 배달팁
- 리뷰
- 별점

### 외식업 Feature

```text
delivery_order_count
delivery_sales
avg_delivery_ticket
repeat_order_ratio
cancellation_rate
avg_delivery_tip
avg_rating
delivery_peak_hour
```

### 서비스 역할

```text
삼성카드 = 오프라인 소비
대구로 = 배달 소비
```

---

## 4.6 현대카드 과거 소비 — P2

기간:

```text
2017 ~ 2022.08
```

사용 목적:

```text
과거 상권 패턴
코로나 충격
장기 상대 변화
```

주의:

```text
삼성카드와 절대금액 직접 연결 금지
```

카드사별 점유율/전수화 방식이 달라,
변화율/상대지수 중심으로 사용.

---

## 4.7 신한카드 관광지 소비 — P3

기간:

```text
2021.01 ~ 2024.10
```

대구 전역이 아닌 지정 관광/핵심상권 중심.

사용:
- 동성로
- 서문시장
- 수성못
- 들안길
- 안지랑
등 Deep Dive 용.

메인 소비데이터는 삼성카드 사용.

---

## 4.8 신용보증기금 대구 기업 재무 — P1/P2

### 주요 컬럼

```text
업종
종업원수
총자산
부채
자기자본
매출액
영업이익
당기순이익
EBITDA
각 산업평균
```

### 용도
개별 소상공인 신용평가에 직접 사용하지 말 것.

```text
업종 재무 Benchmark
```

로 사용.

---

# 5. 추가 확보가 필요한 데이터

## 5.1 소상공인 업종별 원가율 — P0

필요한 값:

```text
재료비율
인건비율
임차료율
영업이익률
```

후보 출처:
- KOSIS
- 소상공인 실태조사
- 서비스업 조사
- 중기부/소진공 통계

구현:

```text
industry_cost_benchmark
```

---

## 5.2 인건비 Benchmark — P0/P1

필요:

```text
지역
업종
직종
평균임금
```

MVP fallback:

```text
최저임금 + 사용자 직접입력
```

---

## 5.3 실제 금융상품 — P0

반드시 추가:

```text
iM뱅크 소상공인 상품
대구신용보증재단
소진공 정책자금
대구시 정책자금
```

Normalized Schema:

```text
product_id
provider
product_name
target
region
business_age_min
business_age_max
category
credit_condition
loan_limit
interest_rate
guarantee_fee
repayment_months
grace_months
documents
source_url
effective_from
effective_to
```

API가 없으면 RAG 문서 적재.

---

## 5.4 세금/보험 Rule Engine — P1

필요:

```text
부가세
종합소득세
원천세
4대보험
카드수수료
```

LLM 계산 금지.

Rule 기반 계산.

---

## 5.5 사용자 입력 Schema — P0

```json
{
  "location": {},
  "business_category": "",
  "owner_age": null,
  "is_pre_startup": true,
  "equity": 0,
  "deposit": 0,
  "monthly_rent": 0,
  "key_money": 0,
  "interior_cost": 0,
  "equipment_cost": 0,
  "working_capital": 0,
  "employee_count": 0,
  "monthly_payroll": 0,
  "cost_ratio": null,
  "existing_debt": 0,
  "desired_loan": 0
}
```

---

# 6. Unified Business Taxonomy — 반드시 신규 구현

각 데이터 업종체계가 다르다.

```text
삼성카드 업종
소진공 상권업종
LOCALDATA 인허가 업종
KSIC
대구로 자체분류
```

따라서 내부 공통 Category 필요.

## 추천 구조

```text
metabole_category
  ├─ food_restaurant
  ├─ cafe
  ├─ bar
  ├─ beauty
  ├─ fitness
  ├─ academy
  ├─ convenience
  └─ ...
```

Mapping Table:

```text
source
source_category_code
source_category_name
metabole_category
confidence
manual_verified
```

---

# 7. Feature Store 추천

## 7.1 Market Feature

```text
region_id
grid_id
dong_code
category

resident_population
worker_population
visitor_population
category_sales
category_transactions
avg_ticket

same_category_store_count
new_openings_12m
closures_12m
survival_1y
survival_3y
survival_5y

rent_index
vacancy_rate
```

---

## 7.2 Derived Feature

```text
market_demand_index
consumption_efficiency
opportunity_index
competition_pressure
survival_risk
rent_burden_index
financial_resilience
```

---

# 8. 계산 엔진

LLM이 숫자를 만들지 않는다.

## 8.1 Market Engine

```text
Demand
Competition
Survival
```

## 8.2 Finance Engine

```text
Expected Revenue
Gross Profit
Fixed Cost
Operating Profit
BEP
Cash Burn
Runway
Funding Gap
Debt Service
Stress Test
```

## 8.3 AI Agent

입력:

```text
Feature Store 결과
Finance Engine 결과
정책/금융 RAG
```

출력:

```text
왜 위험한지
어떤 변수가 문제인지
무엇을 바꾸면 되는지
대체 입지
비용절감
자금조달
지원사업
```

---

# 9. 추천 Adapter 구조

```text
apps/
├── licensing/
│   └── adapters/
│       └── data_go_kr.py
│
├── stores/
│   └── adapters/
│       └── semas.py
│
├── population/
│   ├── adapters/
│   │   ├── resident_population.py
│   │   └── daegu_skt.py          # 신규
│
├── sales/
│   ├── adapters/
│   │   ├── daegu_samsung.py      # 신규
│   │   ├── daegu_hyundai.py      # 옵션
│   │   └── daegu_shinhan.py      # 옵션
│
├── grid/
│   └── adapters/
│       └── daegu_grid.py         # 신규
│
├── rent/
│   └── adapters/
│       └── rone.py
│
├── finance/
│   ├── adapters/
│   │   ├── ecos.py
│   │   ├── imbank.py             # 신규
│   │   └── daegu_credit_guarantee.py
│   └── engine/
│       ├── bep.py
│       ├── runway.py
│       └── stress.py
│
├── policy/
│   └── adapters/
│       ├── bizinfo.py
│       ├── subsidy24.py
│       └── youthcenter.py
│
├── taxonomy/
│   └── business_category_mapper.py
│
└── map/
    └── adapters/
        └── vworld.py
```

---

# 10. 환경변수 정리

기존 `.env`에서 유지:

```bash
# 공공데이터포털
DATA_GO_KR_API_KEY=

# VWorld
VWORLD_API_KEY=

# R-ONE
RONE_API_KEY=

# ECOS
ECOS_API_KEY=

# 기업마당
BIZINFO_API_KEY=

# 온통청년
YOUTHCENTER_API_KEY=

# KOSIS
KOSIS_API_KEY=

# 네이버 (optional)
NAVER_NCP_API_KEY_ID=
NAVER_NCP_API_KEY=
```

추가 예정:

```bash
# 실제 API 존재 여부 확인 후 추가
IMBANK_API_KEY=
DAEGU_CREDIT_GUARANTEE_API_KEY=
```

> DIP 민간데이터는 API Key 방식이라고 가정하지 말 것.

---

# 11. 구현 우선순위

## Phase 1 — 기존 코드 재사용

- [ ] `licensing` 지역필터 서울 → 대구 config화
- [ ] `stores` 대구 조회 검증
- [ ] `rent` R-ONE 대구 상권 데이터 확인
- [ ] `ecos` 그대로 사용
- [ ] `policy` 기업마당 그대로 사용
- [ ] `map` VWorld 대구 경계 검증

## Phase 2 — 대구 Adapter

- [ ] `daegu_skt` importer
- [ ] `daegu_samsung` importer
- [ ] `daegu_grid` importer
- [ ] 대구 도시철도 importer
- [ ] 대구로 importer(optional)

## Phase 3 — 통합

- [ ] Unified Business Taxonomy
- [ ] 행정동 코드 정규화
- [ ] 좌표계 정규화
- [ ] grid ↔ 행정동 mapping
- [ ] category crosswalk

## Phase 4 — 금융 엔진

- [ ] 업종별 원가 benchmark
- [ ] 인건비
- [ ] 사용자 월세/보증금
- [ ] BEP
- [ ] Runway
- [ ] Funding Gap
- [ ] 금리 Stress Test

## Phase 5 — 금융/정책 RAG

- [ ] iM뱅크 상품
- [ ] 대구신용보증재단
- [ ] 소진공 정책자금
- [ ] 대구시 지원사업
- [ ] 기업마당
- [ ] 온통청년(optional)

## Phase 6 — 검증

- [ ] 과거 시점 Feature 생성
- [ ] 다음 12/24개월 폐업 여부 Label 생성
- [ ] Survival Risk Back-test
- [ ] 지역별 calibration
- [ ] 설명가능성 점검

---

# 12. Codex 작업 지시용 요약

Codex에게 먼저 아래 순서로 작업시킨다.

```text
1. 현재 Metabole repository에서
   - licensing
   - stores
   - rent
   - ecos
   - policy
   - map
   관련 모듈을 찾아라.

2. 서울 전용 조건이 하드코딩된 부분을 찾아
   RegionConfig 또는 Adapter config로 분리하라.

3. 기존 Domain / Port 인터페이스는 최대한 유지하고
   Daegu Adapter만 추가하라.

4. 신규 Adapter:
   - DaeguSktPopulationAdapter
   - DaeguSamsungSalesAdapter
   - DaeguGridAdapter
   를 기존 Hexagonal Architecture 규칙에 맞춰 설계하라.

5. 모든 외부 데이터는 raw → normalized → feature
   3단계 파이프라인으로 분리하라.

6. LLM이 금액/점수를 직접 계산하지 않도록
   Finance Engine과 Feature Engine은 deterministic module로 구현하라.

7. 기존 테스트를 깨지 말고,
   신규 Daegu Adapter unit test와 integration test를 추가하라.
```

---

# 13. 최종 데이터 역할

```text
[사람]
SKT 생활인구
    ↓

[돈]
삼성카드
    ↓

[경쟁]
소진공 상가정보
    ↓

[생존]
행정안전부 인허가
    ↓

[입지]
DIP 300m Grid
    ↓

[비용]
R-ONE + 사용자 입력 + 원가/인건비
    ↓

[금융]
ECOS + iM뱅크 + 대구신보
    ↓

[지원]
기업마당 + 정책자금
    ↓

[의사결정]
BEP / Runway / Funding Gap / Survival Risk
```

---

# 14. 현재 기준 결론

## 그대로 재사용

```text
행정안전부 인허가
소진공 상가정보
R-ONE
ECOS
기업마당
VWorld
주민등록인구
```

## 조건부 재사용

```text
온통청년
보조금24
KOSIS
SGIS
국토부 실거래
네이버 뉴스
```

## 대구 데이터로 교체

```text
서울 생활인구
→ SKT 생활인구

서울 추정매출
→ 삼성카드 소비

서울 지하철
→ 대구 도시철도

서울신보
→ 대구신용보증재단
```

## 신규 핵심

```text
DIP 300m Grid
iM뱅크 금융상품
대구신용보증재단 상품
업종별 원가/인건비 Benchmark
Unified Business Taxonomy
Finance Engine
```
