import * as http from "node:http";
import * as crypto from "node:crypto";
import * as path from "node:path";
import * as fs from "node:fs";
import { fileURLToPath } from "node:url";
import * as grpc from "@grpc/grpc-js";
import * as protoLoader from "@grpc/proto-loader";
import {
  Opcode,
  HeaderFlags,
  encodeHeader,
  encodeFrame,
  decodeFrame,
  encodeSettings,
  encodeOpenAck,
  encodeContent,
  encodeToolCall,
  encodeUsage,
  encodeMetrics,
  encodeEnd,
  encodeRewind,
  FinishReason,
  ToolFlags,
} from "./codec/index.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, "../../../..");
const protoPath = path.join(rootDir, "bindings/lmstream.proto");

export const WS_PORT = 9123;
export const GRPC_PORT = 9124;

// Scripted scenario 1 transcript frames generator
export function getScenarioTranscript(sessionId: number): Uint8Array[] {
  return [
    // 1. OPEN_ACK
    encodeFrame({
      header: { streamId: sessionId, opcode: Opcode.OPEN_ACK, flags: 0, length: 0 },
      payload: encodeOpenAck({ sessionId, model: "gpt-4o" }),
    }),
    // 2. REASONING
    encodeFrame({
      header: { streamId: sessionId, opcode: Opcode.REASONING, flags: HeaderFlags.BOUNDARY, length: 0 },
      payload: encodeContent({ choiceIndex: 0, text: "Checking weather..." }),
    }),
    // 3. TOOL_CALL START
    encodeFrame({
      header: { streamId: sessionId, opcode: Opcode.TOOL_CALL, flags: 0, length: 0 },
      payload: encodeToolCall({
        choiceIndex: 0,
        callIndex: 0,
        flags: ToolFlags.START,
        id: "call_1",
        name: "get_weather",
        argsDelta: '{"city":',
      }),
    }),
    // 4. TOOL_CALL END
    encodeFrame({
      header: { streamId: sessionId, opcode: Opcode.TOOL_CALL, flags: 0, length: 0 },
      payload: encodeToolCall({
        choiceIndex: 0,
        callIndex: 0,
        flags: ToolFlags.END,
        argsDelta: '"Paris"}',
      }),
    }),
    // 5. CONTENT (simulating answer after tool result)
    encodeFrame({
      header: { streamId: sessionId, opcode: Opcode.CONTENT, flags: HeaderFlags.BOUNDARY, length: 0 },
      payload: encodeContent({ choiceIndex: 0, text: "The weather in Paris is 18°C and sunny." }),
    }),
    // 6. USAGE
    encodeFrame({
      header: { streamId: sessionId, opcode: Opcode.USAGE, flags: 0, length: 0 },
      payload: encodeUsage({
        promptTokens: 25,
        completionTokens: 14,
        totalTokens: 39,
        cachedTokens: 0,
        attemptCount: 1,
      }),
    }),
    // 7. METRICS
    encodeFrame({
      header: { streamId: sessionId, opcode: Opcode.METRICS, flags: 0, length: 0 },
      payload: encodeMetrics({
        ttftMs: 95,
        totalDurationMs: 340,
        tokensPerSec: 9200,
        obfuscatedKeyId: 0x1122334455667788n,
      }),
    }),
    // 8. END
    encodeFrame({
      header: { streamId: sessionId, opcode: Opcode.END, flags: 0, length: 0 },
      payload: encodeEnd({ finishReason: FinishReason.STOP, choiceIndex: 0 }),
    }),
  ];
}

