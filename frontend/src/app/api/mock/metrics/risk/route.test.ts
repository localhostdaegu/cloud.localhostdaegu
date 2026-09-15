import { expect, it } from "vitest";
import { GET } from "./route";

const REGION = "2711051000";

it("industry+region_code 단건은 200과 {region_code,score,grade,components}를 반환한다", async () => {
  const res = await GET(new Request(`http://test/api/mock/metrics/risk?industry=cafe&region_code=${REGION}`));
  expect(res.status).toBe(200);
  expect(await res.json()).toMatchObject({
    region_code: REGION,
    score: expect.any(Number),
    grade: expect.stringMatching(/^(red|yellow|green)$/),
    components: { closure: expect.any(Number), density: expect.any(Number), growth: expect.any(Number) },
  });
});

it("데이터 없는 region×industry 단건은 200이 아니라 404 RISK_NOT_FOUND를 반환한다 (에러 배너 아닌 '데이터 없음' 케이스)", async () => {
  const res = await GET(
    new Request("http://test/api/mock/metrics/risk?industry=cafe&region_code=9999999999"),
  );
  expect(res.status).toBe(404);
  expect((await res.json()).error.code).toBe("RISK_NOT_FOUND");
});

it("industry만 지정하면 전 region 랭킹을 score 내림차순 배열로 반환한다 (A유형)", async () => {
  const res = await GET(new Request("http://test/api/mock/metrics/risk?industry=cafe"));
  expect(res.status).toBe(200);
  const body = await res.json();
  expect(body.length).toBeGreaterThan(0);
  expect(body[0]).toMatchObject({ region_code: expect.any(String), score: expect.any(Number) });
  const scores = body.map((r: { score: number }) => r.score);
  expect(scores).toEqual([...scores].sort((a, b) => b - a));
});

it("region_code만 지정하면 업종별 랭킹을 score 내림차순 배열로 반환한다 (B유형)", async () => {
  const res = await GET(new Request(`http://test/api/mock/metrics/risk?region_code=${REGION}`));
  expect(res.status).toBe(200);
  const body = await res.json();
  expect(body.length).toBeGreaterThan(0);
  expect(body[0]).toMatchObject({ industry_id: expect.any(String), score: expect.any(Number) });
  const scores = body.map((r: { score: number }) => r.score);
  expect(scores).toEqual([...scores].sort((a, b) => b - a));
});

it("지원하지 않는 industry는 배열 폼에서 500이 아니라 200 빈 배열을 반환한다 (카탈로그 미검증)", async () => {
  const res = await GET(new Request("http://test/api/mock/metrics/risk?industry=unknown_industry"));
  expect(res.status).toBe(200);
  expect(await res.json()).toEqual([]);
});

it("둘 다 미지정이면 400 RISK_QUERY_INVALID를 반환한다", async () => {
  const res = await GET(new Request("http://test/api/mock/metrics/risk"));
  expect(res.status).toBe(400);
  expect((await res.json()).error.code).toBe("RISK_QUERY_INVALID");
});
