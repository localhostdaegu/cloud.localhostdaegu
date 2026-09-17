# 작업 로그

하루 단위로 이 프로젝트에서 진행된 작업을 기록합니다. 최신 날짜가 위로 오도록 작성합니다.

---

## 2026-09-17

### 백엔드 — 적재 점검·온통청년 수집 안정화·RAG 색인 완료

- 적재 현황(11:48 실측): store 161,115 · population_stat 48,174 · region_industry_metric 7,856 · news_article 1,915 · funding_program 1,641 · rent_price 786 · interest_rate 365 · shock_event 23. 빈 테이블: shock_event_region·academy_course·tobacco_retailer·convenience_store. 크론 4종(news 매시·store 04:20·funding 05:10·interest 월 05:20) 정상 가동, `rag-indexer.sh`는 crontab 미등록.
- **05:10 funding 수집 실패 원인**: 온통청년이 유효 키로도 `400`(27140)을 반환 → 재시도 없어 온통청년 수집 중단 + 이어지는 만료 갱신까지 생략. 재현 시 24회 연속 200, 직전 한 순회에선 27230이 `500` — 원천 간헐 오류(전날 403 포함). `_get_with_retry`(4xx 포함 지수 백오프 4회) 추가.
- **크론 로그 `exit 0` 결함**: `|| echo "[$(date)] … (exit $?)"`에서 `$(date)` 명령 치환이 `$?`를 0으로 덮음 → 스크립트 5종 모두 `|| { rc=$?; …; }`로 수정(모의 실패 exit 3 기록 확인).
- **온통청년 조회 8회 → 1회**: 실측 — `zipCd` 서버 필터는 동작(대구 63·서울 67·무필터 340), 대구 63건은 전국 60 + 대구 전역 3(구 전용 0). 전국엔 단일 구·군 전용 창업 정책 105건이라 대표 구 1회 조회는 누락 위험. `pageSize=500` 허용 → **전국 1회 조회 후 항목 `zipCd` ∩ 대구 구·군(군위 27720 포함) 필터**, 서버 필터 63건과 일치. 전역 `DISTRICTS`는 군위 제외 유지(설정 테스트가 명시). 실수집 63건, 테스트 210 통과.
- **RAG 색인 완료**: Gemini 임베딩 유료 키로 교체(사용자) → 증분 1회로 news 잔여 1,595건 69.3초 처리. rag_chunk funding 1,641 · news 1,915(= news_article 전량).
- Neo4j 컨테이너 기동(7476 HTTP 200, cypher-shell 응답). 노드 0 — 백엔드 코드에 Neo4j 사용처 없음.
- `rag-indexer.sh` crontab 등록 — **매일 05:30**(store 04:20·funding 05:10 직후, 뉴스는 최대 하루 지연 허용). 수동 실행: 신규 4건 처리 → 2회차 0건으로 종료, rag_chunk 3,560.
- **"신규 만료 22건" 반복 원인**: 수집 코드가 아니라 테스트. `test_funding_expiry.py`가 개발 DB에서 `_TODAY=2026-09-07`로 `refresh_expirations`를 호출 — 복원 UPDATE가 테스트 prefix로 한정되지 않아 마감 9/7~9/16 실데이터 22건을 미만료로 되돌림(pytest 전후 expired 62→40 재현). 수집 직전마다 전체 pytest를 돌려 매번 22건 재만료. 정상 배치로 복구(62건). 리포지토리 쓰기 중 범위 무제한은 이 메서드뿐.
- 미결: 테스트가 개발 DB(크론 실적재 대상)를 공유하는 구조 — 테스트 DB 분리 여부 결정 필요.

## 2026-09-16

### 백엔드 — 키 투입·수집 1차 가동 (인허가는 활용신청 대기)

