#!/usr/bin/env node
/**
 * AI 분석 E2E 스모크 (headless). 실행 중인 :3300 dev 서버를 재사용한다(E2E_REUSE_SERVER=1 전용 — 서버를 띄우거나 끄지 않는다).
 *
 * 여정: /analysis?region=2711059500&industry=cafe&finance=<13필드 JSON> (Task 10 CTA와 같은 URL) → [분석 시작]
 *      → POST {API_BASE}/analysis 가 기대 베이스로 나감 → 오케스트레이터 "완료"
 *      → 리포트 제목 5개(종합 진단·상권 진단·충격 분석·정책자금·재무 시뮬레이션) + 에러 alert 없음.
 *
 * 실백엔드: E2E_REUSE_SERVER=1 E2E_API_BASE=http://localhost:8300 node tests/analysis.cjs
 * 루트 CLAUDE.md 브라우저 규약: headless: true, 서버 준비 확인은 HTTP, try/finally 로 브라우저 정리, /analysis 재로드 금지.
 */
const http = require("http");
const { chromium } = require("playwright");

const BASE_URL = "http://localhost:3300";
const API_BASE = process.env.E2E_API_BASE || "/api/mock";
const EXPECTED_POST_URL = API_BASE.startsWith("http") ? `${API_BASE}/analysis` : `${BASE_URL}${API_BASE}/analysis`;
const REPORT_TIMEOUT_MS = 180_000; // 실 Gemini 4섹션 순차 스트림
const CITATIONS_TIMEOUT_MS = 10_000; // orchestrator done 이 report_done 보다 먼저 오고, 참고 자료는 report_done 뒤에 그려진다
const HEADINGS = ["종합 진단", "상권 진단", "충격 분석", "정책자금", "재무 시뮬레이션"];
// 시뮬레이터 결론 CTA가 싣는 재무 입력(원 단위) — 백엔드 SimulateRequest 13필드.
const FINANCE = {
  deposit: 20_000_000, key_money: 0, interior_cost: 30_000_000, equipment_cost: 10_000_000,
  monthly_rent: 1_500_000, monthly_payroll: 3_000_000, monthly_insurance: 300_000,
  cost_ratio: 0.35, fee_ratio: 0.03, equity: 40_000_000, desired_loan: 20_000_000,
  loan_rate: 0.05, expected_monthly_revenue: 20_000_000,
};

let failed = false;

function step(label, ok, detail) {
  console.log(`[${ok ? "PASS" : "FAIL"}] ${label}${detail ? " — " + detail : ""}`);
  if (!ok) failed = true;
  return ok;
}

function checkServer(url) {
  return new Promise((resolve, reject) => {
    http
      .get(url, (res) => {
        res.resume();
        res.statusCode && res.statusCode < 500 ? resolve() : reject(new Error(`status ${res.statusCode}`));
      })
      .on("error", reject);
  });
}

async function main() {
  if (process.env.E2E_REUSE_SERVER !== "1") {
    console.log("E2E_REUSE_SERVER=1 로 실행 중인 :3300 서버에 대해서만 실행한다.");
    process.exit(2);
  }
  let browser = null;
  try {
    await checkServer(BASE_URL);
    step("dev 서버 응답", true, BASE_URL);

    browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    const postUrls = [];
    page.on("request", (req) => {
      if (req.method() === "POST" && req.url().endsWith("/analysis")) postUrls.push(req.url());
    });

    const query = new URLSearchParams({ region: "2711059500", industry: "cafe", finance: JSON.stringify(FINANCE) });
    await page.goto(`${BASE_URL}/analysis?${query.toString()}`, { waitUntil: "networkidle" });
    const started = Date.now();
    await page.getByRole("button", { name: "분석 시작" }).click();

    await page
      .locator("li", { hasText: "오케스트레이터" })
      .filter({ hasText: "완료" })
      .waitFor({ state: "visible", timeout: REPORT_TIMEOUT_MS });
    step("오케스트레이터 완료", true, `${((Date.now() - started) / 1000).toFixed(1)}초`);

    step("분석 요청 베이스", postUrls[0] === EXPECTED_POST_URL, `${postUrls[0]} (기대 ${EXPECTED_POST_URL})`);
    for (const name of HEADINGS) {
      step(`리포트 제목 "${name}"`, (await page.getByRole("heading", { name }).count()) > 0);
    }
    // Next.js 라우트 아나운서(<next-route-announcer> 섀도 DOM의 role="alert")는 항상 존재하므로 제외한다.
    const alerts = await page.locator('[role="alert"]:not(#__next-route-announcer__)').allTextContents();
    step("에러 alert 없음", alerts.length === 0, alerts.join(" | "));
    let citationsShown = true;
    try {
      await page.getByRole("heading", { name: "참고 자료" }).waitFor({ timeout: CITATIONS_TIMEOUT_MS });
    } catch {
      citationsShown = false;
    }
    step("참고 자료 블록", citationsShown, `${((Date.now() - started) / 1000).toFixed(1)}초`);
  } catch (err) {
    step("예외 발생", false, err && err.stack ? err.stack : String(err));
  } finally {
    if (browser) await browser.close().catch(() => {});
  }
  console.log(failed ? "RESULT: FAIL" : "RESULT: PASS");
  process.exit(failed ? 1 : 0);
}

main();
