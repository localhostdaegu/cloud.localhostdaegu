# 수기 금융상품 JSON 실값 조사 (초안)

- 확인 일자: 2026-09-17 (모든 항목 동일)
- 상태: **초안**. 운영 파일 `data/manual/*.json`은 바꾸지 않았다. 사용자 확인 후 반영한다.
- 반영(2026-09-17): §5 질문 1·2·4·6 사용자 결정대로 운영 파일에 반영(null 금리는 카드에서 "은행별 상이", youth-3/4 현 위치 유지, 전국 상품 포함, 업종 id 통일). 질문 3은 youth-1 `[]` 유지, 질문 5는 matcher가 `owner_age` 미수집 시 연령 조건을 건너뛰도록 수정, 질문 7은 범위 밖. 최종 리뷰 후속: matcher에 지역 필터가 없어 달성군 한정 dgsinbo-5가 중구 등 대구 전역에 추천되던 문제 → youth-1과 같이 `category: []`로 매칭 제외(구·군 특례보증은 범위 밖 — 사용자 결정).
- 제안 파일: 이 폴더의 `imbank_products.json`(3건), `dgsinbo_products.json`(5건), `daegu_youth_startup.json`(4건). 합계 12건.

## 1. 스키마와 매칭 로직

### 1-1. 누가 읽는가

| 위치 | 역할 |
|---|---|
| `backend/apps/matching/adapter/outbound/gateways/manual_product_gateway.py` | `<repo>/data/manual/` 아래 3개 파일명을 하드코딩해 읽는다. 필수 키 15개가 있는지만 검사한다(타입·enum 검사 없음). `lru_cache`라 서버 재시작 전까지 캐시가 유지된다 |
| `backend/apps/matching/domain/matcher.py` | 필터 + 정렬 |
| `backend/apps/matching/adapter/inbound/api/v1/matching_router.py` | `GET /matching?funding_gap&category&business_age_months&owner_age` |
| `frontend/src/features/simulator/components/matching-cards.tsx` | 카드 표시: provider_type 배지, product_name, provider, `한도 {loan_limit} · 금리 {interest_rate}%`, `url` 링크 |

로더는 `data/manual` 경로만 읽고 `docs/research/`는 읽지 않는다(grep로 확인, 다른 참조 없음).

### 1-2. 필드별 사용처

| 필드 | 타입(현재 파일 기준) | matcher | 프론트 | 제안 파일 기입 원칙 |
|---|---|---|---|---|
| product_id | str | - | key | `imbank-N`/`dgsinbo-N`/`youth-N` 유지 |
| provider | str | - | 표시 | 기관명 |
| provider_type | `guarantee`/`bank`/`policy` | 정렬 우선순위(보증→은행→정책). 다른 값이면 KeyError | 배지 | 파일별 고정 |
| product_name | str | - | 표시 | 공식 상품명 |
| target | str | - | 미표시 | 대상 요건 요약(원문 수치) |
| region | str | - | 미표시 | 대구/구·군/전국 |
| business_age_min | int(개월) | 업력 < min 이면 제외. null이면 통과 | number 타입 | 하한 없으면 0 |
| business_age_max | int(개월)/null | 업력 > max 이면 제외 | | "N년 미만" → N×12−1, "N년 이내" → N×12 |
| category | list[str]/null | null이면 전 업종 통과, list면 `category in list` | | **업종 id**(`restaurant`, `cafe` 등). 아래 주의 참고 |
| owner_age_max | int/null | owner_age가 None이면 **제외** | | 만 나이 상한 |
| loan_limit | int(원)/null | limit < funding_gap 이면 제외. null이면 통과 | number 타입, 표시 | 보증상품은 보증금액 한도, 정책자금은 융자추천 한도 |
| interest_rate | float(%) | - | `금리 {값}%` 표시 | 고정·단일 수치가 공시된 경우만 기입, 변동·은행 결정이면 null |
| guarantee_fee | float(%) | - | 미표시 | 보증료율. 미공시면 null |
| url | str | - | "상세 보기" 링크 | 상품 상세/공고 페이지 |
| source_url | str | - | 미표시 | 값을 확인한 출처 |

