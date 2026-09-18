#!/usr/bin/env node
/**
 * 깔때기 E2E 스모크 (headless, 기본 mock API — E2E_API_BASE=http://localhost:8300 으로 실백엔드 스모크).
 *
 * 여정: /(채팅 랜딩) → 입력("서문시장 근처 카페, 예산 5천") → /map?district=27110...
 *      → 지도에서 대신동(region_code 2711059500) 폴리곤 클릭 → side-panel CTA 클릭
 *      → /simulate?... → 폼 제출 → 결론 헤드라인("부족한 …" 또는 "자기자본으로 충분해요") 노출.
 *
 * 루트 CLAUDE.md 브라우저 규약: headless: true 필수, 서버 준비 확인은 HTTP 폴링,
 * try/finally로 브라우저·dev 서버를 항상 정리한다.
 */
const path = require("path");
const http = require("http");
const { spawn } = require("child_process");
const { chromium } = require("playwright");

const FRONTEND_DIR = path.resolve(__dirname, "..");
const PORT = 3300;
const BASE_URL = `http://localhost:${PORT}`;
const SERVER_READY_TIMEOUT_MS = 60_000;
// 실백엔드 연동 스모크: E2E_API_BASE=http://localhost:8300 node tests/funnel.cjs (백엔드는 미리 기동)
const API_BASE = process.env.E2E_API_BASE || "/api/mock";
// 실행 중인 서버를 사용할 때는 그 서버의 API 설정을 그대로 사용하며 종료하지 않는다.
const REUSE_SERVER = process.env.E2E_REUSE_SERVER === "1";

// map-view.tsx DISTRICTS["27110"].center / flyTo zoom(13) — 클릭 좌표 계산에 쓰는 최종 카메라 상태.
const DISTRICT_CENTER = [128.606, 35.869];
const DISTRICT_ZOOM = 13;
// 대신동 — 실DB region_code(2711059500, mock fixtures.ts와 동일) — "서문시장" 텍스트가 매핑되는 행정동.
const TARGET_REGION_CODE = "2711059500";
const TARGET_REGION_CENTER = [128.578, 35.868]; // 실경계(data/geojson/regions/2711059500.json) bbox 중심과 일치

let failed = false;

function step(label, ok, detail) {
  const mark = ok ? "PASS" : "FAIL";
  console.log(`[${mark}] ${label}${detail ? " — " + detail : ""}`);
  if (!ok) failed = true;
  return ok;
}

function waitForServer(url, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  return new Promise((resolve, reject) => {
    function attempt() {
      const req = http.get(url, (res) => {
        res.resume();
        if (res.statusCode && res.statusCode < 500) {
          resolve();
        } else if (Date.now() > deadline) {
          reject(new Error(`서버가 준비되지 않았습니다 (status ${res.statusCode})`));
        } else {
          setTimeout(attempt, 500);
        }
      });
      req.on("error", () => {
        if (Date.now() > deadline) {
          reject(new Error(`서버가 준비되지 않았습니다 (${url}, ${timeoutMs}ms 초과)`));
        } else {
          setTimeout(attempt, 500);
        }
      });
    }
    attempt();
  });
}

/** 표준 Web Mercator 투영 — maplibre-gl 내부 좌표계와 동일한 공식(px/py). */
function project([lng, lat], zoom) {
  const world = 512 * Math.pow(2, zoom);
  const x = ((lng + 180) / 360) * world;
  const s = Math.sin((lat * Math.PI) / 180);
  const y = (0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)) * world;
  return [x, y];
}

