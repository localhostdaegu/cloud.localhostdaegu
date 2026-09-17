# 이어받기(Handoff) — 어디서부터 계속하나

> 작성: 2026-09-16 / **갱신: 2026-09-17** / 브랜치: `feat/daegu-backend` (main 대비 커밋 20여 개 앞섬, 미머지)
> 마감: 접수 **2026-09-20(일) 23:59** — 남은 작업일 D-3
> 전제 문서: 기획서 `docs/daegunavi.md` · API 목록 `docs/apilist.md` · 개발로그 `docs/jekyll.md`

---

## 0. 지금 어디까지 왔나 (30초 요약)

| 스트림 | 상태 |
|---|---|
| 백엔드 이식·대구화·신규 API | ✅ 완료 — pytest **210 passed/1 skipped** (테스트 전용 DB `localhostdaegu_test` 분리, 9/17) |
| 백엔드 수집 (인허가·funding·news·금리·rent·경계) | ✅ 완료·크론 가동 — store 161,115 · funding 1,641(온통청년 63) · news 1,915+(매시) · 금리 365 · rent 786 · 경계 142/144 |
| RAG 색인 | ✅ 완료 — Gemini 유료 키, rag_chunk 3,560(funding·news 전량), 크론 매일 05:30 |
| 프론트엔드 "한 문장 깔때기" | ✅ 완료 — vitest **78/78**, tsc clean. 9/17 상단 바 **홈 탭** 추가(지도 탐색 → 채팅 첫 화면 복귀) |
| 실백엔드 연동 스모크 | ✅ 9/16 PASS (intent→map→simulate 완주) |
| **AI 리포트 SSE `/analysis`** | ✅ 완료 (9/17) — `POST /analysis` + `GET /analysis/{id}/events` SSE(Gemini `gemini-3.8-flash`, RAG gemini 임베더), 프론트 실백엔드 연결·시뮬레이터 CTA 재무 계산표. 실스모크 52이벤트·10.4초·인용 10·매칭 10건, headless `tests/analysis.cjs` PASS. 단일 워커 전제(인메모리 저장소) |
| 수기 금융상품 JSON | ✅ 9/17 실상품 12건 반영(iM뱅크 3·대구신보 5·정책 4, 조사 `docs/research/finance-products/`) + 업종 id 통일·연령 미수집 시 비제외·카드 null 금리 "은행별 상이". 서버 재시작 후 반영(lru_cache) |
| 신규 활용신청 5종 적재 | 📋 미착수 (§4-2) |
| 백엔드 최종 리뷰·브랜치 정리 | 📋 미착수 (§3) |
| 제출물 (제안요약서·시연 영상·배포·서류) | 📋 미착수 — 참가신청서 초안만 `docs/application_form.md`(미커밋) |

크론(crontab, 로그 `logs/*.log`): news 매시 10분 · store 04:20 · funding 05:10 · rag-indexer 05:30 · 금리/rent 월요일 05:20

### 0-1. 남은 일 (2026-09-17 점검, 추천 순서)

1. ~~**AI 리포트 `/analysis` SSE**~~ — ✅ 9/17 완료(devlog 2026-09-17 "AI 리포트 /analysis SSE")
2. **수기 금융상품 JSON 실값** — iM뱅크·대구신보·대구 청년창업 실상품 5~10개 조사 → 사용자 확인. 1과 병렬 가능
3. **배포(localhostdaegu.cloud) + 시연 영상** (9/19) — 둘 다 미착수
4. **백엔드 whole-branch 최종 리뷰 → 브랜치 정리/머지** (9/19, §3)
5. **제출 서류·접수** (9/20) — 참가신청서(초안 있음)·서약서·개인정보 동의서·제안요약서 → im-challenge.com (§6)
6. 여력 시: 활용신청 5종 적재 · 빈 테이블(`shock_event_region` 충격↔지역 연결, `tobacco_retailer` 수동 파일, `academy_course`·`convenience_store`는 서울 원본 잔재로 대구 수집기 없음) · Neo4j 사용처 결정(컨테이너 기동 중, 노드 0, 코드 사용처 없음 → 쓰거나 compose 에서 제외)

