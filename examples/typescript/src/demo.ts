import { startWsServer, WS_PORT } from "./mock-server.js";
import { decodeFrame, encodeFrame, Opcode } from "./codec/index.js";
import { LMStreamSession } from "./client.js";

async function runDemo() {
  console.log("Starting LMStream WebSocket Demo...");
  const server = startWsServer(WS_PORT);

  // Allow server socket to bind
  await new Promise((r) => setTimeout(r, 150));

  const ws = new (WebSocket as any)(`ws://127.0.0.1:${WS_PORT}`, ["lmstream-v1"]);
  ws.binaryType = "arraybuffer";

  const session = new LMStreamSession(1);

  await new Promise<void>((resolve, reject) => {
    ws.onopen = () => {
      console.log("✓ WebSocket connected with subprotocol 'lmstream-v1'");
      // Emit OPEN frame on StreamID 1
      const openPayload = new TextEncoder().encode(JSON.stringify({ model: "gpt-4o" }));
      const openFrame = encodeFrame({
        header: { streamId: 1, opcode: Opcode.OPEN, flags: 0, length: 0 },
        payload: openPayload,
      });
      ws.send(openFrame);
    };

    ws.onmessage = async (event: any) => {
      let data = event.data;
      if (data instanceof Blob) {
        data = await data.arrayBuffer();
      }
      const bytes = new Uint8Array(data);
      const frame = decodeFrame(bytes);

      if (frame.header.streamId === 0) {
        console.log(`✓ Received connection frame: Opcode 0x${frame.header.opcode.toString(16)} on StreamID 0`);
        return;
      }

      session.handleFrame(frame);

      if (frame.header.opcode === Opcode.END) {
        console.log("✓ Received terminal END frame!");
        ws.close();
        resolve();
      }
    };

    ws.onerror = reject;
  });

  // Verify assertions against golden scenario transcript
  console.log("\nVerifying golden transcript assertions:");
  console.log(`- Reasoning: "${session.reasoningAccumulator}"`);
  if (session.reasoningAccumulator !== "Checking weather...") {
    throw new Error(`Reasoning mismatch: got "${session.reasoningAccumulator}"`);
  }

  console.log(`- Tool Calls: ${session.completedTools.length} completed`);
  if (session.completedTools.length !== 1 || session.completedTools[0].name !== "get_weather") {
    throw new Error("Tool call validation failed");
  }
  if (session.completedTools[0].arguments.city !== "Paris") {
    throw new Error(`Tool argument mismatch: ${JSON.stringify(session.completedTools[0].arguments)}`);
  }

  console.log(`- Content: "${session.contentAccumulator}"`);
  if (session.contentAccumulator !== "The weather in Paris is 18°C and sunny.") {
    throw new Error(`Content mismatch: got "${session.contentAccumulator}"`);
  }

  console.log(`- Total Tokens: ${session.usage?.totalTokens}`);
  if (session.usage?.totalTokens !== 39) {
    throw new Error(`Usage mismatch: got ${session.usage?.totalTokens}`);
  }

  console.log(`- Tok/s Metric: ${session.metrics?.tokensPerSec}`);
  if (session.metrics?.tokensPerSec !== 9200) {
    throw new Error(`Metrics mismatch: got ${session.metrics?.tokensPerSec}`);
  }

  console.log("\nAll WebSocket demo assertions passed successfully!");
  (server as any).closeAllConnections?.();
  server.close();
  process.exit(0);
}

runDemo().catch((err) => {
  console.error("Demo failed:", err);
  process.exit(1);
});
