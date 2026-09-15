/**
 * LMStream Protocol Enums and Numerical Identifiers
 */

export enum Opcode {
  OPEN = 0x01,
  OPEN_ACK = 0x02,
  CONTENT = 0x03,
  REASONING = 0x04,
  TOOL_CALL = 0x05,
  USAGE = 0x06,
  METRICS = 0x07,
  END = 0x08,
  ERROR = 0x09,
  CANCEL = 0x0a,
  PAUSE = 0x0b,
  RESUME = 0x0c,
  STEER = 0x0d,
  REWIND = 0x0e,
  SETTINGS = 0x0f,
  PING = 0x10,
  PONG = 0x11,
}

export enum HeaderFlags {
  BOUNDARY = 0x01,
  COMPRESSED = 0x02,
  RESERVED_MASK = 0xfe, // In v1, bits 1-7 MUST be 0
}

export enum ToolFlags {
  START = 0x01,
  CONT = 0x02,
  END = 0x04,
  RESERVED_MASK = 0xf8, // Bits 3-7 MUST be 0
}

export enum FinishReason {
  STOP = 0x00,
  LENGTH = 0x01,
  TOOL_CALLS = 0x02,
  CONTENT_FILTER = 0x03,
  CANCELLED = 0x04,
}

export enum ErrorCode {
  BAD_REQUEST = 1001,
  AUTH_FAILED = 1002,
  RATE_LIMITED = 1003,
  MODEL_OVERLOADED = 1004,
  UPSTREAM_ERROR = 1005,
  BUFFER_OVERFLOW = 1006,
  INVALID_STATE = 1007,
  PROTOCOL_VIOLATION = 1008,
  SESSION_EXPIRED = 1009,
}

export enum ErrorScope {
  SESSION = 0x00,
  CONNECTION = 0x01,
}
