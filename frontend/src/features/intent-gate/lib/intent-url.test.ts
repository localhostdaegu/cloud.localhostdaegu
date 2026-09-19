import { intentToUrl } from "./intent-url";

test("full intent A routes to map with all params", () => {
  expect(intentToUrl({ intent_type: "A", district_code: "27260", industry_id: "cafe",
    budget_krw: 50_000_000, missing: [] }))
    .toBe("/map?district=27260&industry=cafe&budget=50000000");
});
test("type B omits industry", () => {
  expect(intentToUrl({ intent_type: "B", district_code: "27110", industry_id: null,
    budget_krw: null, missing: ["industry", "budget"] }))
    .toBe("/map?district=27110");
});
test("type C without region stays on daegu overview", () => {
  expect(intentToUrl({ intent_type: "C", district_code: null, industry_id: "cafe",
    budget_krw: 50_000_000, missing: ["region"] }))
    .toBe("/map?industry=cafe&budget=50000000");
});

it("말한 동네의 행정동 코드가 있으면 region으로 실어 지도가 그 동을 바로 고르게 한다", () => {
  expect(
    intentToUrl({ intent_type: "A", district_code: "27110", region_code: "2711059500", industry_id: "cafe", budget_krw: null, missing: [] }),
  ).toBe("/map?district=27110&region=2711059500&industry=cafe");
});
