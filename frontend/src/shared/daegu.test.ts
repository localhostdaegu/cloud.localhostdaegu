import { DAEGU_CENTER, DISTRICTS } from "./daegu";

test("daegu has 8 districts without gunwi", () => {
  expect(Object.keys(DISTRICTS)).toHaveLength(8);
  expect(DISTRICTS["27720"]).toBeUndefined();
  expect(DISTRICTS["27110"].name).toBe("중구");
});
test("center is in daegu bbox", () => {
  const [lng, lat] = DAEGU_CENTER;
  expect(lng).toBeGreaterThan(128.35); expect(lng).toBeLessThan(128.77);
  expect(lat).toBeGreaterThan(35.6); expect(lat).toBeLessThan(36.02);
});
