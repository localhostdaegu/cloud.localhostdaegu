import { expect, it } from "vitest";
import { manwonToWon, wonToManwon } from "./money";

it("원 단위 값을 만원 단위로 표시하고, 경계값(0)을 포함해 원 단위로 되돌린다", () => {
  expect(wonToManwon(50_000_000)).toBe(5000);
  expect(manwonToWon(5000)).toBe(50_000_000);
  expect(wonToManwon(0)).toBe(0);
  expect(manwonToWon(0)).toBe(0);
});
