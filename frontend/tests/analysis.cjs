#!/usr/bin/env node
/**
 * AI 분석 E2E 스모크 (headless). 실행 중인 :3300 dev 서버를 재사용한다(E2E_REUSE_SERVER=1 전용 — 서버를 띄우거나 끄지 않는다).
 *
 * 여정: 저장된 선택안(sessionStorage)을 깔고 /analysis 로 진입 → [분석 시작]
 *      → POST {API_BASE}/analysis 가 purpose=handoff 로 나감 → 오케스트레이터 "완료"
 *      → 상담자료 섹션(계획·비교·계산·확인 사항) + 서버 재계산 수치 + 저장 버튼 활성 + 에러 alert 없음.
 *
 * 제목이 보이는지만 보지 않는다 — 선택안의 월세가 계산표에 반영됐는지, 미확보 희망대출이 남아 있는지 본다.
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
const HANDOFF_HEADINGS = ["상담할 계획", "최초안과 현재안", "재무 시뮬레이션", "상담에서 확인할 것"];
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

    // 시뮬레이터가 남겼을 선택안을 그대로 깔아 둔다 — /analysis 는 이것으로 상담자료를 만든다(§5-3).
    const BASELINE = { ...FINANCE, monthly_rent: 2_500_000 };
    const RESULT_CURRENT = {
      capex: 60_000_000, monthly_fixed: 4_883_333, bep_revenue: 7_876_343, funding_gap: 49_299_998,
      reserve_months: 6, operating_reserve: 29_299_998,
      total_required_funds: 89_299_998, external_funding_need: 49_299_998,
      scenarios: [], stress: [],
    };
    const RESULT_BASELINE = {
      ...RESULT_CURRENT,
      monthly_fixed: 5_883_333, bep_revenue: 9_489_247,
      operating_reserve: 35_299_998, total_required_funds: 95_299_998,
      external_funding_need: 55_299_998, funding_gap: 55_299_998,
    };
    const DRAFT = {
      version: 1,
      region: "2711059500",
      industry: "cafe",
      // 복원 검증(consultation-draft.isValidPlan)이 통과하도록 실제 계산 형태를 넣는다.
      baseline: { input: BASELINE, result: RESULT_BASELINE },
      current: { input: FINANCE, result: RESULT_CURRENT },
      selected: "current",
      change_reason: "월세가 낮은 자리로 바꿨습니다",
      profile: {
        business_registered: false,
        business_age_months: null,
        planned_opening_date: "2026-11-01",
        funds_needed_by: "2026-10-15",
        owner_age: 34,
        guarantee_status: "unknown",
        policy_confirmation_status: "in_progress",
      },
    };
    await page.goto(`${BASE_URL}/analysis`, { waitUntil: "domcontentloaded" });
    await page.evaluate((draft) => {
      sessionStorage.setItem("localhostdaegu.consultation.v1", JSON.stringify(draft));
    }, DRAFT);

    const query = new URLSearchParams({ region: "2711059500", industry: "cafe", finance: JSON.stringify(FINANCE) });
    await page.goto(`${BASE_URL}/analysis?${query.toString()}`, { waitUntil: "networkidle" });

    const postBodies = [];
    page.on("request", (req) => {
      if (req.method() === "POST" && req.url().endsWith("/analysis")) postBodies.push(req.postData());
    });

    const started = Date.now();
    await page.getByRole("button", { name: "분석 시작" }).click();

    // 진행 라벨은 내부 에이전트명이 아니라 사용자가 읽는 단계다(§3-1) — orchestrator = "입력 확인".
    await page
      .locator("li", { hasText: "입력 확인" })
      .filter({ hasText: "완료" })
      .waitFor({ state: "visible", timeout: REPORT_TIMEOUT_MS });
    step("상담자료 생성 완료", true, `${((Date.now() - started) / 1000).toFixed(1)}초`);

    step("분석 요청 베이스", postUrls[0] === EXPECTED_POST_URL, `${postUrls[0]} (기대 ${EXPECTED_POST_URL})`);

    const body = postBodies[0] ? JSON.parse(postBodies[0]) : {};
    step("purpose=handoff 로 요청", body.purpose === "handoff", String(body.purpose));
    step("선택안의 월세가 실렸다", body.finance && body.finance.monthly_rent === 1_500_000, String(body.finance?.monthly_rent));
    step("비교 원본을 함께 보냈다", body.consultation?.baseline_finance?.monthly_rent === 2_500_000);
    step("변경 이유가 실렸다", body.consultation?.change_reason === "월세가 낮은 자리로 바꿨습니다");
    step(
      "'모름'이 확인 목록에 남았다",
      (body.consultation?.open_questions ?? []).some((q) => q.includes("보증기관")),
      JSON.stringify(body.consultation?.open_questions ?? []),
    );

    for (const name of HANDOFF_HEADINGS) {
      step(`상담자료 섹션 "${name}"`, (await page.getByRole("heading", { name }).count()) > 0);
    }
    step("위험 판정 헤드라인 없음(§3-1)", (await page.getByRole("heading", { name: "종합 진단" }).count()) === 0);

    // 서버가 다시 계산한 수치인지 — 선택안(월세 150만) 기준 값이 계산표에 있어야 한다.
    const reportText = await page.locator(".report-markdown").allTextContents();
    const joined = reportText.join("\n");
    step("계산표에 조달 필요액 표기", /자기자본 외 조달 필요 [\d,]+원/.test(joined));
    step("미확보 희망대출 구분 표기", /희망대출 반영 후 남는 부족액 [\d,]+원/.test(joined));
    step("비교표에 최초안·현재안 두 열", /최초안/.test(joined) && /현재안/.test(joined));
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

    // 완성된 자료만 저장할 수 있다 — 외부 사이트는 조작하지 않고 버튼 상태·링크 주소만 본다.
    const saveButton = page.getByRole("button", { name: /상담자료 저장/ });
    step("상담자료 저장 버튼 활성", await saveButton.isEnabled());
    const officialHref = await page.getByRole("link", { name: /iM뱅크 공식 상담 안내/ }).first().getAttribute("href");
    step("공식 상담 링크", Boolean(officialHref && officialHref.includes("imbank.co.kr")), officialHref);
  } catch (err) {
    step("예외 발생", false, err && err.stack ? err.stack : String(err));
  } finally {
    if (browser) await browser.close().catch(() => {});
  }
  console.log(failed ? "RESULT: FAIL" : "RESULT: PASS");
  process.exit(failed ? 1 : 0);
}

main();