동작 확인 명령:
```bash
docker compose up -d db redis neo4j          # 데이터 스토어 (5437/6381/7476·7689)
cd backend && .venv/bin/python -m pytest tests/ -q          # 210 passed 기대 (localhostdaegu_test 자동 생성·마이그레이션·시드)
cd backend && .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8300   # 백엔드
cd frontend && npm run dev                   # :3300 (브라우저 열지 말 것)
cd frontend && npx vitest run                # 78 passed 기대
node frontend/tests/funnel.cjs               # E2E (mock 기준) PASS 기대
```

---

## 1. 재개 지점 ①: API 키 입력 (사람 작업, 5분) — ✅ 완료(9/16)

`backend/.env`의 빈 값들을 기존 Metabole `~/projects/cloud.beyondfacade/backend/.env`에서 복사.
최소 필수(P0): `DATA_GO_KR_API_KEY`, `VWORLD_API_KEY`, `RONE_API_KEY`, `ECOS_API_KEY`, `BIZINFO_API_KEY`, `NAVER_NCP_API_KEY_ID/KEY`, `GEMINI_API_KEY`(리포트용).

같은 타이밍에 (리드타임 있는 것, apilist §15):
- [ ] data.go.kr **활용신청 5종**: 전통시장·온누리·백년가게·나들가게·대구교통공사 승하차 (당일 자동승인, ID는 apilist §1-6에 `[확인]`으로 표시)
- [ ] `frontend/.env.local`의 `NEXT_PUBLIC_VWORLD_KEY` 값 확인(원본 frontend .env.local에서 복사됐는지)

## 2. 재개 지점 ②: 백엔드 수집 (키 입력 직후) — ✅ 완료(9/16, Task 10 담배소매업 제외)

**SDD 이어가기**: 원장 `.superpowers/sdd/2026-09-15-daegu-backend-port/progress.md`가 살아 있다.
`Task <N>: complete` 줄이 있는 태스크(1·2·3·6·7·8·9)는 재실행 금지. 남은 것:

### Task 3 잔여 — 브이월드 경계 적재 (보류분)
```bash
cd backend
.venv/bin/python -m apps.master.adapter.inbound.cli.load_boundaries   # 대구 읍면동 WFS → data/geojson/regions/
```
- 주의: `vworld_service_domain` 기본값은 beyondfacade.cloud (기존 키의 등록 도메인 — 의도된 값). INCORRECT_KEY 나면 키·도메인 쌍 확인.

### Task 4 — 인허가 수집 (브리프: `.superpowers/sdd/.../task-4-brief.md`)
1. **OPN 코드 확정 1건 호출** (브리프 Step 1) — 3410000 체계가 맞는지. 다르면 `backend/core/matrix/grid_region_config.py`의 DISTRICTS 8개 값 + `docs/apilist.md` §11 갱신
2. 전량 수집(수 시간, 백그라운드): `store_collector` → `assign_regions`(경계 적재 선행 필수) → `build_metrics`
3. 검증 게이트(브리프 Step 5): 8구·군 count>0, bbox ≥95%, region_industry_metric>0
4. API 스모크 후 커밋 `feat: daegu permit collection + metrics verified`

### Task 5 — 수집기 가동 (브리프: `task-5-brief.md`)
- SRC `~/projects/cloud.beyondfacade/scripts/`에서 4개 셸 복사, BACKEND_DIR 수정, store 파이프라인은 **store→assign_regions→build_metrics 3단**(academy·broker 제거)
- funding 1회 실행(~1,500건), news 폴링 즉시(소급 불가), 금리·rent 1회 — **R-ONE 대구 상권 수 확인**(적으면 기획서 §10 미결 5: 구 단위 평균 강등 결정)
- crontab 등록(멱등)

### (선택) Task 10 — 담배소매업 파일 (D-데이터허브 수동 다운로드 필요, 브리프: `task-10` 없음 — 계획서 본문 참조)

## 3. 재개 지점 ③: 실연동 스모크 + 백엔드 최종 리뷰 — 스모크 ✅(9/16) / 최종 리뷰 📋

