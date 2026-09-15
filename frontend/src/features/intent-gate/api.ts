import { apiPost } from "@/shared/api/client";
import type { IntentResult } from "./lib/intent-url";

/** 백엔드 계약: IntentResult + region_name (화면 표기용, intentToUrl은 소비하지 않음). */
export interface ParseIntentResult extends IntentResult {
  region_name: string | null;
}

export function parseIntent(text: string): Promise<ParseIntentResult> {
  return apiPost<ParseIntentResult>("/intent", { text });
}
