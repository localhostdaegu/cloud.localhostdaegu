# 배포 가이드 — 프론트 Vercel + 백엔드 Cloudflare Tunnel

처음 배포하는 사람이 **이 문서만 보고 끝까지 갈 수 있게** 썼습니다. 명령마다 "무엇을 하는지"와 "성공하면 뭐가 보이는지"를 함께 적었습니다.

작성 2026-09-18 · 배포 예정 9/20

---

## 0. 전체 그림 (먼저 이해하고 시작하세요)

```
        사용자 브라우저
              │
              ▼
   ┌─────────────────────┐
   │ Vercel (프론트 화면)  │   Next.js, 인터넷에 공개
   │ localhostdaegu.cloud │
   └──────────┬──────────┘
              │  API 요청 (fetch)
              ▼
   ┌──────────────────────────┐
   │ Cloudflare (인터넷 입구)   │   api.localhostdaegu.cloud
   └──────────┬───────────────┘
              │  터널 (암호화된 연결, 포트 개방 없음)
              ▼
   ┌──────────────────────────┐
   │ 이 컴퓨터                  │
   │  · 백엔드 FastAPI :8300    │
   │  · Postgres (Docker) :5437 │
   └──────────────────────────┘
```

**핵심**: 백엔드는 인터넷에 직접 열지 않습니다. Cloudflare Tunnel이 **바깥에서 안으로 뚫는 게 아니라, 이 컴퓨터가 Cloudflare로 나가서 연결을 유지**합니다. 공유기 포트포워딩·방화벽 설정이 필요 없는 이유입니다.

> ⚠️ **이 컴퓨터가 꺼지면 백엔드가 멈춥니다.** 화면(Vercel)은 떠 있지만 데이터가 안 나옵니다. 심사 기간에는 켜 두세요.

---

## 1. 지금 상태 점검 (이미 되어 있는 것)

이 컴퓨터에는 **이미 같은 구조가 돌고 있습니다.** `remakeday.com`이 똑같이 "Vercel 화면 + 터널 API"로 운영 중입니다. 그 설정을 본떠서 갑니다.

| 항목 | 상태 |
|---|---|
| `cloudflared` 설치 | ✅ `~/.local/bin/cloudflared` (2026.8.2) |
| Cloudflare 로그인 | ✅ `~/.cloudflared/cert.pem` 있음 — `tunnel login` 다시 안 해도 됨 |
| 기존 터널 예시 | ✅ `~/.cloudflared/remakeday.yml` + systemd 서비스 |
| **도메인** `localhostdaegu.cloud` | ❌ **아직 Cloudflare가 아니라 가비아 네임서버** ← 여기가 할 일 |

확인 명령:

```bash
dig +short NS localhostdaegu.cloud
```

- `ns1.gabia.co.kr` 처럼 나오면 → **아직 Cloudflare 아님** (§2-A 필요)
- `...ns.cloudflare.com` 처럼 나오면 → 준비 완료 (§2-A 건너뛰고 §2-B로)

---

## 2. 백엔드 — Cloudflare Tunnel

### 경로가 두 개입니다. 먼저 고르세요

| | A. 도메인 연결 (권장) | B. 임시 주소 (급할 때) |
|---|---|---|
| 주소 | `api.localhostdaegu.cloud` 고정 | `랜덤이름.trycloudflare.com` |
| 준비 | 네임서버 이전 필요 (**전파에 수십 분~수 시간**) | 없음, 즉시 |
| 재시작하면 | 주소 그대로 | **주소가 바뀜** → Vercel 환경변수·CORS 다시 설정 |
| 언제 | 시간이 있을 때 | 마감이 코앞일 때 |

> **시간 계산**: 9/20 마감인데 네임서버 이전은 전파를 기다려야 합니다. **9/19 중에 A를 시작**하고, 전파가 안 끝나면 B로 제출한 뒤 나중에 A로 바꾸는 것이 안전합니다.

---

### 2-A. 도메인을 Cloudflare로 옮기기

> ⚠️ **먼저 읽으세요.** `053.localhostdaegu.cloud`(지킬 블로그)가 현재 GitHub Pages(`localhostdaegu.github.io`)를 가리키고 있습니다. 네임서버를 옮기면 **기존 DNS 레코드를 Cloudflare에 다시 만들어야** 합니다. 안 하면 블로그가 죽습니다.
>
> 옮기기 전에 가비아 DNS 관리 화면을 **스크린샷으로 남겨 두세요.** 레코드를 그대로 옮겨 적어야 합니다.

