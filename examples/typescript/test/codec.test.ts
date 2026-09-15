import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  Opcode,
  HeaderFlags,
  ErrorCode,
  FinishReason,
  ErrorScope,
  encodeHeader,
  decodeHeader,
  encodeFrame,
  decodeFrame,
  encodeSettings,
  decodeSettings,
  encodePingPong,
  decodePingPong,
  encodeOpenAck,
  decodeOpenAck,
  encodeContent,
  decodeContent,
  encodeToolCall,
  decodeToolCall,
  encodeUsage,
  decodeUsage,
  encodeMetrics,
  decodeMetrics,
  encodeEnd,
  decodeEnd,
  encodeError,
  decodeError,
  encodeSteer,
  decodeSteer,
  encodeRewind,
  decodeRewind,
  LMStreamError,
} from "../src/index.js";

describe("LMStream Frame Codec", () => {
  it("encodes and decodes valid frame header", () => {
    const header = { streamId: 1, opcode: Opcode.CONTENT, flags: HeaderFlags.BOUNDARY, length: 5 };
    const bytes = encodeHeader(header);
    assert.equal(bytes.length, 8);
    const decoded = decodeHeader(bytes);
    assert.deepEqual(decoded, header);
  });

  it("rejects reserved flags", () => {
    const header = { streamId: 1, opcode: Opcode.CONTENT, flags: 0x02, length: 0 };
    const bytes = encodeHeader(header);
    assert.throws(() => decodeHeader(bytes), (err: any) => err.code === ErrorCode.PROTOCOL_VIOLATION);
  });

  it("rejects unknown core opcode", () => {
    const buf = new Uint8Array(8);
    const view = new DataView(buf.buffer);
    view.setUint32(0, 1, true);
    view.setUint8(4, 0x25); // unknown core opcode
    assert.throws(() => decodeHeader(buf), (err: any) => err.code === ErrorCode.PROTOCOL_VIOLATION);
  });

  it("round-trips full frame", () => {
    const payload = new Uint8Array([0, 65, 66, 67]); // choice 0 + "ABC"
    const frame = {
      header: { streamId: 1, opcode: Opcode.CONTENT, flags: 1, length: payload.length },
      payload,
    };
    const bytes = encodeFrame(frame);
    assert.equal(bytes.length, 12);
    const decoded = decodeFrame(bytes);
    assert.deepEqual(decoded.header, frame.header);
    assert.deepEqual(decoded.payload, payload);
  });
});

describe("LMStream Payload Codecs", () => {
  it("round-trips SETTINGS", () => {
    const s = {
      version: 1,
      maxFrameSize: 65535,
      pauseBufferCap: 1048576,
      heartbeatMs: 15000,
      maxConcurrentSessions: 100,
    };
    const b = encodeSettings(s);
    assert.equal(b.length, 18);
    assert.deepEqual(decodeSettings(b), s);
  });

  it("round-trips PING / PONG", () => {
    const p = { timestampMs: 1700000000000n };
    const b = encodePingPong(p);
    assert.equal(b.length, 8);
    assert.deepEqual(decodePingPong(b), p);
  });

  it("round-trips OPEN_ACK", () => {
    const p = { sessionId: 1, model: "gpt-4o" };
    const b = encodeOpenAck(p);
    assert.deepEqual(decodeOpenAck(b), p);
  });

  it("round-trips CONTENT", () => {
    const p = { choiceIndex: 0, text: "Hello, world! 🌍" };
    const b = encodeContent(p);
    assert.deepEqual(decodeContent(b), p);
  });

  it("round-trips single-frame TOOL_CALL", () => {
    const p = {
      choiceIndex: 0,
      callIndex: 0,
      flags: 5,
      id: "call_123",
      name: "get_weather",
      argsDelta: '{"city":"NYC"}',
    };
    const b = encodeToolCall(p);
    assert.deepEqual(decodeToolCall(b), p);
  });

  it("round-trips USAGE", () => {
    const p = {
      promptTokens: 150,
      completionTokens: 42,
      totalTokens: 192,
      cachedTokens: 20,
      attemptCount: 1,
    };
    const b = encodeUsage(p);
    assert.equal(b.length, 20);
    assert.deepEqual(decodeUsage(b), p);
  });

  it("round-trips METRICS", () => {
    const p = {
      ttftMs: 45,
      totalDurationMs: 230,
      tokensPerSec: 8550,
      obfuscatedKeyId: 0x1234567890abcdefn,
    };
    const b = encodeMetrics(p);
    assert.equal(b.length, 20);
    assert.deepEqual(decodeMetrics(b), p);
  });

  it("round-trips END", () => {
    const p = { finishReason: FinishReason.STOP, choiceIndex: 0 };
    const b = encodeEnd(p);
    assert.equal(b.length, 2);
    assert.deepEqual(decodeEnd(b), p);
  });

  it("round-trips ERROR", () => {
    const p = {
      code: ErrorCode.RATE_LIMITED,
      upstreamStatus: 429,
      choiceIndex: 0,
      scope: ErrorScope.SESSION,
      message: "Rate limit exceeded",
    };
    const b = encodeError(p);
    assert.deepEqual(decodeError(b), p);
  });

  it("round-trips STEER", () => {
    const p = { text: "be concise" };
    const b = encodeSteer(p);
    assert.deepEqual(decodeSteer(b), p);
  });

  it("round-trips REWIND", () => {
    const p = { targetOpcode: Opcode.CONTENT, choiceIndex: 0, byteOffset: 48 };
    const b = encodeRewind(p);
    assert.equal(b.length, 8);
    assert.deepEqual(decodeRewind(b), p);
  });
});
