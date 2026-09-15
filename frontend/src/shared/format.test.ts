import { expect, it } from "vitest";
import { formatKrw } from "./format";

it("1억원 미만은 만원 단위 콤마 표기", () => {
  expect(formatKrw(20_000_000)).toBe("2,000만원");
});

it("1억원 이상은 억 단위 소수 1자리 표기", () => {
  expect(formatKrw(120_000_000)).toBe("1.2억원");
});

it("0원은 그대로 0원", () => {
  expect(formatKrw(0)).toBe("0원");
});

it("만원 미만 잔액은 절사한다", () => {
  expect(formatKrw(15_555_000)).toBe("1,555만원");
});

it("억 단위 경계값도 소수 1자리로 표기한다", () => {
  expect(formatKrw(100_000_000)).toBe("1.0억원");
});
