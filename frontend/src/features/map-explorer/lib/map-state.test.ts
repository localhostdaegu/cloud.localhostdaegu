import { expect, it } from "vitest";
import { parseMapState, serializeMapState, YEARS } from "./map-state";

it("YEARS는 2019~2026 8개년을 제공한다 (백엔드 지표 범위와 일치)", () => {
  expect(YEARS).toEqual([2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]);
});

it("기본값: 파라미터 없으면 industry=null(미지정)/closure_rate/2025(마지막 완결 연도)/null", () => {
  expect(parseMapState(new URLSearchParams())).toEqual({
    industry: null,
    metric: "closure_rate",
    year: 2025,
    region: null,
    district: null,
    budget: null,
  });
});

it("직렬화→파싱 라운드트립이 보존된다", () => {
  const s = {
    industry: "karaoke",
    metric: "growth_rate" as const,
    year: 2021,
    region: "1168051500",
    district: "27260",
    budget: 50_000_000,
  };
  expect(parseMapState(new URLSearchParams(serializeMapState(s)))).toEqual(s);
});

it("industry=restaurant는 기본값 강제 없이 라운드트립된다 (채팅→지도 음식점 깔때기)", () => {
  const s = {
    industry: "restaurant",
    metric: "closure_rate" as const,
    year: 2026,
    region: null,
    district: null,
    budget: null,
  };
  expect(parseMapState(new URLSearchParams(serializeMapState(s)))).toEqual(s);
});

it("알 수 없는 값은 기본값(미지정=null)으로 강제된다", () => {
  expect(parseMapState(new URLSearchParams("industry=hack&metric=x"))
    .industry).toBe(null);
});

it("district·budget은 없으면 URL에서 생략된다", () => {
  const s = { industry: "cafe", metric: "closure_rate" as const, year: 2026, region: null, district: null, budget: null };
  expect(serializeMapState(s)).not.toMatch(/district=|budget=/);
});

it("industry가 미지정(null)이면 URL에서 생략된다 — 기본값(cafe) 주입 금지", () => {
  const s = { industry: null, metric: "closure_rate" as const, year: 2026, region: null, district: null, budget: null };
  expect(serializeMapState(s)).not.toMatch(/industry=/);
});

it("C1: district만 있는 상태에서 region 선택(state 갱신)해도 industry가 URL에 주입되지 않는다 (B유형 도달성)", () => {
  // 채팅 랜딩에서 district만 넘어온 상태 — industry 없음.
  const initial = parseMapState(new URLSearchParams("district=27110"));
  expect(initial.industry).toBe(null);

  // 지도에서 region 클릭 시 map-page.handleSelectRegion과 동일하게 기존 state를 스프레드 + region만 갱신.
  const afterRegionClick = { ...initial, region: "1168051500" };
  const serialized = serializeMapState(afterRegionClick);

  expect(serialized).not.toMatch(/industry=/);
  expect(serialized).toMatch(/district=27110/);
  expect(serialized).toMatch(/region=1168051500/);

  // 라운드트립해도 industry는 여전히 미지정 — side-panel의 isRanking(industryParam===null) 조건이 계속 참일 수 있다.
  expect(parseMapState(new URLSearchParams(serialized)).industry).toBe(null);
});