수집 완료 후:
```bash
# 프론트를 실백엔드로 전환
# frontend/.env.local: NEXT_PUBLIC_API_BASE=http://localhost:8300
cd backend && .venv/bin/uvicorn main:app --port 8300 &   # 서버
cd frontend && npm run dev &                              # :3300 (브라우저 열지 말 것)
# /map에서 대구 실폴리곤·지표 렌더, /simulate 실계산, /matching 실상품 확인 (curl/E2E)
```
- 확인 포인트: risk API가 실데이터로 값을 내는지(수집 전엔 빈 배열이 정상이었음), intent→map→simulate 깔때기가 실계약으로 완주하는지
- 그 다음 **백엔드 whole-branch 최종 리뷰** (SDD 규칙: `scripts/review-package` d62089e..HEAD → requesting-code-review/code-reviewer.md, 최상위 모델. 원장의 deferred minor 목록을 트리아지 대상으로 전달)
- 클린이면 superpowers:finishing-a-development-branch로 브랜치 정리(머지 여부는 사용자 결정)

## 4. 재개 지점 ④: D-2 계획 (별도 writing-plans 필요 — 미작성) — 9/17 전부 미착수

1. **RAG 색인 + AI 리포트 생성** — rag 앱에 LLM 생성이 없음(임베딩·검색만). 프론트 agent-report는 mock SSE로 동작 중. 백엔드 `/analysis` SSE 엔드포인트(Feature+Finance 결과+RAG 문서 → Gemini 해석) 신규 계획 필요. 계약은 프론트 `shared/api/types.ts`의 `AgentEvent` 참조
2. **신규 활용신청 5종 적재** — 승인·데이터셋 ID 확정 후 (전통시장 "반경 500m" 파생변수 포함, apilist §1-6)
3. **수기 JSON 실값 기입** — `data/manual/*.json` 3파일이 `[확인]` 플레이스홀더 상태. imbank.co.kr·대구신보에서 실상품 5~10개 (기획서 §9 D-2)
4. (선택) 리포트 해시 앵커링 — 기획서 §5.5, 여력 시에만

## 5. 알려진 이월 사항 (급하지 않음)

- 프론트: ResultView 자체 QueryClient 제거 권장(3줄), formatKrw 밴드 불일치, MoneyField 소수 입력, B유형 헤더 region 이름(백엔드 랭킹 응답에 name 추가 필요), 스펙 갭 3건(A유형 대안 업종·결론 AI 리포트 CTA·stress 렌더), T7 redoceanmap 차트(P1)
- 백엔드: `/metrics/risk` OpenAPI 스키마 부재(response_model=None), rank_by_industry N+1, tobacco 하이브리드 픽스처, s4u 수기 샘플 노출 여부(기획서 §10 미결 3)
- 저장소: `부트캠프 과제.pdf`(1.2MB) 커밋에 포함됨 — 제출 저장소 정리 시 제거 검토
- 9/17 해결분(참고): 온통청년 간헐 400/403/500 → 재시도 + 전국 1회 조회·대구(군위 포함) 필터 / 크론 로그 `exit 0` 오표기 수정 / "신규 만료 22건" 반복 = 테스트가 개발 DB 오염 → 테스트 DB 분리 / 프론트 브이월드 키는 새 키와 동일 확인(9/16 미결 해소)
- 팀 구성(1~4인)·참가신청서 — 기획서 §10 미결 2

## 6. 제출 체크리스트 (기획서 §11 — D-1)

- [ ] 참가신청서·서약서·개인정보 동의서 / [ ] 제안요약서(기획서 §1+§8 기반) / [ ] 배포 URL·시연 영상 / [ ] im-challenge.com 접수

## 7. 참조 경로 모음

| 무엇 | 어디 |
|---|---|
| 백엔드 SDD 원장(판정 이력 전체) | `.superpowers/sdd/2026-09-15-daegu-backend-port/progress.md` |
| 백엔드 계획서 | `docs/superpowers/plans/2026-09-15-daegu-backend-port.md` |
| 프론트 계획서 (실행 완료) | `docs/superpowers/plans/2026-09-15-daegu-frontend.md` |
| 태스크 브리프·리포트 (백엔드 4·5·10) | `.superpowers/sdd/2026-09-15-daegu-backend-port/task-{4,5}-brief.md` |
| SDD 스크립트 | `.claude/skills/subagent-driven-development/scripts/{task-brief,review-package,sdd-workspace}` |
| Metabole 원본(읽기 전용) | `~/projects/cloud.beyondfacade` |
| redoceanmap 저장소(콜라보 접근) | `gh repo view jangminseok-dev/com.redoceanmap` — `www/` |
