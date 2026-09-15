import { intentToUrl } from "./intent-url";

test("full intent A routes to map with all params", () => {
  expect(intentToUrl({ intent_type: "A", district_code: "27260", industry_slug: "rest_cafes",
    budget_krw: 50_000_000, missing: [] }))
    .toBe("/map?district=27260&industry=rest_cafes&budget=50000000");
});
test("type B omits industry", () => {
  expect(intentToUrl({ intent_type: "B", district_code: "27110", industry_slug: null,
    budget_krw: null, missing: ["industry", "budget"] }))
    .toBe("/map?district=27110");
});
test("type C without region stays on daegu overview", () => {
  expect(intentToUrl({ intent_type: "C", district_code: null, industry_slug: "rest_cafes",
    budget_krw: 50_000_000, missing: ["region"] }))
    .toBe("/map?industry=rest_cafes&budget=50000000");
});
