import { beforeEach, expect, it } from "vitest";

import { POST } from "./route";
import { GET } from "./[id]/events/route";
import { rememberPurpose, takePurpose } from "../analysis-purpose";

async function readSections(response: Response): Promise<string[]> {
  const text = await response.text();
  return text
    .split("\n\n")
    .filter((block) => block.startsWith("event: report_delta"))
    .map((block) => JSON.parse(block.split("\ndata: ")[1]).section);
}

const post = (body: object) =>
  POST(new Request("http://localhost/api/mock/analysis", { method: "POST", body: JSON.stringify(body) }));

beforeEach(() => takePurpose("nonexistent"));

it("purpose 를 보내지 않으면 기존 review 스크립트가 나온다", async () => {
  const { analysis_id } = await (await post({ region: "2711059500", industry: "cafe" })).json();

  const sections = await readSections(await GET(new Request("http://localhost"), { params: { id: analysis_id } }));

  expect(sections).toEqual(["verdict", "market", "shock", "funding", "calculator"]);
});

it("purpose=handoff 면 상담자료 섹션이 나온다", async () => {
  const { analysis_id } = await (
    await post({ region: "2711059500", industry: "cafe", purpose: "handoff" })
  ).json();

  const sections = await readSections(await GET(new Request("http://localhost"), { params: { id: analysis_id } }));

  expect(sections).toEqual(["plan", "comparison", "calculator", "funding", "questions", "market"]);
});

it("목적은 한 번만 소비된다 — 실백엔드 저장소와 같은 규칙", () => {
  rememberPurpose("abc", "handoff");

  expect(takePurpose("abc")).toBe("handoff");
  expect(takePurpose("abc")).toBe("review");
});
