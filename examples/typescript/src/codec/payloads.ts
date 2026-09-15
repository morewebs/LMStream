import { Opcode, ToolFlags, FinishReason, ErrorCode, ErrorScope } from "./enums.js";
import { LMStreamError } from "./frame.js";

const encoder = new TextEncoder();
const decoder = new TextDecoder();

export interface SettingsPayload {
  version: number;
  maxFrameSize: number;
  pauseBufferCap: number;
  heartbeatMs: number;
  maxConcurrentSessions: number;
}

export function encodeSettings(p: SettingsPayload): Uint8Array {
  const buf = new Uint8Array(18);
  const view = new DataView(buf.buffer);
  view.setUint8(0, p.version);
  view.setUint32(1, p.maxFrameSize, true);
  view.setUint32(5, p.pauseBufferCap, true);
  view.setUint32(9, p.heartbeatMs, true);
  view.setUint16(13, p.maxConcurrentSessions, true);
  view.setUint8(15, 0); // reserved
  view.setUint16(16, 0, true); // reserved
  return buf;
}

export function decodeSettings(bytes: Uint8Array): SettingsPayload {
  if (bytes.length !== 18) {
    throw new LMStreamError(
      ErrorCode.PROTOCOL_VIOLATION,
      "connection",
      `SETTINGS payload must be exactly 18 bytes, got ${bytes.length}`
    );
  }
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const version = view.getUint8(0);
  const maxFrameSize = view.getUint32(1, true);
  const pauseBufferCap = view.getUint32(5, true);
  const heartbeatMs = view.getUint32(9, true);
  const maxConcurrentSessions = view.getUint16(13, true);
  return { version, maxFrameSize, pauseBufferCap, heartbeatMs, maxConcurrentSessions };
}

export interface PingPongPayload {
  timestampMs: bigint;
}

export function encodePingPong(p: PingPongPayload): Uint8Array {
  const buf = new Uint8Array(8);
  const view = new DataView(buf.buffer);
  view.setBigUint64(0, p.timestampMs, true);
  return buf;
}

export function decodePingPong(bytes: Uint8Array): PingPongPayload {
  if (bytes.length !== 8) {
    throw new LMStreamError(
      ErrorCode.PROTOCOL_VIOLATION,
      "connection",
      `PING/PONG payload must be exactly 8 bytes, got ${bytes.length}`
    );
  }
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  return { timestampMs: view.getBigUint64(0, true) };
}

export interface OpenAckPayload {
  sessionId: number;
  model: string;
}

export function encodeOpenAck(p: OpenAckPayload): Uint8Array {
  const modelBytes = encoder.encode(p.model);
  const buf = new Uint8Array(6 + modelBytes.length);
  const view = new DataView(buf.buffer);
  view.setUint32(0, p.sessionId, true);
  view.setUint16(4, modelBytes.length, true);
  buf.set(modelBytes, 6);
  return buf;
}

export function decodeOpenAck(bytes: Uint8Array): OpenAckPayload {
  if (bytes.length < 6) {
    throw new LMStreamError(
      ErrorCode.PROTOCOL_VIOLATION,
      "connection",
      `OPEN_ACK payload too short: ${bytes.length}`
    );
  }
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const sessionId = view.getUint32(0, true);
  const modelLen = view.getUint16(4, true);
  if (bytes.length < 6 + modelLen) {
    throw new LMStreamError(
      ErrorCode.PROTOCOL_VIOLATION,
      "connection",
      `Truncated model name in OPEN_ACK`
    );
  }
  const model = decoder.decode(bytes.subarray(6, 6 + modelLen));
  return { sessionId, model };
}

export interface ContentPayload {
  choiceIndex: number;
  text: string;
}

export function encodeContent(p: ContentPayload): Uint8Array {
  const textBytes = encoder.encode(p.text);
  const buf = new Uint8Array(1 + textBytes.length);
  buf[0] = p.choiceIndex;
  buf.set(textBytes, 1);
  return buf;
}

export function decodeContent(bytes: Uint8Array): ContentPayload {
  if (bytes.length < 1) {
    throw new LMStreamError(
      ErrorCode.PROTOCOL_VIOLATION,
      "connection",
      "CONTENT payload missing ChoiceIndex"
    );
  }
  const choiceIndex = bytes[0];
  const text = decoder.decode(bytes.subarray(1));
  return { choiceIndex, text };
}

export interface ToolCallPayload {
  choiceIndex: number;
  callIndex: number;
  flags: number;
  id?: string;
  name?: string;
  argsDelta: string;
}

