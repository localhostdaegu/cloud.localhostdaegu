import { Suspense } from "react";
import { SimulatorPage } from "@/features/simulator/components/simulator-page";
import { RouteFallback } from "@/shared/ui/route-fallback";

export default function Page() {
  return (
    <Suspense fallback={<RouteFallback label="시뮬레이터를 불러오는 중" />}>
      <SimulatorPage />
    </Suspense>
  );
}
