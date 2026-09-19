"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "./client";

export interface RegionName {
  code: string;
  name: string;
}

interface RegionFeatures {
  features: { properties: { region_code: string; name: string } }[];
}

const toNames = (geojson: RegionFeatures): RegionName[] =>
  geojson.features
    .map((f) => ({ code: f.properties.region_code, name: f.properties.name }))
    .sort((a, b) => a.name.localeCompare(b.name, "ko"));

/** 행정동 코드 ↔ 이름. 지도 경계와 같은 응답·같은 캐시 키(["geojson"])를 쓰므로 추가 요청이 생기지 않는다.
 *  화면에는 10자리 코드 대신 동 이름을 보여준다. */
export function useRegionNames(): RegionName[] {
  const { data } = useQuery({
    queryKey: ["geojson"],
    queryFn: () => apiGet<RegionFeatures>("/regions/geojson"),
    staleTime: Infinity,
    select: toNames,
  });
  return data ?? [];
}
