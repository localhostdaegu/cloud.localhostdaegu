# 작업 로그

하루 단위로 이 프로젝트에서 진행된 작업을 기록합니다. 최신 날짜가 위로 오도록 작성합니다.

---

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