- 환경변수: 루트 `.env`(도커 컴포즈 공용)에 사용자가 신규 발급 키를 수기 기입. 백엔드 `Settings`가 루트 `.env` → `backend/.env` 순으로 읽고 빈 `KEY=` 자리표시자는 무시하도록 변경(`env_ignore_empty`). 키 전부 기존 Metabole 것과 다른 신규 발급분.
- 뉴스: 네이버 검색 API 키 문제로 **구글 뉴스 RSS**(키·쿼터 없음)로 교체. `GoogleNewsRssGateway` 신규, 조립 지점 2곳 교체, 네이버 어댑터는 코드만 잔존. 실측 "서문시장 상권" 61건·"수성구 상권" 71건. 구·군 8키워드 688건 + 랜드마크 10키워드 871건 적재 → `news_article` 1,620건.
- 브이월드 경계: 새 키는 `localhostdaegu.cloud` 등록분 → `VWORLD_SERVICE_DOMAIN` 변경. WFS `lt_c_cademd`의 `adm_cd`가 **통계청 시도코드(대구=22)** 라 행안부 27 필터로는 0건 — 서울은 11로 동일해 드러나지 않던 결함. `KOSTAT_SIDO_PREFIX` 분리로 **142/144** 매칭(미매칭 2건은 논공읍공단출장소·다사읍서재출장소 = 출장소, 경계 없음이 정상). 서울 신설동·용두동 법정동 보충 항목 제거.
- 적재 실측: ECOS 기준금리 92행·대출금리 273행 / R-ONE 대구 1,572행(임대료 786·공실률 786, 2019Q1~2026Q2, 최신 빈티지 상권 **24개** → 상권 단위 유지, 구 단위 강등 불필요) / 기업마당 1,533건(해시태그 '대구' 501) / 주민등록 인구 5시점 × 144동 / 충격 이벤트 시드 23건.
- **인허가 전량 수집 완료(13:04~13:22, 18분)**: 활용신청 반영 후 7업종 × 8구·군 **161,115건**(일반음식점 96,366·휴게음식점 30,703·미용 24,800·노래 3,035·PC방 2,979·당구 1,908·체력단련 1,324). 검증 게이트: 8구·군 전부 >0 / 좌표 보유 155,568건 중 대구 bbox 내 **100%** / open_date 100%·폐업 close_date 99.98% 파싱 / 공간조인 155,557건 배정(미판정 11, 구 교차 불일치 397) / `region_industry_metric` **7,856행**(2019~2026). 연도별 개업 5.0~6.2천 건으로 안정.
- RAG 색인: Gemini 무료 등급 분당 토큰 한도(3만 TPM)에 32청크 배치 2회면 걸림 → 60초 간격 증분 반복 루프로 우회(회차당 128청크).
- **실백엔드 연동 스모크 PASS**: `frontend/.env.local` API 베이스 8300 전환, `E2E_API_BASE` 오버라이드로 깔때기 E2E 실행. 실API로 intent→map→대신동 폴리곤 클릭(실경계에서는 히트테스트 성공)→simulate→결론까지 완주. 잡힌 결함 2건: E2E·mock 픽스처의 대신동 코드가 mock 값(2711053500)이라 실DB(2711059500)와 불일치 → 통일 / 결론 헤드라인이 mock 고정 gap 전제("부족한")라 실엔진 프리필(CAPEX 0 → "자기자본으로 충분해요")에서 실패 → 두 문구 모두 결론 도달로 판정. 실API 스모크: 위험도 랭킹·동 요약·점포·지원사업 전부 실데이터, 매칭은 `data/manual` 자리표시자.
- **온통청년 게이트웨이 이식(P2)**: 키 승인 후 실호출 확정 — `zipCd`는 행안부 시군구 5자리 단일값(콤마 다중 미지원, 시도 27은 광주 반환), 서버측 `mclsfNm=창업` 필터 동작. 8구·군 순회 + plcyNo 중복 제거로 `funding_program`에 **63건(미만료 23)** 적재. 결함 2건: 신청 URL(forms.gle·gepa.kr 등)이 정책 간 공유라 `url` 유니크 제약 충돌 → 정책별 상세 페이지 URL로 교체 / 짧은 시간 40여 회 호출에 403 → 구·군 사이 1초 대기. 실수집 후 `test_store_ingest` 커서 테스트가 실데이터 최댓값에 밀려 실패 → 기존 최댓값과 픽스처 중 큰 값으로 판정하게 수정.
- RAG 색인 실측: 16:00 KST(태평양 자정) 리셋 확인 — 992 → 1,961청크(+969 ≈ 일 1,000건 한도, 배치 내 문서 단위 계산). **funding 1,641/1,641 완료**(온통청년 63 포함), news 320/1,685(잔여 1,365 → 이틀 더). `scripts/rag-indexer.sh`(매일 16:10, 정체 감지 종료) 추가 — crontab 등록은 사용자.
- 크론 스크립트 4종 `scripts/`(news·funding·interest-rent·store) 작성 — store 파이프라인은 3단. crontab 등록은 자동 모드 권한 제한으로 미실행(사용자 등록 필요).
- **차단**: 공공데이터포털 새 계정 키가 인허가 7종·상가정보·거리두기에서 `SERVICE_KEY_IS_NOT_REGISTERED_ERROR`(403). 실거래가는 200이라 키 자체는 정상 → 해당 데이터셋 **활용신청 미완**. Task 4(인허가 전량·지표 빌드)·OPN 코드 확정은 승인 후.
- 미결: Gemini 임베딩 429(RESOURCE_EXHAUSTED)로 RAG 색인 64청크에서 중단(fp16 로컬 임베더는 torch 미설치) / 프론트 `NEXT_PUBLIC_VWORLD_KEY`가 구 beyondfacade 키라 새 키로 교체 필요 / 온통청년 키 신청 중.