export function encodeToolCall(p: ToolCallPayload): Uint8Array {
  const isStart = (p.flags & ToolFlags.START) !== 0;
  if (isStart) {
    const idBytes = encoder.encode(p.id ?? "");
    const nameBytes = encoder.encode(p.name ?? "");
    const argsBytes = encoder.encode(p.argsDelta);
    const buf = new Uint8Array(7 + idBytes.length + nameBytes.length + argsBytes.length);
    const view = new DataView(buf.buffer);
    buf[0] = p.choiceIndex;
    view.setUint16(1, p.callIndex, true);
    buf[3] = p.flags;
    buf[4] = idBytes.length;
    view.setUint16(5, nameBytes.length, true);
    buf.set(idBytes, 7);
    buf.set(nameBytes, 7 + idBytes.length);
    buf.set(argsBytes, 7 + idBytes.length + nameBytes.length);
    return buf;
  } else {
    const argsBytes = encoder.encode(p.argsDelta);
    const buf = new Uint8Array(4 + argsBytes.length);
    const view = new DataView(buf.buffer);
    buf[0] = p.choiceIndex;
    view.setUint16(1, p.callIndex, true);
    buf[3] = p.flags;
    buf.set(argsBytes, 4);
    return buf;
  }
}

export function decodeToolCall(bytes: Uint8Array): ToolCallPayload {
  if (bytes.length < 4) {
    throw new LMStreamError(
      ErrorCode.PROTOCOL_VIOLATION,
      "connection",
      "TOOL_CALL payload too short"
    );
  }
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const choiceIndex = bytes[0];
  const callIndex = view.getUint16(1, true);
  const flags = bytes[3];

  if ((flags & ToolFlags.RESERVED_MASK) !== 0) {
    throw new LMStreamError(
      ErrorCode.PROTOCOL_VIOLATION,
      "connection",
      `TOOL_CALL reserved flags non-zero: 0x${flags.toString(16)}`
    );
  }

  const isStart = (flags & ToolFlags.START) !== 0;
  if (isStart) {
    if (bytes.length < 7) {
      throw new LMStreamError(
        ErrorCode.PROTOCOL_VIOLATION,
        "connection",
        "TOOL_CALL START frame missing headers"
      );
    }
    const idLen = bytes[4];
    const nameLen = view.getUint16(5, true);
    const idEnd = 7 + idLen;
    const nameEnd = idEnd + nameLen;
    if (bytes.length < nameEnd) {
      throw new LMStreamError(
        ErrorCode.PROTOCOL_VIOLATION,
        "connection",
        "Truncated TOOL_CALL identifiers"
      );
    }
    const id = decoder.decode(bytes.subarray(7, idEnd));
    const name = decoder.decode(bytes.subarray(idEnd, nameEnd));
    const argsDelta = decoder.decode(bytes.subarray(nameEnd));
    return { choiceIndex, callIndex, flags, id, name, argsDelta };
  } else {
    const argsDelta = decoder.decode(bytes.subarray(4));
    return { choiceIndex, callIndex, flags, argsDelta };
  }
}

export interface UsagePayload {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
  cachedTokens: number;
  attemptCount: number;
}

export function encodeUsage(p: UsagePayload): Uint8Array {
  const buf = new Uint8Array(20);
  const view = new DataView(buf.buffer);
  view.setUint32(0, p.promptTokens, true);
  view.setUint32(4, p.completionTokens, true);
  view.setUint32(8, p.totalTokens, true);
  view.setUint32(12, p.cachedTokens, true);
  buf[16] = p.attemptCount;
  buf[17] = 0; // reserved
  view.setUint16(18, 0, true); // reserved
  return buf;
}

export function decodeUsage(bytes: Uint8Array): UsagePayload {
  if (bytes.length !== 20) {
    throw new LMStreamError(
      ErrorCode.PROTOCOL_VIOLATION,
      "connection",
      `USAGE payload must be exactly 20 bytes, got ${bytes.length}`
    );
  }
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const res1 = bytes[17];
  const res2 = view.getUint16(18, true);
  if (res1 !== 0 || res2 !== 0) {
    throw new LMStreamError(
      ErrorCode.PROTOCOL_VIOLATION,
      "connection",
      "Non-zero reserved field in USAGE payload"
    );
  }
  return {
    promptTokens: view.getUint32(0, true),
    completionTokens: view.getUint32(4, true),
    totalTokens: view.getUint32(8, true),
    cachedTokens: view.getUint32(12, true),
    attemptCount: bytes[16],
  };
}

export interface MetricsPayload {
  ttftMs: number;
  totalDurationMs: number;
  tokensPerSec: number;
  obfuscatedKeyId: bigint;
}

export function encodeMetrics(p: MetricsPayload): Uint8Array {
  const buf = new Uint8Array(20);
  const view = new DataView(buf.buffer);
  view.setUint32(0, p.ttftMs, true);
  view.setUint32(4, p.totalDurationMs, true);
  view.setUint32(8, p.tokensPerSec, true);
  view.setBigUint64(12, p.obfuscatedKeyId, true);
  return buf;
}

