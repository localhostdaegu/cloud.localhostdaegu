import { agentEventScript } from "../../../fixtures";
import { takePurpose } from "../../../analysis-purpose";

const STEP_MS = process.env.VITEST ? 0 : 400; // 진행 패널 시연용 지연 — 테스트에서는 기다리지 않는다

export async function GET(_request: Request, context: { params: Promise<{ id: string }> | { id: string } }) {
  const { id } = await context.params;
  const script = agentEventScript(takePurpose(id));
  const stream = new ReadableStream({
    async start(controller) {
      const enc = new TextEncoder();
      for (const ev of script) {
        controller.enqueue(enc.encode(`event: ${ev.type}\ndata: ${JSON.stringify(ev)}\n\n`));
        if (STEP_MS) await new Promise((r) => setTimeout(r, STEP_MS));
      }
      controller.close();
    },
  });
  return new Response(stream, {
    headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" },
  });
}