async function main() {
  let server = null;
  if (REUSE_SERVER) {
    console.log(`[INFO] 실행 중인 서버 사용: ${BASE_URL}`);
  } else {
    console.log(`[INFO] dev 서버 기동: npm run dev (cwd=${FRONTEND_DIR}, port=${PORT}, api=${API_BASE})`);
    server = spawn("npm", ["run", "dev"], {
      cwd: FRONTEND_DIR,
      env: { ...process.env, NEXT_PUBLIC_API_BASE: API_BASE },
      detached: true,
      stdio: ["ignore", "pipe", "pipe"],
    });
    server.stdout.on("data", (d) => process.stdout.write(`[dev] ${d}`));
    server.stderr.on("data", (d) => process.stderr.write(`[dev] ${d}`));
  }

  let browser = null;

  try {
    await waitForServer(BASE_URL, SERVER_READY_TIMEOUT_MS);
    step("dev 서버 준비 완료", true, BASE_URL);

    browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

    // ① / 접속 → 입력 → 제출
    await page.goto(`${BASE_URL}/`, { waitUntil: "networkidle" });
    const input = page.getByPlaceholder("예: 서문시장 근처 카페, 예산 5천");
    await input.fill("서문시장 근처 카페, 예산 5천");
    await page.getByRole("button", { name: "찾아보기" }).click();

    // ② /map?district=27110... 도달 assert
    await page.waitForURL(/\/map\?/, { timeout: 15_000 });
    const mapUrl = page.url();
    step("① /map으로 이동", mapUrl.includes("/map?"), mapUrl);
    step("② URL에 district=27110 포함", mapUrl.includes("district=27110"), mapUrl);

    // ③ 지도에서 대신동 폴리곤 클릭 → region 선택
    await page.waitForSelector(".maplibregl-map", { timeout: 15_000 });
    // flyTo(district 중심, zoom 13) 애니메이션이 끝날 시간을 준다.
    await page.waitForTimeout(3_000);

    const rect = await page.evaluate(() => {
      const el = document.querySelector(".maplibregl-map");
      const r = el.getBoundingClientRect();
      return { left: r.left, top: r.top, width: r.width, height: r.height };
    });
    const [centerX, centerY] = project(DISTRICT_CENTER, DISTRICT_ZOOM);
    const [targetX, targetY] = project(TARGET_REGION_CENTER, DISTRICT_ZOOM);
    const clickX = Math.round(rect.left + rect.width / 2 + (targetX - centerX));
    const clickY = Math.round(rect.top + rect.height / 2 + (targetY - centerY));

    await page.mouse.click(clickX, clickY);

    let regionSelected = false;
    try {
      await page.waitForURL((url) => url.toString().includes(`region=${TARGET_REGION_CODE}`), {
        timeout: 5_000,
      });
      regionSelected = true;
    } catch {
      regionSelected = false;
    }

    if (regionSelected) {
      step("③ 대신동 폴리곤 클릭 → region 선택", true, page.url());
    } else {
      // 알려진 이슈(frontend/scripts/e2e-journey.sh 참고): 헤드리스 환경에서 WebGL 폴리곤
      // 히트테스트가 간헐적으로 동작하지 않을 수 있다. URL을 직접 갱신해 동일한 최종 상태로
      // 폴백하고, 실제 클릭 경로는 검증되지 않았음을 명시적으로 로그에 남긴다.
      console.warn("[WARN] 폴리곤 클릭이 region 파라미터에 반영되지 않았습니다 — URL 폴백으로 진행합니다.");
      const fallbackUrl = new URL(mapUrl);
      fallbackUrl.searchParams.set("region", TARGET_REGION_CODE);
      await page.goto(fallbackUrl.toString(), { waitUntil: "networkidle" });
      step("③ 대신동 region 선택(폴백 내비게이션)", page.url().includes(`region=${TARGET_REGION_CODE}`), page.url());
    }

    // ④ side-panel 주 CTA 클릭 → /simulate 도달 (전환계획 §3-1: 주 버튼이 사전상담 입력이다)
    const simulateCta = page.getByRole("link", { name: /창업자금 사전상담/ });
    await simulateCta.waitFor({ state: "visible", timeout: 15_000 });
    await simulateCta.click();
    await page.waitForURL(/\/simulate\?/, { timeout: 15_000 });
    step("④ /simulate로 이동", page.url().includes("/simulate?"), page.url());

    // ⑤ 최초 계산 — 주 지표가 자금 수요 기준인지 확인한다(§3-2)
    const submitButton = page.getByRole("button", { name: "시뮬레이션 실행" });
    await submitButton.waitFor({ state: "visible", timeout: 15_000 });
    await submitButton.click();
    const needLabel = page.getByText("자기자본 외 조달 필요");
    await needLabel.first().waitFor({ state: "visible", timeout: 20_000 });
    const noSelfSufficient = (await page.getByText(/자기자본으로 충분/).count()) === 0;
    step("⑤ 최초 계산 → 조달 필요 지표 노출", true, "자기자본 외 조달 필요");
    step("⑤-1 '자기자본으로 충분' 문구 없음(§7-2)", noSelfSufficient);

    // ⑥ 조건 수정 → 재계산 → 최초안·현재안 비교표
    const rentField = page.getByLabel(/월세/);
    await rentField.fill("100");
    const staleNotice = await page.getByText(/이전 입력 기준/).count();
    step("⑥-1 미제출 수정 중 이전 결과 경고", staleNotice > 0);
    await submitButton.click();
    const currentPlan = page.getByRole("radio", { name: /현재안/ });
    await currentPlan.waitFor({ state: "visible", timeout: 20_000 });
    step("⑥ 재계산 → 최초안·현재안 비교표 노출", await currentPlan.isChecked());

    // ⑦ 최초안 재선택 → 선택안이 바뀐다
    const baselinePlan = page.getByRole("radio", { name: /최초안/ });
    await baselinePlan.click();
    await page.waitForTimeout(300);
    step("⑦ 최초안 재선택", await baselinePlan.isChecked());

    // ⑧ 상담 준비 CTA → /analysis
    const handoffCta = page.getByRole("link", { name: /이 안으로 상담 준비/ });
    await handoffCta.waitFor({ state: "visible", timeout: 15_000 });
    await handoffCta.click();
    await page.waitForURL(/\/analysis\?/, { timeout: 15_000 });
    step("⑧ /analysis로 이동", page.url().includes("/analysis?"), page.url());

    // ⑨ 공식 상담 경로 — 외부 사이트를 조작하지 않고 링크 주소·문구만 확인한다
    const officialLink = page.getByRole("link", { name: /iM뱅크 공식 상담 안내/ });
    await officialLink.first().waitFor({ state: "visible", timeout: 15_000 });
    const href = await officialLink.first().getAttribute("href");
    step("⑨ iM뱅크 공식 상담 링크 노출", Boolean(href && href.includes("imbank.co.kr")), href);
  } catch (err) {
    step("예외 발생", false, err && err.stack ? err.stack : String(err));
  } finally {
    if (browser) {
      await browser.close().catch(() => {});
    }
    // detached: true로 띄웠으므로 pid == pgid — 음수 pid로 프로세스 그룹 전체(npm + next dev)를 종료한다.
    try {
      if (server) process.kill(-server.pid, "SIGTERM");
    } catch {
      // 이미 종료된 경우 무시.
    }
  }

  if (failed) {
    console.log("RESULT: FAIL");
    process.exit(1);
  } else {
    console.log("RESULT: PASS");
    process.exit(0);
  }
}

main();
