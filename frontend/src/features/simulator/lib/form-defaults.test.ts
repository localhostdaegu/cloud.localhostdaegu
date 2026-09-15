import { buildDefaults } from "./form-defaults";

test("budget from url becomes equity default", () => {
  const d = buildDefaults({ budget: "50000000", industry: "cafe" });
  expect(d.equity).toBe(50_000_000);
  expect(d.cost_ratio).toBe(0.35);           // 카페 기본 원가율
});
test("industry benchmark cost ratios", () => {
  expect(buildDefaults({ industry: "restaurant" }).cost_ratio).toBe(0.40);
  expect(buildDefaults({}).cost_ratio).toBe(0.40);   // 미지정 기본
});