### 백엔드 — Metabole 이식·대구화 완료 (키 불요 구간)

- SDD(서브에이전트) 방식으로 Task 1·2·3·6·7·8·9 완료. 테스트 **196 passed / 0 failed** (이식 시점 117 → 시드 후 160 → 엔진·API 추가 후 196).
- 실측: district 8 · region 144 · mois 업종 7(일반음식점은 원본 Metabole에 없어 시드에 신규 추가) · 주민등록 CSV 전국 원본에서 대구 150행.
- 신규 API: `POST /finance/simulate`(BEP/Runway/Funding Gap/스트레스) · `GET /metrics/risk`(3형태, 백분위 모델) · `GET /matching`(보증→은행→정책) · `POST /intent`(랜드마크 15 사전).
- 리뷰 루프가 잡은 결함: 일반음식점 업종 누락, 재무 산식 1원 truncation(계획서 결함), 위험도 혼합 연도 누락, placebo 게이트웨이 테스트 — 전부 fix·재리뷰 완료.
- 미결: Task 4(인허가 수집)·5(수집기 가동)·브이월드 경계 적재 — **API 키 대기**. 백엔드 최종 whole-branch 리뷰는 수집 후.

### 프론트엔드 — "한 문장 깔때기" 완성

- Metabole 프론트 이식(71파일) → 대구화 → 채팅 랜딩(⓪①) → 진단 패널(RiskCard·B유형 랭킹) → 시뮬레이터 → 결론 화면(Funding Gap→매칭 카드) → headless E2E. **vitest 77/77 · tsc clean · funnel E2E PASS**.
- 업종 어휘를 전 구간 industry_id로 통일(백엔드 intent 계층 포함) — mois slug는 수집 계층에만 유지.
- 최종 whole-branch 리뷰가 Critical 1건(B유형 도달 불가 — 계획 내부 모순) 적발 → fix 웨이브로 해소(B유형 직행 칩, MapState.industry nullable, 도달성 테스트).
- 리뷰가 잡은 실계약 결함: matching category 파라미터 누락 시 실백엔드 422(mock이 가림) — 상시 전송으로 수정.
- 미결: T7(redoceanmap 차트, P1 보류) · 실백엔드 연동 스모크(수집 후) · 스펙 갭 후속(A유형 대안 업종, 결론 화면 AI 리포트 CTA, stress 렌더).


## 2026-09-15 — 프로젝트 개시: 뼈대·지침 체계·포트 확정·도커 구성·해커톤 정리와 도메인 확정

### 프로젝트 뼈대 생성

- 루트 `CLAUDE.md` 첫 커밋(4ba6dac)으로 저장소를 시작했다. 공유 행동 지침(Part I 신중함·단순성·수술적 변경·목표 주도 실행 + Part II GoF 23패턴 매핑)이 내용이다.
- 백엔드 헥사고날 스캐폴딩을 준비했다 — `backend/apps/dummy/` 아래 프랙탈 디렉터리 골격(domain/entities·value_objects, app/ports/input·output·use_cases·dtos, adapter/inbound·outbound, dependencies)과 `backend/core/`. `main.py`·`requirements.txt`는 아직 빈 파일이며 구현은 이후 단계다.
- `frontend/`는 지침 문서만 있는 빈 상태로 두었다(스택 미확정).

### Superpowers v6.3.0 스킬 라이브러리 설치

- obra/superpowers 저장소를 클론해 스킬 13종(brainstorming, test-driven-development, systematic-debugging, subagent-driven-development, code review 계열, git-worktrees 등)을 `.claude/skills/`에 복사했다.
- session-start 훅을 `.claude/hooks/`에 설치(실행 권한 포함)하고 `.claude/settings.json`에 SessionStart 훅(startup|clear|compact)을 구성했다. 훅이 `hookSpecificOutput.additionalContext` JSON을 정상 출력하고 exit 0으로 끝나는 것까지 검증한 뒤 임시 클론을 정리했다.
- `.agents/skills`·`.codex/skills`에도 스킬 디렉터리를 두어 타 하네스에서 같은 스킬을 쓸 수 있게 했다.