1. [dash.cloudflare.com](https://dash.cloudflare.com) 로그인 → **Add a site** → `localhostdaegu.cloud` 입력
2. 플랜 선택 화면에서 **Free** 선택
3. Cloudflare가 기존 DNS 레코드를 자동으로 읽어옵니다. **`053` 레코드(CNAME → `localhostdaegu.github.io`)가 있는지 꼭 확인**하고, 없으면 직접 추가
4. Cloudflare가 네임서버 2개를 알려줍니다 (예: `michael.ns.cloudflare.com`)
5. **가비아** 로그인 → 도메인 관리 → `localhostdaegu.cloud` → 네임서버 변경 → Cloudflare가 준 2개로 교체
6. 기다립니다. 확인:

```bash
dig +short NS localhostdaegu.cloud
```

`...ns.cloudflare.com`이 나오면 완료입니다. (보통 10분~2시간, 길면 24시간)

---

### 2-B. 터널 만들기 (도메인 연결 완료 후)

**① 터널 생성** — 이름은 `localhostdaegu`로 합니다.

```bash
cloudflared tunnel create localhostdaegu
```

성공하면 이렇게 나옵니다:

```
Created tunnel localhostdaegu with id 1a2b3c4d-....
```

**이 id를 복사해 두세요.** 다음 단계에서 씁니다. (`~/.cloudflared/<id>.json` 파일도 함께 생깁니다 — 이게 터널 자격증명입니다. 절대 공유하지 마세요.)

**② 설정 파일 작성** — `~/.cloudflared/localhostdaegu.yml`

아래에서 `<터널ID>` 두 곳을 ①에서 복사한 id로 바꾸세요.

```yaml
# localhostdaegu — api.localhostdaegu.cloud → 이 컴퓨터 백엔드(8300)
# 화면은 Vercel이 담당하므로 이 터널은 API 하나만 노출한다.
tunnel: <터널ID>
credentials-file: /home/kimchungsik/.cloudflared/<터널ID>.json

ingress:
  # Swagger 문서는 외부에 열지 않는다. 내부 확인은 localhost:8300/docs 로 그대로 된다.
  - hostname: api.localhostdaegu.cloud
    path: ^/(docs|redoc|openapi\.json)
    service: http_status:404

  - hostname: api.localhostdaegu.cloud
    service: http://127.0.0.1:8300
    originRequest:
      connectTimeout: 30s
      # AI 리포트가 SSE로 10~20초 흐른다. 넉넉히 둔다.
      noTLSVerify: false

  - service: http_status:404
```

**③ DNS 연결** — 이 명령이 Cloudflare에 `api.localhostdaegu.cloud` 레코드를 자동으로 만듭니다.

```bash
cloudflared tunnel route dns localhostdaegu api.localhostdaegu.cloud
```

성공하면 `Added CNAME api.localhostdaegu.cloud which will route to this tunnel` 이 나옵니다.

**④ 먼저 손으로 한 번 띄워 보기** (서비스로 등록하기 전에 동작 확인)

```bash
# 터미널 1 — 백엔드
cd ~/projects/cloud.localhostdaegu/backend
CORS_ALLOW_ORIGINS=https://localhostdaegu.cloud .venv/bin/uvicorn main:app --host 127.0.0.1 --port 8300

# 터미널 2 — 터널
cloudflared --config ~/.cloudflared/localhostdaegu.yml tunnel run localhostdaegu
```

**터미널 3에서 확인:**

```bash
curl https://api.localhostdaegu.cloud/matching/myself
```

`{"app":"matching","status":"wired"}` 가 나오면 **터널 성공**입니다. 🎉

여기까지 되면 두 터미널을 `Ctrl+C`로 끄고 ⑤로 갑니다.

**⑤ 자동 실행 등록** (컴퓨터를 켜면 알아서 뜨도록)

백엔드와 터널 **둘 다** 등록합니다. 하나만 등록하면 반쪽만 살아납니다.

`~/.config/systemd/user/localhostdaegu-backend.service`:

```ini
[Unit]
Description=localhostdaegu backend (FastAPI :8300)
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=/home/kimchungsik/projects/cloud.localhostdaegu/backend
# 워커는 반드시 1개 — 분석 요청 저장소가 메모리에 있어 2개 이상이면 리포트가 404가 난다.
ExecStart=/home/kimchungsik/projects/cloud.localhostdaegu/backend/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8300 --workers 1
Environment=CORS_ALLOW_ORIGINS=https://localhostdaegu.cloud
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

`~/.config/systemd/user/localhostdaegu-tunnel.service`:

```ini
[Unit]
Description=cloudflared tunnel — api.localhostdaegu.cloud → 127.0.0.1:8300
After=network-online.target localhostdaegu-backend.service
Wants=network-online.target

[Service]
ExecStart=/home/kimchungsik/.local/bin/cloudflared --config %h/.cloudflared/localhostdaegu.yml --no-autoupdate tunnel run localhostdaegu
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

등록하고 시작:

```bash
systemctl --user daemon-reload
systemctl --user enable --now localhostdaegu-backend localhostdaegu-tunnel

# 둘 다 active (running) 인지 확인
systemctl --user status localhostdaegu-backend localhostdaegu-tunnel --no-pager | grep -E "Active|●"

# 로그가 보고 싶으면
journalctl --user -u localhostdaegu-backend -f
```

> **노트북이라면** `sudo loginctl enable-linger kimchungsik` 을 한 번 실행하세요. 로그아웃해도 서비스가 계속 돕니다.

---

### 2-B′. 임시 주소로 가는 경우 (경로 B)

도메인 없이 한 줄이면 끝납니다.

```bash
cloudflared tunnel --url http://127.0.0.1:8300
```

출력에 이런 줄이 나옵니다:

```
+-------------------------------------------------------+
|  https://cold-river-1234.trycloudflare.com            |
+-------------------------------------------------------+
```

**이 주소를 복사**해서 §3의 `NEXT_PUBLIC_API_BASE`와 백엔드 `CORS_ALLOW_ORIGINS`에 씁니다.

> ⚠️ **끄면 주소가 사라집니다.** 다시 켜면 다른 주소가 나오고, 그때마다 Vercel 환경변수를 고치고 **재배포**해야 합니다. 시연 직전에 껐다 켜지 마세요.

---

## 3. 프론트엔드 — Vercel

### 3-1. 프로젝트 만들기

1. [vercel.com](https://vercel.com) → GitHub 계정으로 로그인
2. **Add New → Project** → `localhostdaegu/cloud.localhostdaegu` 저장소 선택
3. 설정 화면에서 **딱 하나 반드시 바꿔야 합니다**:

   | 항목 | 값 | 이유 |
   |---|---|---|
   | **Root Directory** | `frontend` | **저장소 루트에 `package.json`이 없습니다.** 이걸 안 바꾸면 빌드가 바로 실패합니다 |
   | Framework Preset | Next.js (자동 인식) | 그대로 두기 |
   | Build Command | 비워 두기 (자동 `next build`) | 그대로 두기 |

### 3-2. 환경변수 — 배포 전에 넣으세요

**Settings → Environment Variables** 에서 추가합니다. Production·Preview 둘 다 체크.

| 이름 | 값 | 비고 |
|---|---|---|
| `NEXT_PUBLIC_API_BASE` | `https://api.localhostdaegu.cloud` | 경로 B면 `https://....trycloudflare.com` |
| `NEXT_PUBLIC_VWORLD_KEY` | 브이월드 인증키 | 없으면 지도 배경이 안 나옴 |

> 🚨 **가장 흔한 실수** — `NEXT_PUBLIC_API_BASE`를 **안 넣으면 에러 없이** 내장 가짜 데이터(mock)로 동작합니다. 화면은 멀쩡한데 숫자가 고정값입니다. 반드시 넣으세요.
>
> 🚨 **두 번째 흔한 실수** — `NEXT_PUBLIC_`으로 시작하는 값은 **빌드할 때 코드에 박힙니다.** 나중에 값을 고치면 **재배포(Redeploy)** 해야 반영됩니다. 저장만으로는 안 바뀝니다.

### 3-3. 배포

**Deploy** 버튼을 누릅니다. 2~3분이면 끝나고 `https://<프로젝트명>.vercel.app` 주소가 나옵니다.

### 3-4. 도메인 연결 (경로 A인 경우)

**Settings → Domains** → `localhostdaegu.cloud` 추가 → Vercel이 알려주는 DNS 레코드를 **Cloudflare 대시보드**에 추가합니다.

> Cloudflare에서 이 레코드의 **프록시는 끄세요**(회색 구름 ☁️, "DNS only"). 주황 구름이면 Vercel과 Cloudflare가 서로 캐시를 물어 이상하게 동작할 수 있습니다.

---

## 4. 연결하기 — CORS (여기서 제일 많이 막힙니다)

브라우저는 "다른 주소로 보내는 요청"을 기본적으로 막습니다. 백엔드가 **"이 주소는 괜찮다"고 허락**해야 합니다.

`CORS_ALLOW_ORIGINS`에 **프론트 주소를 전부** 넣습니다. 쉼표로 구분:

```bash
CORS_ALLOW_ORIGINS=https://localhostdaegu.cloud,https://cloud-localhostdaegu.vercel.app
```

- 커스텀 도메인과 `.vercel.app` 주소 **둘 다** 넣으세요
- 끝에 `/`를 붙이지 마세요 (`https://localhostdaegu.cloud/` ❌)
- `http`가 아니라 `https`입니다
- 바꿨으면 백엔드를 다시 시작: `systemctl --user restart localhostdaegu-backend`

`localhost:3300`은 넣지 않아도 항상 허용됩니다(개발용).

**확인 명령:**

```bash
curl -s -o /dev/null -D - -X OPTIONS https://api.localhostdaegu.cloud/finance/simulate \
  -H "Origin: https://localhostdaegu.cloud" \
  -H "Access-Control-Request-Method: POST" | grep -i access-control-allow-origin
```

`access-control-allow-origin: https://localhostdaegu.cloud` 가 나오면 성공입니다.

---

## 5. 배포 끝났으면 이것들을 눈으로 확인하세요

### 명령으로

```bash
# ① 백엔드가 살아 있는가
curl https://api.localhostdaegu.cloud/matching/myself
#   → {"app":"matching","status":"wired"}

# ② 데이터가 들어 있는가 (상품 3건이 나와야 정상)
curl "https://api.localhostdaegu.cloud/matching/consultation?external_funding_need=20000000&category=cafe"

# ③ Swagger가 막혔는가 (보안)
curl -o /dev/null -w "%{http_code}\n" https://api.localhostdaegu.cloud/docs
#   → 404 가 정상입니다
```

### 브라우저로 (순서대로)

- [ ] 홈에서 **"중구에서 카페, 예산 4천만"** 입력 → 지도로 이동
- [ ] 지도에 **폴리곤이 그려지는가** (안 그려지면 브이월드 키 문제)
- [ ] 대신동 클릭 → **"이 자리로 창업자금 사전상담"** 버튼 클릭
- [ ] 월세 250 입력 후 계산 → **"자기자본 외 조달 필요"에 숫자가 보이는가**
      → 비어 있거나 이상하면 **`NEXT_PUBLIC_API_BASE`가 mock으로 떨어진 것**
- [ ] 월세를 100으로 고치고 다시 계산 → **최초안·현재안 비교표**가 뜨는가
- [ ] "이 안으로 상담 준비" → 리포트에 **"상담할 계획"** 섹션이 뜨는가
      → "종합 진단"이 뜨면 상담자료가 아니라 옛 리포트로 간 것
- [ ] 리포트가 **한 번에 툭 나오지 않고 조금씩 채워지는가** (SSE 정상)
- [ ] "상담자료 저장" 눌러 `.md` 파일이 받아지는가

---

## 6. 문제 해결

| 증상 | 원인 | 조치 |
|---|---|---|
| Vercel 빌드가 `package.json not found`로 실패 | Root Directory가 `frontend`가 아님 | Settings → General → Root Directory = `frontend` → Redeploy |
| 화면은 뜨는데 숫자가 항상 똑같음 | `NEXT_PUBLIC_API_BASE` 미설정 → mock 동작 | 환경변수 넣고 **Redeploy** (저장만으론 안 됨) |
| 브라우저 콘솔에 `CORS policy` 빨간 에러 | 백엔드가 그 주소를 허락 안 함 | `CORS_ALLOW_ORIGINS`에 그 주소 추가 → 백엔드 재시작 |
| `curl`은 되는데 브라우저만 안 됨 | 거의 항상 CORS | 위와 같음 |
| `api.…` 주소가 502/1033 | 터널은 살아 있는데 백엔드가 죽음 | `systemctl --user status localhostdaegu-backend` |
| `api.…` 주소가 아예 안 열림 | 터널이 죽음 | `systemctl --user status localhostdaegu-tunnel` |
| 리포트가 10초 뒤 **한 번에** 나옴 | SSE 스트림이 중간에 모였다 옴 | 앱은 이미 올바른 헤더를 보냅니다. Cloudflare 프록시가 주황 구름인지, 앞단에 다른 프록시가 있는지 확인 |
| 리포트가 500 에러 | `GEMINI_API_KEY` 없음 | 백엔드 서비스의 `Environment=`에 키 추가 후 재시작 |
| 리포트를 시작하면 404 | uvicorn 워커가 2개 이상 | `--workers 1` 확인 (분석 요청이 메모리에 있음) |
| 지도 배경만 안 나옴 | 브이월드 키 / 등록 도메인 | 브이월드에서 운영 도메인이 등록됐는지 확인 |
| 갑자기 전부 안 됨 | **컴퓨터가 꺼졌거나 잠듦** | 켜고 `systemctl --user status …` 확인 |

---

## 7. 꼭 기억할 것 세 가지

1. **이 컴퓨터가 백엔드입니다.** 꺼지면 서비스가 멈춥니다. 심사 기간에 절전·자동 종료를 꺼 두세요.
2. **`NEXT_PUBLIC_*`은 빌드 때 박힙니다.** 고쳤으면 반드시 Redeploy.
3. **CORS에 주소를 빠짐없이.** `.vercel.app`과 커스텀 도메인은 서로 다른 주소입니다.

---

## 관련 문서

- 환경변수 전체 목록·DB 준비: [배포 런북](deploy-runbook.md)
- 시연 순서와 예상 질문: [시연 대본](demo-script.md)
- 지금까지 한 일과 남은 일: [이어받기](handoff.md)
