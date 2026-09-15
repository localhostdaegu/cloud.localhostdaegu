import { riskRankingByIndustry, riskRankingByRegion, riskScoreOf } from "../../fixtures";

/** 백엔드 실계약(GET /metrics/risk) 3형태를 모두 미러링:
 *  industry+region_code → 단건(없으면 404 RISK_NOT_FOUND) / industry만 → region 랭킹(A유형, 배열)
 *  / region_code만 → 업종별 랭킹(B유형, 배열) / 둘 다 없으면 400 RISK_QUERY_INVALID. */
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const industry = searchParams.get("industry");
  const regionCode = searchParams.get("region_code");

  if (industry && regionCode) {
    const score = riskScoreOf(regionCode, industry);
    if (!score) {
      return Response.json(
        {
          error: {
            code: "RISK_NOT_FOUND",
            message: `위험도 데이터 없음: region=${regionCode}, industry=${industry}`,
          },
        },
        { status: 404 },
      );
    }
    return Response.json(score);
  }

  if (industry) {
    return Response.json(riskRankingByIndustry(industry));
  }

  if (regionCode) {
    return Response.json(riskRankingByRegion(regionCode));
  }

  return Response.json(
    { error: { code: "RISK_QUERY_INVALID", message: "industry 또는 region_code 중 최소 하나는 필요합니다" } },
    { status: 400 },
  );
}