### 지침 파일 6종에 포트 기록 — 백엔드 8300 · 프론트엔드 3300

- 루트·`backend/`·`frontend/`의 `AGENTS.md`/`CLAUDE.md` 6개 파일 전부에 포트 약속(백엔드 **8300**, 프론트엔드 **3300**)을 기록했다. 이전 프로젝트에서 복사되며 남아 있던 구 포트(3500/8500)는 전부 제거했다(grep 검증).
- 함께 바로잡은 결함 3건: ① 루트 `AGENTS.md`가 존재하지 않는 `backend/docs/AGENTS.md`·`frontend/docs/AGENTS.md`를 가리키던 참조를 실제 경로로 수정 ② `frontend/AGENTS.md` 헤더가 `# CLAUDE.md — Frontend`로 잘못돼 있던 것을 정정 ③ `frontend/CLAUDE.md`가 루트 CLAUDE.md 전문 복사본(8.4KB)이었던 것을 프론트 전용 내용만 남기고 187바이트로 정리(루트는 자동 로드되므로 중복).
- 루트 `CLAUDE.md`에는 하위 `backend/CLAUDE.md`·`frontend/CLAUDE.md`를 함께 따르라는 안내 절을 추가했다.

### 도커 구성 — pgvector · neo4j · redis (cloud.beyondfacade 패턴)

- 적재 데이터 스토어로 pgvector·neo4j·redis를 쓰기로 하고, 동일 구성을 이미 운영 중인 `cloud.beyondfacade`의 compose 패턴을 따라 `docker-compose.yml`(프로젝트명 `localhostdaegu`)과 `backend/Dockerfile`(python:3.14-slim + uvicorn, 내·외부 8300 통일)을 작성했다.
- 호스트 포트는 전 프로젝트의 compose를 전수 조사해(5432~5436, 6379~6380, 7474~7475/7687~7688, 8000/8200/8700, 3000/3200/3700 사용 중) 충돌 없는 번호로 배정: **Postgres/pgvector 5437 · Neo4j 7476(HTTP)/7689(Bolt) · Redis 6381**. 전부 `127.0.0.1` 바인딩으로 LAN 노출을 차단하고 네임드 볼륨(pgdata·neo4jdata·neo4jlogs·redisdata)으로 영속화한다.
- backend 서비스에는 `DATABASE_URL`(psycopg)·`NEO4J_URI`·`REDIS_URL` 환경변수 주입과 db 헬스체크 의존을 배선했다. 다만 백엔드가 아직 구현 전이라 **backend·frontend 둘 다 프로필로 게이트** — 기본 `docker compose up`은 데이터 스토어 3종만 띄우고, 백엔드는 구성 완료 후 `--profile backend`로 붙인다. `docker compose config` 검증 통과(기본 서비스: db·neo4j·redis).
- beyondfacade의 cloudflared 터널 서비스는 필요 여부 미정이라 넣지 않았다. 데이터 스토어 포트는 루트 `AGENTS.md`/`CLAUDE.md` Local ports 절에도 반영했다.

### 작업 로그 규약 수립

- 하루 단위로 `docs/jekyll.md`에 기록한다. 최신 날짜가 위로 오고, 실측·검증 결과와 미결 사항을 함께 남긴다(다른 프로젝트 데브로그와 동일 규약).

### 해커톤 정리와 도메인 확정

- 이 프로젝트의 목적을 확정했다 — **2026 AI Blockchain Challenge in Daegu**(iM뱅크 주최·DIP 주관·대구시 후원) 참가작. 트랙은 **5.3 소상공인·골목상권 디지털 금융**. 공고 정리는 `docs/2026_AI_Blockchain_Challenge_Daegu.md`에 작성했다(대회 개요·일정·제출물 5종·시상·6개 트랙·활용 데이터·공략 포인트·체크리스트).
- 핵심 제약: **접수 마감 2026-09-20 23:59(D-5)**, 프로토타입(구현 코드) 제출 필수 — 슬라이드만으로는 접수 불가. 본선 발표 9/23, 시상식 10/22 대구 EXCO.
- 도메인 확정: 서비스는 **localhostdaegu.cloud**(이 저장소), 지킬 블로그/허브는 **053.localhostdaegu.cloud**(별도 저장소 `~/projects/053.localhostdaegu.cloud`, 현재 README만 있는 초기 상태). 루트 `AGENTS.md`/`CLAUDE.md`에 Project context 절로 반영했다.