export function decodeMetrics(bytes: Uint8Array): MetricsPayload {
  if (bytes.length !== 20) {
    throw new LMStreamError(
      ErrorCode.PROTOCOL_VIOLATION,
      "connection",
      `METRICS payload must be exactly 20 bytes, got ${bytes.length}`
    );
  }
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  return {
    ttftMs: view.getUint32(0, true),
    totalDurationMs: view.getUint32(4, true),
    tokensPerSec: view.getUint32(8, true),
    obfuscatedKeyId: view.getBigUint64(12, true),
  };
}

export interface EndPayload {
  finishReason: FinishReason;
  choiceIndex: number;
}

export function encodeEnd(p: EndPayload): Uint8Array {
  return new Uint8Array([p.finishReason, p.choiceIndex]);
}

export function decodeEnd(bytes: Uint8Array): EndPayload {
  if (bytes.length !== 2) {
    throw new LMStreamError(
      ErrorCode.PROTOCOL_VIOLATION,
      "connection",
      `END payload must be exactly 2 bytes, got ${bytes.length}`
    );
  }
  return { finishReason: bytes[0] as FinishReason, choiceIndex: bytes[1] };
}

export interface ErrorPayload {
  code: ErrorCode;
  upstreamStatus: number;
  choiceIndex: number;
  scope: ErrorScope;
  message: string;
}

export function encodeError(p: ErrorPayload): Uint8Array {
  const msgBytes = encoder.encode(p.message);
  const buf = new Uint8Array(8 + msgBytes.length);
  const view = new DataView(buf.buffer);
  view.setUint16(0, p.code, true);
  view.setUint16(2, p.upstreamStatus, true);
  buf[4] = p.choiceIndex;
  buf[5] = p.scope;
  view.setUint16(6, msgBytes.length, true);
  buf.set(msgBytes, 8);
  return buf;
}

export function decodeError(bytes: Uint8Array): ErrorPayload {
  if (bytes.length < 8) {
    throw new LMStreamError(
      ErrorCode.PROTOCOL_VIOLATION,
      "connection",
      `ERROR payload too short: ${bytes.length}`
    );
  }
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const code = view.getUint16(0, true) as ErrorCode;
  const upstreamStatus = view.getUint16(2, true);
  const choiceIndex = bytes[4];
  const scope = bytes[5] as ErrorScope;
  const msgLen = view.getUint16(6, true);
  if (bytes.length < 8 + msgLen) {
    throw new LMStreamError(
      ErrorCode.PROTOCOL_VIOLATION,
      "connection",
      `Truncated ERROR message: declared ${msgLen}, got ${bytes.length - 8}`
    );
  }
  const message = decoder.decode(bytes.subarray(8, 8 + msgLen));
  return { code, upstreamStatus, choiceIndex, scope, message };
}

export interface SteerPayload {
  text: string;
}

export function encodeSteer(p: SteerPayload): Uint8Array {
  const textBytes = encoder.encode(p.text);
  const buf = new Uint8Array(2 + textBytes.length);
  const view = new DataView(buf.buffer);
  view.setUint16(0, textBytes.length, true);
  buf.set(textBytes, 2);
  return buf;
}

export function decodeSteer(bytes: Uint8Array): SteerPayload {
  if (bytes.length < 2) {
    throw new LMStreamError(
      ErrorCode.PROTOCOL_VIOLATION,
      "connection",
      "STEER payload missing length field"
    );
  }
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const textLen = view.getUint16(0, true);
  if (bytes.length < 2 + textLen) {
    throw new LMStreamError(
      ErrorCode.PROTOCOL_VIOLATION,
      "connection",
      "Truncated STEER payload string"
    );
  }
  const text = decoder.decode(bytes.subarray(2, 2 + textLen));
  return { text };
}

export interface RewindPayload {
  targetOpcode: Opcode;
  choiceIndex: number;
  byteOffset: number;
}

export function encodeRewind(p: RewindPayload): Uint8Array {
  const buf = new Uint8Array(8);
  const view = new DataView(buf.buffer);
  buf[0] = p.targetOpcode;
  buf[1] = p.choiceIndex;
  view.setUint16(2, 0, true); // reserved
  view.setUint32(4, p.byteOffset, true);
  return buf;
}

export function decodeRewind(bytes: Uint8Array): RewindPayload {
  if (bytes.length !== 8) {
    throw new LMStreamError(
      ErrorCode.PROTOCOL_VIOLATION,
      "connection",
      `REWIND payload must be exactly 8 bytes, got ${bytes.length}`
    );
  }
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const targetOpcode = bytes[0] as Opcode;
  const choiceIndex = bytes[1];
  const res = view.getUint16(2, true);
  if (res !== 0) {
    throw new LMStreamError(
      ErrorCode.PROTOCOL_VIOLATION,
      "connection",
      "Non-zero reserved field in REWIND"
    );
  }
  const byteOffset = view.getUint32(4, true);
  return { targetOpcode, choiceIndex, byteOffset };
}
