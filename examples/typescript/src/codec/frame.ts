import { Opcode, HeaderFlags, ErrorCode } from "./enums.js";

export const HEADER_SIZE = 8;
export const MAX_PAYLOAD_SIZE = 65527;

export interface FrameHeader {
  streamId: number;
  opcode: Opcode;
  flags: number;
  length: number;
}

export interface Frame {
  header: FrameHeader;
  payload: Uint8Array;
}

export class LMStreamError extends Error {
  public readonly code: ErrorCode;
  public readonly scope: "session" | "connection";

  constructor(code: ErrorCode, scope: "session" | "connection", message: string) {
    super(`[LMStream ${scope.toUpperCase()} ERROR ${code}] ${message}`);
    this.name = "LMStreamError";
    this.code = code;
    this.scope = scope;
  }
}

export function encodeHeader(header: FrameHeader): Uint8Array {
  if (header.length > MAX_PAYLOAD_SIZE) {
    throw new LMStreamError(
      ErrorCode.PROTOCOL_VIOLATION,
      "connection",
      `Payload length ${header.length} exceeds maximum permissible cap of ${MAX_PAYLOAD_SIZE} bytes`
    );
  }
  const buf = new Uint8Array(HEADER_SIZE);
  const view = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
  view.setUint32(0, header.streamId, true);
  view.setUint8(4, header.opcode);
  view.setUint8(5, header.flags);
  view.setUint16(6, header.length, true);
  return buf;
}

export function decodeHeader(bytes: Uint8Array): FrameHeader {
  if (bytes.length < HEADER_SIZE) {
    throw new LMStreamError(
      ErrorCode.PROTOCOL_VIOLATION,
      "connection",
      `Buffer too short for frame header: got ${bytes.length}, expected ${HEADER_SIZE}`
    );
  }
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const streamId = view.getUint32(0, true);
  const opcodeRaw = view.getUint8(4);
  const flags = view.getUint8(5);
  const length = view.getUint16(6, true);

  if (length > MAX_PAYLOAD_SIZE) {
    throw new LMStreamError(
      ErrorCode.PROTOCOL_VIOLATION,
      "connection",
      `Frame length ${length} exceeds maximum limit of ${MAX_PAYLOAD_SIZE}`
    );
  }

  // Validate reserved flag bits (Bits 1-7 in v1)
  if ((flags & HeaderFlags.RESERVED_MASK) !== 0) {
    throw new LMStreamError(
      ErrorCode.PROTOCOL_VIOLATION,
      "connection",
      `Reserved flag bits non-zero: 0x${flags.toString(16)}`
    );
  }

  // Validate opcode
  const isKnownCore = Object.values(Opcode).includes(opcodeRaw);
  if (!isKnownCore) {
    if (opcodeRaw >= 0x00 && opcodeRaw <= 0x2f) {
      throw new LMStreamError(
        ErrorCode.PROTOCOL_VIOLATION,
        "connection",
        `Unknown or reserved core opcode: 0x${opcodeRaw.toString(16).padStart(2, "0")}`
      );
    }
  }

  const opcode = opcodeRaw as Opcode;

  // StreamID 0 rules
  const isConnectionOpcode =
    opcode === Opcode.SETTINGS ||
    opcode === Opcode.PING ||
    opcode === Opcode.PONG ||
    opcode === Opcode.ERROR;

  if (streamId === 0 && !isConnectionOpcode) {
    throw new LMStreamError(
      ErrorCode.PROTOCOL_VIOLATION,
      "connection",
      `Data opcode 0x${opcode.toString(16)} forbidden on StreamID 0`
    );
  }

  if (
    streamId !== 0 &&
    (opcode === Opcode.SETTINGS || opcode === Opcode.PING || opcode === Opcode.PONG)
  ) {
    throw new LMStreamError(
      ErrorCode.PROTOCOL_VIOLATION,
      "connection",
      `Control opcode 0x${opcode.toString(16)} forbidden on non-zero StreamID ${streamId}`
    );
  }

  return { streamId, opcode, flags, length };
}

export function encodeFrame(frame: Frame): Uint8Array {
  const payloadLen = frame.payload.length;
  if (frame.header.length !== payloadLen) {
    frame.header.length = payloadLen;
  }
  const headerBytes = encodeHeader(frame.header);
  const out = new Uint8Array(HEADER_SIZE + payloadLen);
  out.set(headerBytes, 0);
  out.set(frame.payload, HEADER_SIZE);
  return out;
}

export function decodeFrame(bytes: Uint8Array): Frame {
  const header = decodeHeader(bytes);
  const totalNeeded = HEADER_SIZE + header.length;
  if (bytes.length < totalNeeded) {
    throw new LMStreamError(
      ErrorCode.PROTOCOL_VIOLATION,
      "connection",
      `Truncated frame payload: expected ${header.length} bytes, got ${bytes.length - HEADER_SIZE}`
    );
  }
  const payload = bytes.subarray(HEADER_SIZE, totalNeeded);
  return { header, payload };
}