주의할 점(코드 수정은 하지 않았다):
- **category 코드 불일치**: 운영 파일 `imbank-1`의 `["general_restaurants", ...]`는 행안부 인허가 원천 코드다. 프론트는 URL `industry` 값(`restaurant`, `cafe` 등 `frontend/src/shared/industries.ts`)을 그대로 넘긴다. 그래서 지금 이 상품은 어떤 업종에도 매칭되지 않는다. 제안 파일은 업종 id 기준으로 쓴다.
- **프론트 호출 조건**: `fetchMatching`은 `business_age_months=0`으로 고정하고 `owner_age`를 보내지 않는다. 그 결과 `owner_age_max`가 있는 상품(youth-1, youth-2)과 `business_age_min>0`인 상품(imbank-3)은 화면에 나오지 않는다.
- **null 표시 문제**: 프론트 타입은 `loan_limit/interest_rate/guarantee_fee: number`다. `interest_rate`가 null이면 카드에 "금리 null%"가 찍힌다. 제안 파일은 지시대로 미확인 값을 null로 뒀으므로 반영 전에 표시 방식을 결정해야 한다(§5 질문 1).

## 2. 상품 표

### 2-1. iM뱅크 (`imbank_products.json`, provider_type=bank)

| id | 상품 | 한도 | 금리 | 보증료 | 대상·기간 | 출처 |
|---|---|---|---|---|---|---|
| imbank-1 | 소상공인시장진흥공단 정책자금 (운전자금) | 1억원 | 기준금리(소진공 분기 고시) + 가산 − 우대. 페이지 표기 "2026년 2/4분기 기준금리 3.44%" → **null** | 기관별 상이 → **null** | 소진공 추천 기업. 업력은 자금유형별(청년고용연계: 업력 3년 미만·만39세 이하 등). 5년(거치 2년), 원금 70% 3개월 균등·30% 만기 | [iM뱅크 상품 페이지](https://www.imbank.co.kr/cms/fnm/loan/product/giup/01/sda_41216/1221451_5612.html) (심의필 제26-1052호, 2026.04.23~2028.03.31) |
| imbank-2 | 같은 상품 (시설자금) | 5억원 | 위와 같음 → null | null | 8년(거치 3년) | 위와 같음 |
| imbank-3 | 소상공인 성장촉진 보증대출 | 개인사업자 5천만원 (법인 1억원) | 우대만 명시, 수치 미공개 → **null** | 0.8% (대구신보 상품 페이지) | 업력 1년 이상, 개인신용평점 710점 이상, 경쟁력 강화 계획 입증. 지역신보 90% 보증. 2025-11-07~한도 소진 | [매일신문 2025-11-30](https://www.imaeil.com/page/view/2025113013422798725), [대구신보 gdsNo=34](https://www.dgsinbo.or.kr/page/10039/10043.tc?pageDtlOrdrNo=1&importUrl=/guaranteegoods/detail.tc&gdsNo=34) |

운전/시설을 두 건으로 나눈 이유: 한도 차이(1억/5억)가 funding_gap 필터에 직접 걸리기 때문이다.

### 2-2. 대구신용보증재단 (`dgsinbo_products.json`, provider_type=guarantee)

모두 [대구신보 보증상품 소개](https://www.dgsinbo.or.kr/page/10039/10043.tc)에서 2026-09-17 기준 "지원가능"으로 확인했다. 대출금리는 전부 취급은행이 정하므로 `interest_rate`는 null로 뒀다.

| id | 상품 | 보증한도 | 보증료 | 대상 | 기간·상환 | 출처 |
|---|---|---|---|---|---|---|
| dgsinbo-1 | 대구형 창업·성장 플러스 특별보증 (2026) | 기업당 1억원 | 0.9% | Track1 보증잔액 없음 또는 업력 3년 미만 / Track2 업력 3년+ 성장 / Track3 성실상환 | 2026-01-02~한도 소진, 6,000억원. 5년(1년 거치) 또는 1년 일시 | [gdsNo=35](https://www.dgsinbo.or.kr/page/10039/10043.tc?pageDtlOrdrNo=1&importUrl=/guaranteegoods/detail.tc&gdsNo=35) |
| dgsinbo-2 | 대구형 전통시장·골목상권 활력 특별보증 (2026) | 1억원 | 0.9% | 전통시장·상점가·골목형상점가·상권활성화구역 소재 | 2026-01-02~, 500억원. 대구시 경영안정자금 연계 시 이차보전 2%(1년) | [gdsNo=36](https://www.dgsinbo.or.kr/page/10039/10043.tc?pageDtlOrdrNo=1&importUrl=/guaranteegoods/detail.tc&gdsNo=36), [2026 경영안정자금 변경 공고](https://www.dgsinbo.or.kr/page/10065/10006.tc?pageDtlOrdrNo=1&&boardNo=84527&boardMngNo=2&importUrl=%2Fboard%2Fview.tc) |
| dgsinbo-3 | 유망 예비창업자 사전보증 | 교육·컨설팅 이수자 5천만원 / IP 사업화 7천만원 | 0.8% | 6개월 내 창업 예정 예비창업자, NICE 755 또는 KCB 670 이상 | 2022-09-01~한도 소진 | [gdsNo=5](https://www.dgsinbo.or.kr/page/10039/10043.tc?pageDtlOrdrNo=1&importUrl=/guaranteegoods/detail.tc&gdsNo=5) |
| dgsinbo-4 | 금융기관 특별출연 중소기업·소상공인 금융지원 협약보증 | 4억원 | 0.9% | 대구 사업자등록 소상공인·중소기업 | 상시. 1년 일시 또는 5년(1년 거치) | [gdsNo=30](https://www.dgsinbo.or.kr/page/10039/10043.tc?pageDtlOrdrNo=1&importUrl=/guaranteegoods/detail.tc&gdsNo=30) |
| dgsinbo-5 | 2026 달성군 소상공인 경영안정자금 지원 특례보증 | 고·중신용 3천만원 / 저신용 1천만원 | 0.8% 고정 | 달성군 소재 소상공인. 달성군이 이자 2%를 2년 지원 | 2026-01-22 접수 개시, 120억원 | [뉴스핌 2026-01-16](https://www.newspim.com/news/view/20260116000791) |

dgsinbo-3: 사업자등록 전 단계라 `business_age_min=0, max=0`으로 뒀다. `loan_limit`은 기본 트랙인 5천만원이다.

### 2-3. 대구 청년·창업 정책자금 (`daegu_youth_startup.json`, provider_type=policy)

| id | 사업 | 한도 | 금리/이차보전 | 대상 | 연도 | 출처 |
|---|---|---|---|---|---|---|
| youth-1 | 북구 청년창업 특례보증 | 5천만원 (제조업 7천만원) | 대출금리 금융채 12M + 1.5% (변동 → **null**), 북구 이자지원 연 2%·2년 | 북구 소재 제조업·지식서비스업, 만19~39세, 창업 5년 이내, 신용 595+ | **2025년 공고** (2026 공고 미확인) | [기업마당 2025 공고](https://www.bizinfo.go.kr/web/lay1/bbs/S1T122C128/AS/74/view.do?pblancId=PBLN_000000000105652), [서울경제TV 2025-03-01](https://www.sentv.co.kr/article/view/sentv202503010027) |
| youth-2 | 청년전용창업자금 (중진공) | 1억원 (제조·지역특화 2억원) | **2.5% 고정** | 만39세 이하, 업력 3년 미만(예비창업자 포함) | 정부24 최종수정 2026-08-14 | [정부24](https://www.gov.kr/portal/service/serviceInfo/142000000099) |
| youth-3 | 2026 대구시 경영안정자금 일반창업기업 지원자금 | 융자추천 5억원 (연매출 1/2 내) | 대출금리는 은행 결정(보증서 85%+ 담보 시 1년간 5.5% 이하) → null. 이차보전 1년: 5천만원 이하 1.8/2.0/2.2%, 초과 1.3/1.5/1.7%, 청년(만34세 이하)+간이과세자 +0.2%, 고용 1~4인 +0.2% | 대구 소재 업력 7년 미만 중소기업 | 2026 (9/16 변경 공고, 9/21 시행) | [대구신보 공지 + 첨부 공고문(대구광역시공고 제2026-1259호)](https://www.dgsinbo.or.kr/page/10065/10006.tc?pageDtlOrdrNo=1&&boardNo=84527&boardMngNo=2&importUrl=%2Fboard%2Fview.tc) |
| youth-4 | 2026 대구시 경영안정자금 소상공인 지원자금 | 1억원 | youth-3과 같은 이차보전표 | 연매출 5억원 이하 소상공인 | 2026 | 위와 같음 |

youth-1의 `category=[]`: 대상이 제조업·지식서비스업인데, 서비스 업종 11종(카페·음식점·편의점·미용실·노래방·PC방·헬스장·당구장·부동산중개·학원·어린이집) 중 어느 것이 해당되는지 확인하지 못했다. null이면 카페까지 통과하므로 빈 리스트로 막아 두었다(§5 질문 3).

youth-3/4는 청년 전용이 아니다. 다만 대구시 창업 이차보전의 핵심 자금이고 policy 타입 상품을 담을 파일이 이것뿐이라 여기에 넣었다.

## 3. 확인하지 못한 값 (null 처리)

| id | 필드 | 사유 |
|---|---|---|
| imbank-1, imbank-2 | interest_rate | 분기 변동(기준금리+가산−우대). 공시는 2026 2/4분기 기준금리 3.44%뿐이고 최종 금리 수치는 없다. 3/4분기 3.85%라는 블로그 글이 있지만 1차 출처로 확인하지 못했다 |
| imbank-1, imbank-2 | guarantee_fee | "신용보증기관 이용 시 고객 부담(기관별 상이)" |
| imbank-3 | interest_rate | "금리 우대"라고만 적혀 있고 수치가 없다 |
| dgsinbo-1~5 | interest_rate | 보증상품이라 대출금리는 취급은행이 정한다 |
| youth-1 | interest_rate, guarantee_fee | 금리는 금융채 연동 변동. 보증료는 공고 요약에 없다(원문 첨부 미확인) |
| youth-2 | guarantee_fee | 중진공 직접대출이라 보증료 개념이 있는지 확인하지 못했다 |
| youth-3, youth-4 | interest_rate, guarantee_fee | 금리는 은행이 정하고, 보증료는 담보 종류(재단/신보/기보/부동산)에 따라 다르다 |

그 밖의 불확실 사항:
- imbank-3의 한도: iM뱅크 보도자료는 "개인 5천만원·법인 1억원", 대구신보 상품 페이지는 "같은기업당 총보증금액 8억원 이내"다. 개인사업자 기준 5천만원을 채택했다.
- youth-1은 2025년 공고다. 2026년에도 하는지는 확인하지 못했다(북구청 일자리정책과 053-665-2666 / 대구신보 북지점 053-601-5255).
- dgsinbo-5의 `url`: 개별 공고 페이지를 찾지 못해 대구신보 메인으로 뒀다.
- 달서구(96억)·중구(30억, 3천만원)·수성구(5천만원, 이자 3% 2년)·남구·서구·동구 2026 특례보증은 검색 요약에만 나오고 1차 출처로 확인하지 못해 제외했다.
- 대구시 청년정책 포털(daegu.go.kr/YouthPolicy)은 정책 목록을 JS로 불러와 융자 항목을 뽑지 못했다.

## 4. 조사했지만 제외한 후보

| 후보 | 제외 사유 |
|---|---|
| iM뱅크 대구광역시 상생전통시장 특례보증대출 (4억, 보증료 0.9%) | 판매기간 2024.04.17~2026.04.16 종료 |
| iM뱅크 대구광역시 따뜻한 금융지원 특례보증대출 (창업 7년 이내, 2억, 0.9%) | 심의필 유효기간 2023.04.06~2025.04.05 경과, 금리 기준일 2023. 현재 목록에 없음 |
| iM뱅크 SOHO 이로운 특별대출 (5.80~8.74%, CSS 4등급+) | 심의필 2023.05.26~2025.05.25 경과, 금리 기준일 2023.05.23. 현재 소상공인 상품 목록에 없음 |
| iM뱅크 신용보증재단 희망플러스 특례보증 대출 | 2022년 방역지원금 대상 상품, 유효기간 경과 |
| iM뱅크 국세 성실납세 사업자 특별대출 | 경상북도 소재 기업 대상 |
| iM뱅크 탑티어 전문직·착한 건물주 특별대출 | 전문직·부동산임대업 대상이라 서비스 업종과 무관 |
| 대구신보 기업가형 소상공인 육성 협약보증 (4억, 0.8%) | 로컬크리에이터·백년가게 등 선정기업 한정, 국민은행 취급 |
| 대구신보 골목상권 살리기·프랜차이즈 가맹점 협약보증 (0.9%) | 한도 미기재, 기업은행 취급 |
| 대구신보 대구 중소기업 시설및 경쟁력 강화 특례보증 | 소상공인 제외 |
| 대구시 경영안정자금 유망창업·기술형창업 자금 | 신보·기보 보증서 담보(10억 한도). 서비스 소상공인보다 기술·유망창업 대상이라 이번 초안에서는 뺐다. 필요하면 추가 가능 |
| "2026년도 청년창업특례보증 지원계획 공고" (기업마당 첨부) | 열어 보니 **광주광역시** 공고였다(대구 아님) |

## 5. 반영 전 확인할 질문

1. **null 표시**: 프론트 카드가 `금리 {interest_rate}%`를 그대로 찍는다. null을 허용하고 프론트에서 "금리 은행별 상이"로 표시할까, 아니면 JSON에 대표 수치(예: 보증서 담보 상한 5.5%)를 넣을까?
2. **youth-3/4 배치**: 청년 전용이 아닌 대구시 경영안정자금을 `daegu_youth_startup.json`에 둬도 될까? 아니면 파일 역할을 "대구 정책자금"으로 넓힐까?
3. **youth-1 업종**: 북구 청년창업 특례보증(제조업·지식서비스업)을 11개 업종 중 어디에 열어 둘까? 예를 들어 `academy`를 지식서비스로 볼지. 지금은 `[]`로 매칭에서 빠진다.
4. **전국 상품 포함 여부**: 중진공 청년전용창업자금(youth-2)과 소진공 정책자금(imbank-1/2)은 대구 전용이 아니다. 넣어도 될까?
5. **프론트 호출 조건**: `business_age_months=0` 고정과 `owner_age` 미전송 때문에 청년 상품(youth-1/2)과 성장촉진 보증대출(imbank-3)은 화면에 나오지 않는다. 연령 입력을 추가할지는 별도 과제로 판단해야 한다.
6. **운영 파일 category 코드**: 운영 파일의 `general_restaurants` 같은 원천 코드는 프론트 업종 id와 맞지 않는다. 교체할 때 업종 id 기준으로 통일해도 될까?
7. **구·군 특례보증 추가**: 달서구·중구·수성구 등 2026 구·군 특례보증을 전화나 공고문으로 추가 확인해 dgsinbo 파일에 넣을까?

## 6. 검증

- 방법: 스크래치 디렉터리에 `data/manual/`을 만들어 제안 JSON 3개를 복사했다. 이어서 `backend/tests/test_matching.py`와 같은 방식으로 `manual_product_gateway.Path`를 patch하고 실제 `load_all_products()`를 호출했다(`backend/.venv/bin/python`, DB 접근 없음).
- 결과: 12건 로드 성공, 필수 키 누락 없음. 3개 파일 모두 키 집합·순서가 운영 파일과 같다. product_id 중복 없음, provider_type enum 유효, 정수/실수/null 타입 일관.
- `match_products` 스모크:
  - `(3천만, restaurant, 0개월, 나이 없음)` → dgsinbo-1~5, imbank-1, imbank-2, youth-3, youth-4
  - `(8천만, cafe, 24개월, 30세)` → dgsinbo-1·2·4, imbank-1·2, youth-2·3·4
- 운영 파일 `data/manual/*.json`의 SHA-256이 검증 전후로 같았다(변경 없음).
