"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { MapView } from "./map-view";
import { ControlBar } from "./control-bar";
import { SidePanel } from "./side-panel";
import { DEFAULT_INDUSTRY, parseMapState, serializeMapState } from "../lib/map-state";
import type { MapState } from "../lib/map-state";

/** URL 파라미터와 상태를 연동. */
export function MapPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const state = parseMapState(searchParams);

  const handleStateChange = (nextState: MapState) => {
    router.replace(`?${serializeMapState(nextState)}`, { scroll: false });
  };

  const handleSelectRegion = (code: string) => {
    handleStateChange({ ...state, region: code });
  };

  const handleSelectIndustry = (industry: string) => {
    handleStateChange({ ...state, industry });
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <ControlBar state={state} onChange={handleStateChange} />
      <div className="flex min-h-0 flex-1">
        <div className="min-w-0 flex-1 overflow-hidden">
          <MapView
            regionCode={state.region}
            metric={state.metric}
            industry={state.industry ?? DEFAULT_INDUSTRY}
            year={state.year}
            district={state.district}
            onSelectRegion={handleSelectRegion}
          />
        </div>
        <SidePanel
          regionCode={state.region}
          industry={state.industry ?? DEFAULT_INDUSTRY}
          industryParam={searchParams.get("industry")}
          onSelectIndustry={handleSelectIndustry}
          searchParams={searchParams.toString()}
        />
      </div>
    </div>
  );
}
