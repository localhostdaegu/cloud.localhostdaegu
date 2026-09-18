# 배포 런북 (2026-09-18 작성, 배포 예정일 9/20)

한 번도 배포한 적 없는 상태에서 쓰는 문서다. **아직 배포하지 않았고**, 여기 적힌 것은 코드에서 확인한 설정과 알려진 함정이다. 실제 배포에서 새로 드러나는 것은 이 문서에 덧붙인다.

## 0. 먼저 정해야 하는 것 (코드로 못 정함)

- [ ] 프론트 호스팅 — Vercel / 이 머신 / 기타
- [ ] 백엔드 호스팅 — 이 머신 + 리버스 프록시 / 클라우드 VM / 기타
- [ ] DB — 현재 개발 DB(로컬 Docker `localhostdaegu-db`, 포트 5437)를 그대로 쓸지, 별도 인스턴스를 둘지
- [ ] 도메인 `localhostdaegu.cloud` DNS를 어디로 향하게 할지

백엔드는 **인메모리 상태**를 쓰므로(§3) 서버리스에 그대로 올릴 수 없다. 프로세스가 계속 살아 있는 형태여야 한다.

## 1. 환경변수

### 백엔드 (`backend/.env` 또는 프로세스 환경)

| 변수 | 필요성 | 비고 |
|---|---|---|
| `DATABASE_URL` | **필수** | 없으면 기동 실패 |
| `GEMINI_API_KEY` | **필수** | 없으면 `POST /analysis` 500. 리포트와 RAG 임베딩이 같은 키를 쓴다 |
| `CORS_ALLOW_ORIGINS` | **필수** | `https://localhostdaegu.cloud` 형태, 쉼표 구분. **없으면 배포한 프론트의 요청을 브라우저가 버린다** |
| `GEMINI_REPORT_MODEL` | 선택 | 기본 `gemini-3.8-flash` |
| `VWORLD_SERVICE_DOMAIN` | 확인 필요 | **코드 기본값이 `beyondfacade.cloud`(원천 프로젝트 도메인)다.** 브이월드 키 등록 조건과 운영 도메인에 맞게 설정 |
| `ECOS_API_KEY` · `BIZINFO_API_KEY` · `DATA_GO_KR_API_KEY` · `YOUTHCENTER_API_KEY` | 수집기만 | 런타임 조회는 DB를 읽으므로 웹 서비스에는 없어도 된다. 크론을 함께 돌린다면 필요 |

`CORS_ALLOW_ORIGINS`를 비워도 `http://localhost:3300`·`http://127.0.0.1:3300`은 항상 허용된다(`core/matrix/grid_cors.py`).

### 프론트 (`frontend/.env.production` 또는 호스팅 설정)

| 변수 | 필요성 | 비고 |
|---|---|---|
| `NEXT_PUBLIC_API_BASE` | **필수** | 운영 백엔드 주소. **미설정이면 `/api/mock`으로 떨어져 고정 데이터가 보인다** — 배포 후 반드시 눈으로 확인 |
| `NEXT_PUBLIC_VWORLD_KEY` | 지도 배경에 필요 | 브라우저에서 호출하는 키다. 서버용 키를 여기에 넣지 않는다 |

## 2. DB 준비

```bash
cd backend
.venv/bin/alembic upgrade head          # 현재 head: b93358fab70e (29테이블)
.venv/bin/python -m apps.product.adapter.inbound.cli.seed_finance_product
```

시드 후 확인 — 상품 12건, 상담 메타데이터 12건이어야 한다.

```sql
select count(*) from finance_product;                 -- 12
select bank_connection, count(*) from product_consultation_metadata group by 1;
-- direct 2 / linked 3 / unverified 7
```

`external_dataset`·`regional_indicator`는 **0행이 정상**이다(센터 데이터 미확보).

## 3. 서버 기동 시 지켜야 할 것

- **uvicorn 단일 워커.** 인메모리 상태가 두 곳 있다 — 분석 요청 저장소(`InMemoryAnalysisRequestStore`)와 mock 목적 저장소(`analysis-purpose.ts`). 워커를 늘리면 `POST /analysis` 직후 `GET /events`가 404가 되거나 목적이 섞인다.
- **SSE 버퍼링 끄기.** 리버스 프록시 뒤라면 nginx `proxy_buffering off;`. 켜져 있으면 리포트가 한꺼번에 도착해 진행 표시가 죽는다. 앱은 `X-Accel-Buffering: no`를 이미 보낸다.
- **타임아웃.** 리포트 스트림이 실측 11~16초다. 프록시 `proxy_read_timeout`을 넉넉히(예: 300s).

## 4. 배포 후 눈으로 확인할 것

```bash
curl https://<백엔드>/matching/myself                      # {"app":"matching","status":"wired"}
curl "https://<백엔드>/matching/consultation?external_funding_need=20000000&category=cafe"
#   → 3건 (imbank-1·2 direct, imbank-3 linked)
curl -X OPTIONS https://<백엔드>/finance/simulate \
  -H "Origin: https://localhostdaegu.cloud" -H "Access-Control-Request-Method: POST" -D - -o /dev/null
#   → access-control-allow-origin 헤더에 운영 도메인
```

브라우저에서:

- [ ] `/map` 폴리곤이 그려지고 지표가 보인다 (브이월드 키·경계 데이터)
- [ ] `/simulate` 계산 결과에 **자기자본 외 조달 필요**가 보인다 — 여기 값이 비면 `NEXT_PUBLIC_API_BASE`가 mock으로 떨어진 것이다
- [ ] 조건을 바꿔 재계산하면 **최초안·현재안 비교표**가 뜬다
- [ ] `/analysis`에서 **상담할 계획 / 최초안과 현재안** 섹션이 나온다 — `종합 진단`이 나오면 handoff가 아니라 review로 간 것이다
- [ ] 상담자료 저장 버튼이 눌리고 Markdown이 내려받아진다

## 5. 배포하지 않아도 되는 것

- 크론(수집기) — 시연에 필요한 데이터는 이미 DB에 있다. 배포일에 수집기를 새로 돌리지 않는다
- `external_dataset`·`regional_indicator` 적재 — 데이터가 없다

## 6. 알려진 함정 (실제로 겪은 것)

- **개발 중 백엔드를 `--reload` 없이 띄웠다가 코드 변경이 반영되지 않아 E2E가 통과한 것처럼 보인 적이 있다.** 배포 후 검증은 반드시 §4의 `curl`로 응답 필드를 직접 확인한다. 화면에 라벨만 떠도 값이 비어 있을 수 있다.
- `NEXT_PUBLIC_API_BASE` 미설정 시 조용히 mock으로 떨어진다. 에러가 나지 않아 알아채기 어렵다.
