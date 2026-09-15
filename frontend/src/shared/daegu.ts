export const DAEGU_CENTER: [number, number] = [128.60, 35.87];
export const DISTRICTS: Record<string, { name: string; center: [number, number] }> = {
  "27110": { name: "중구", center: [128.606, 35.869] },
  "27140": { name: "동구", center: [128.635, 35.887] },
  "27170": { name: "서구", center: [128.559, 35.872] },
  "27200": { name: "남구", center: [128.598, 35.846] },
  "27230": { name: "북구", center: [128.583, 35.885] },
  "27260": { name: "수성구", center: [128.630, 35.858] },
  "27290": { name: "달서구", center: [128.533, 35.830] },
  "27710": { name: "달성군", center: [128.431, 35.775] },
};
export const INDUSTRY_LABELS: Record<string, string> = {
  cafe: "카페·휴게음식점", restaurant: "일반음식점", hair_salon: "미용실",
  gym: "헬스장", billiard: "당구장", karaoke: "노래방", pc_bang: "PC방",
};