// Lightweight RFC 6455 WebSocket Server using Node HTTP/Net stdlib
export function startWsServer(port: number): http.Server {
  const server = http.createServer((req, res) => {
    res.writeHead(200, { "Content-Type": "text/plain" });
    res.end("LMStream Mock Server");
  });

  server.on("upgrade", (req, socket, head) => {
    const subproto = req.headers["sec-websocket-protocol"];
    if (!subproto || !subproto.includes("lmstream-v1")) {
      socket.write("HTTP/1.1 400 Bad Request\r\n\r\n");
      socket.destroy();
      return;
    }

    const key = req.headers["sec-websocket-key"];
    const hash = crypto
      .createHash("sha1")
      .update(key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11")
      .digest("base64");

    socket.write(
      "HTTP/1.1 101 Switching Protocols\r\n" +
        "Upgrade: websocket\r\n" +
        "Connection: Upgrade\r\n" +
        "Sec-WebSocket-Protocol: lmstream-v1\r\n" +
        `Sec-WebSocket-Accept: ${hash}\r\n\r\n`
    );

    function sendWsBinary(data: Uint8Array) {
      const len = data.length;
      let header: Buffer;
      if (len < 126) {
        header = Buffer.from([0x82, len]);
      } else if (len < 65536) {
        header = Buffer.alloc(4);
        header[0] = 0x82;
        header[1] = 126;
        header.writeUInt16BE(len, 2);
      } else {
        header = Buffer.alloc(10);
        header[0] = 0x82;
        header[1] = 127;
        header.writeBigUInt64BE(BigInt(len), 2);
      }
      socket.write(Buffer.concat([header, Buffer.from(data)]));
    }

    // Immediately send server SETTINGS on StreamID 0
    const settingsFrame = encodeFrame({
      header: { streamId: 0, opcode: Opcode.SETTINGS, flags: 0, length: 0 },
      payload: encodeSettings({
        version: 1,
        maxFrameSize: 65535,
        pauseBufferCap: 1048576,
        heartbeatMs: 15000,
        maxConcurrentSessions: 100,
      }),
    });
    sendWsBinary(settingsFrame);

    let rxBuf = Buffer.alloc(0);
    socket.on("data", (chunk) => {
      rxBuf = Buffer.concat([rxBuf, chunk]);
      while (rxBuf.length >= 2) {
        const masked = (rxBuf[1] & 0x80) !== 0;
        let payloadLen = rxBuf[1] & 0x7f;
        let offset = 2;

        if (payloadLen === 126) {
          if (rxBuf.length < 4) break;
          payloadLen = rxBuf.readUInt16BE(2);
          offset = 4;
        } else if (payloadLen === 127) {
          if (rxBuf.length < 10) break;
          payloadLen = Number(rxBuf.readBigUInt64BE(2));
          offset = 10;
        }

        const maskKeyLen = masked ? 4 : 0;
        if (rxBuf.length < offset + maskKeyLen + payloadLen) break;

        let payload = rxBuf.subarray(offset + maskKeyLen, offset + maskKeyLen + payloadLen);
        if (masked) {
          const maskKey = rxBuf.subarray(offset, offset + 4);
          payload = Buffer.from(payload);
          for (let i = 0; i < payload.length; i++) {
            payload[i] ^= maskKey[i % 4];
          }
        }

        rxBuf = rxBuf.subarray(offset + maskKeyLen + payloadLen);

        // Process LMStream frame
        try {
          const frame = decodeFrame(new Uint8Array(payload));
          if (frame.header.opcode === Opcode.OPEN) {
            // Stream scenario transcript
            const frames = getScenarioTranscript(frame.header.streamId);
            for (const f of frames) {
              sendWsBinary(f);
            }
          } else if (frame.header.opcode === Opcode.PING) {
            // Echo PONG
            const pong = encodeFrame({
              header: { streamId: 0, opcode: Opcode.PONG, flags: 0, length: 8 },
              payload: frame.payload,
            });
            sendWsBinary(pong);
          }
        } catch (err: any) {
          console.error("Mock server frame error:", err);
        }
      }
    });
  });

  server.listen(port);
  return server;
}

// gRPC Server implementing lmstream.v1.LMStream
export function startGrpcServer(port: number): grpc.Server {
  const packageDef = protoLoader.loadSync(protoPath, {
    keepCase: true,
    longs: String,
    enums: String,
    defaults: true,
    oneofs: true,
  });
  const proto = (grpc.loadPackageDefinition(packageDef) as any).lmstream.v1;
  const server = new grpc.Server();

  server.addService(proto.LMStream.service, {
    Control: (call: any) => {
      // First send SETTINGS on StreamID 0
      const settings = encodeFrame({
        header: { streamId: 0, opcode: Opcode.SETTINGS, flags: 0, length: 0 },
        payload: encodeSettings({
          version: 1,
          maxFrameSize: 65535,
          pauseBufferCap: 1048576,
          heartbeatMs: 15000,
          maxConcurrentSessions: 100,
        }),
      });
      call.write({ frame: Buffer.from(settings) });

      call.on("data", (msg: any) => {
        const frame = decodeFrame(new Uint8Array(msg.frame));
        if (frame.header.opcode === Opcode.PING) {
          const pong = encodeFrame({
            header: { streamId: 0, opcode: Opcode.PONG, flags: 0, length: 8 },
            payload: frame.payload,
          });
          call.write({ frame: Buffer.from(pong) });
        }
      });
      call.on("end", () => call.end());
    },

    Session: (call: any) => {
      call.on("data", (msg: any) => {
        const frame = decodeFrame(new Uint8Array(msg.frame));
        if (frame.header.opcode === Opcode.OPEN) {
          const transcript = getScenarioTranscript(frame.header.streamId);
          for (const f of transcript) {
            call.write({ frame: Buffer.from(f) });
          }
          call.end();
        }
      });
    },
  });

  server.bindAsync(`0.0.0.0:${port}`, grpc.ServerCredentials.createInsecure(), (err, boundPort) => {
    if (err) throw err;
    console.log(`Mock gRPC server running on port ${boundPort}`);
  });

  return server;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  startWsServer(WS_PORT);
  console.log(`Mock WebSocket server running on port ${WS_PORT}`);
  startGrpcServer(GRPC_PORT);
}
