import * as path from "node:path";
import { fileURLToPath } from "node:url";
import * as grpc from "@grpc/grpc-js";
import * as protoLoader from "@grpc/proto-loader";
import { startGrpcServer, GRPC_PORT } from "./mock-server.js";
import { encodeFrame, decodeFrame, Opcode } from "./codec/index.js";
import { LMStreamSession } from "./client.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, "../../../..");
const protoPath = path.join(rootDir, "bindings/lmstream.proto");

async function runGrpcDemo() {
  console.log("Starting LMStream gRPC Demo...");
  const server = startGrpcServer(GRPC_PORT);

  // Allow server to bind
  await new Promise((r) => setTimeout(r, 200));

  const packageDef = protoLoader.loadSync(protoPath, {
    keepCase: true,
    longs: String,
    enums: String,
    defaults: true,
    oneofs: true,
  });
  const proto = (grpc.loadPackageDefinition(packageDef) as any).lmstream.v1;
  const client = new proto.LMStream(`127.0.0.1:${GRPC_PORT}`, grpc.credentials.createInsecure());

  // 1. Open Control stream
  console.log("Calling Control RPC...");
  const controlCall = client.Control();
  await new Promise<void>((resolve, reject) => {
    controlCall.on("data", (msg: any) => {
      const frame = decodeFrame(new Uint8Array(msg.frame));
      console.log(`✓ Received on Control RPC: Opcode 0x${frame.header.opcode.toString(16)} on StreamID ${frame.header.streamId}`);
      if (frame.header.opcode === Opcode.SETTINGS) {
        resolve();
      }
    });
    controlCall.on("error", reject);
  });

  // 2. Open Session RPC
  console.log("Calling Session RPC on StreamID 1...");
  const session = new LMStreamSession(1);
  const sessionCall = client.Session();

  await new Promise<void>((resolve, reject) => {
    sessionCall.on("data", (msg: any) => {
      const frame = decodeFrame(new Uint8Array(msg.frame));
      session.handleFrame(frame);
      if (frame.header.opcode === Opcode.END) {
        console.log("✓ Received terminal END frame on gRPC Session!");
        resolve();
      }
    });
    sessionCall.on("error", reject);

    // Send OPEN frame
    const openPayload = new TextEncoder().encode(JSON.stringify({ model: "gpt-4o" }));
    const openFrame = encodeFrame({
      header: { streamId: 1, opcode: Opcode.OPEN, flags: 0, length: 0 },
      payload: openPayload,
    });
    sessionCall.write({ frame: Buffer.from(openFrame) });
  });

  // Assert golden transcript
  console.log("\nVerifying gRPC session assertions:");
  console.log(`- Reasoning: "${session.reasoningAccumulator}"`);
  console.log(`- Tool Calls: ${session.completedTools.length}`);
  console.log(`- Content: "${session.contentAccumulator}"`);
  console.log(`- Total Tokens: ${session.usage?.totalTokens}`);
  console.log(`- Tok/s Metric: ${session.metrics?.tokensPerSec}`);

  if (
    session.reasoningAccumulator !== "Checking weather..." ||
    session.completedTools.length !== 1 ||
    session.completedTools[0].name !== "get_weather" ||
    session.contentAccumulator !== "The weather in Paris is 18°C and sunny." ||
    session.usage?.totalTokens !== 39 ||
    session.metrics?.tokensPerSec !== 9200
  ) {
    throw new Error("gRPC scenario assertions failed!");
  }

  console.log("\nAll gRPC demo assertions passed successfully!");
  controlCall.end();
  sessionCall.end();
  server.forceShutdown();
  process.exit(0);
}

runGrpcDemo().catch((err) => {
  console.error("gRPC Demo failed:", err);
  process.exit(1);
});
