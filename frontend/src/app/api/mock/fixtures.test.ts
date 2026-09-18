import { expect, it } from "vitest";
import { SEOUL_REGIONS_GEOJSON, metricRows, summaryOf, agentEventScript } from "./fixtures";

it("geojson feature마다 region_code·name이 있다", () => {
  expect(SEOUL_REGIONS_GEOJSON.features.length).toBeGreaterThanOrEqual(5);
  for (const f of SEOUL_REGIONS_GEOJSON.features)
    expect(f.properties).toMatchObject({ region_code: expect.any(String), name: expect.any(String) });
});
it("metricRows는 모든 feature의 region_code를 커버한다", () => {
  const codes = new Set(metricRows("closure_rate", 2026, "cafe").map((r) => r.region_code));
  for (const f of SEOUL_REGIONS_GEOJSON.features) expect(codes.has(f.properties!.region_code)).toBe(true);
});
it("metricRows는 industry가 다르면 값도 달라진다", () => {
  expect(metricRows("closure_rate", 2026, "cafe")).not.toEqual(metricRows("closure_rate", 2026, "gym"));
});
it("metricRows는 같은 (metric, year, industry)에 대해 결정적이다", () => {
  expect(metricRows("closure_rate", 2026, "cafe")).toEqual(metricRows("closure_rate", 2026, "cafe"));
});
it("summaryOf는 industry가 다르면 점포수·폐업률·성장률 카드 값도 달라진다", () => {
  const code = SEOUL_REGIONS_GEOJSON.features[0].properties!.region_code;
  const cafeCards = summaryOf(code, "cafe").cards.filter((c) => c.grade === "fact");
  const gymCards = summaryOf(code, "gym").cards.filter((c) => c.grade === "fact");
  expect(cafeCards).not.toEqual(gymCards);
});
it("이벤트 스크립트는 report_done으로 끝난다", () => {
  const script = agentEventScript();
  expect(script.at(-1)!.type).toBe("report_done");
});

// --- 전환계획 T4: mock 도 상담자료(handoff) 섹션을 내보낸다 ---------------

it("handoff 목적이면 상담자료 6섹션을 순서대로 낸다", () => {
  const sections = agentEventScript("handoff")
    .filter((e) => e.type === "report_delta")
    .map((e) => e.section);

  expect(sections).toEqual(["plan", "comparison", "calculator", "funding", "questions", "market"]);
});

it("handoff 에는 위험 판정·충격 섹션이 없다", () => {
  const sections = agentEventScript("handoff")
    .filter((e) => e.type === "report_delta")
    .map((e) => e.section);

  expect(sections).not.toContain("verdict");
  expect(sections).not.toContain("shock");
});

it("목적을 주지 않으면 기존 review 스크립트를 유지한다", () => {
  const sections = agentEventScript()
    .filter((e) => e.type === "report_delta")
    .map((e) => e.section);

  expect(sections).toEqual(["verdict", "market", "shock", "funding", "calculator"]);
});

it("handoff 계산표 수치는 재무 엔진 검산값이다", () => {
  const plan = agentEventScript("handoff").find(
    (e) => e.type === "report_delta" && e.section === "plan",
  );
  const comparison = agentEventScript("handoff").find(
    (e) => e.type === "report_delta" && e.section === "comparison",
  );

  // 월세 100만 안: 총 준비자금 6,260만 · 조달 필요 2,260만 · 부족액 0원
  expect(plan.markdown).toContain("62,600,000원");
  expect(plan.markdown).toContain("22,600,000원");
  // 월세 250만 최초안: 조달 필요 3,160만
  expect(comparison.markdown).toContain("31,600,000원");
});

it("handoff 진행 표시는 실제 도구 이름을 쓴다 — 진행 패널이 한국어 라벨로 바꾼다", () => {
  const tools = agentEventScript("handoff")
    .filter((e) => e.type === "tool_call")
    .map((e) => e.tool);

  expect(tools).toContain("finance_simulate");
  expect(tools).toContain("product_matching");
});
