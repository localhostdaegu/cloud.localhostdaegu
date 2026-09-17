#!/usr/bin/env node
/** Responsive brand acceptance; uses the running server and one headless browser. */
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const { chromium } = require("playwright");

const BASE_URL = process.env.BASE_URL || "http://localhost:3300";
const OUTPUT = process.env.SCREENSHOT_DIR || path.join(os.tmpdir(), "localhostdaegu-mint-checks");

function contrast(first, second) {
  function luminance(color) {
    const channels = color.match(/[\d.]+/g).slice(0, 3).map(Number).map((value) => {
      const channel = value / 255;
      return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
    });
    return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
  }
  const [low, high] = [luminance(first), luminance(second)].sort((a, b) => a - b);
  return (high + 0.05) / (low + 0.05);
}

async function checkLayout(page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  assert.equal(overflow, false, "The page must not scroll horizontally");
  for (const name of ["지도 탐색", "AI 분석"]) {
    const link = page.locator("header").first().getByRole("link", { name, exact: true });
    assert.equal(await link.isVisible(), true, `${name} must remain accessible`);
    const lines = await link.evaluate((element) => {
      const tops = new Set();
      const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) {
        if (!walker.currentNode.textContent.trim()) continue;
        const range = document.createRange();
        range.selectNodeContents(walker.currentNode);
        for (const rect of range.getClientRects()) tops.add(Math.round(rect.top));
      }
      return tops.size;
    });
    assert.equal(lines, 1, `${name} must stay on one line`);
  }
  const disclaimerFits = await page.getByText("이해를 돕기 위한 지도 모식도입니다.", { exact: true }).evaluate((element) => {
    const text = element.getBoundingClientRect();
    const card = element.closest("article").getBoundingClientRect();
    return text.top >= card.top && text.bottom <= card.bottom && text.left >= card.left && text.right <= card.right;
  });
  assert.equal(disclaimerFits, true, "Map explanation must remain inside the visible card");
  const evidenceLink = page.getByRole("link", { name: "상권 지표 확인하기", exact: true });
  await evidenceLink.focus();
  await page.keyboard.press("Tab");
  await page.keyboard.press("Shift+Tab");
  const focus = await evidenceLink.evaluate((element) => {
    const style = getComputedStyle(element);
    return {
      active: element === document.activeElement,
      width: parseFloat(style.outlineWidth),
      color: style.outlineColor,
      background: getComputedStyle(element.closest("article")).backgroundColor,
    };
  });
  assert.equal(focus.active, true);
  assert.ok(focus.width >= 2 && contrast(focus.color, focus.background) >= 3, "Evidence link needs a contrasting keyboard outline");
  await page.evaluate(() => window.scrollTo(0, 0));
}

async function main() {
  await fs.mkdir(OUTPUT, { recursive: true });
  const response = await fetch(BASE_URL, { signal: AbortSignal.timeout(10_000) });
  assert.equal(response.ok, true, "Start the frontend on port 3300 before running acceptance");
  let browser;
  try {
    browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    for (const [width, height] of [[1440, 1000], [1024, 768], [390, 844], [320, 720]]) {
      await page.setViewportSize({ width, height });
      await page.goto(BASE_URL, { waitUntil: "networkidle" });
      await page.getByRole("heading", { level: 1, name: /대구에서 여는 내 가게/ }).waitFor();
      await page.evaluate(() => document.fonts.ready);
      await page.waitForFunction(() => {
        const pin = [...document.images].find((image) => image.currentSrc.includes("brand-pin"));
        return pin && pin.complete && pin.naturalWidth > 0;
      });
      assert.equal(await page.getByRole("button", { name: "찾아보기", exact: true }).isDisabled(), true);
      for (const theme of ["light", "dark"]) {
        if (theme === "dark") {
          await page.getByRole("button", { name: /테마 전환/ }).click();
          await page.waitForTimeout(200);
        }
        assert.equal(await page.locator("html").getAttribute("data-theme"), theme);
        await checkLayout(page);
        await page.screenshot({ path: path.join(OUTPUT, `home-${width}-${theme}.png`), fullPage: true });
        console.log(`[PASS] ${width}px ${theme}: heading, artwork, no overflow, navigation labels`);
      }
    }

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(BASE_URL, { waitUntil: "networkidle" });
    const input = page.getByRole("textbox", { name: "생각 중인 동네나 업종을 알려주세요" });
    await page.getByRole("button", { name: "서문시장 근처 카페, 예산 5천", exact: true }).click();
    assert.equal(await input.inputValue(), "서문시장 근처 카페, 예산 5천");
    await input.focus();
    assert.equal(await input.evaluate((element) => element === document.activeElement), true);
    await page.keyboard.press("Tab");
    assert.equal(await page.getByRole("button", { name: "찾아보기", exact: true }).evaluate((element) => element === document.activeElement), true);
    console.log("[PASS] Example question fills input; keyboard reaches submit");

    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.waitForTimeout(200);
    const running = await page.evaluate(() => document.getAnimations().filter((animation) => animation.playState === "running").length);
    assert.equal(running, 0, "Reduced-motion preference must stop decorative animations");
    assert.deepEqual(errors, [], "Home must not emit uncaught runtime errors");
    console.log(`[PASS] Reduced motion and runtime checks. Screenshots: ${OUTPUT}`);
  } finally {
    if (browser) await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
