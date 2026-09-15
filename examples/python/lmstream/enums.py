from enum import IntEnum

class Opcode(IntEnum):
    OPEN = 0x01
    OPEN_ACK = 0x02
    CONTENT = 0x03
    REASONING = 0x04
    TOOL_CALL = 0x05
    USAGE = 0x06
    METRICS = 0x07
    END = 0x08
    ERROR = 0x09
    CANCEL = 0x0A
    PAUSE = 0x0B
    RESUME = 0x0C
    STEER = 0x0D
    REWIND = 0x0E
    SETTINGS = 0x0F
    PING = 0x10
    PONG = 0x11

class HeaderFlags(IntEnum):
    BOUNDARY = 0x01
    COMPRESSED = 0x02
    RESERVED_MASK = 0xFE

class ToolFlags(IntEnum):
    START = 0x01
    CONT = 0x02
    END = 0x04
    RESERVED_MASK = 0xF8

class FinishReason(IntEnum):
    STOP = 0x00
    LENGTH = 0x01
    TOOL_CALLS = 0x02
    CONTENT_FILTER = 0x03
    CANCELLED = 0x04

class ErrorCode(IntEnum):
    BAD_REQUEST = 1001
    AUTH_FAILED = 1002
    RATE_LIMITED = 1003
    MODEL_OVERLOADED = 1004
    UPSTREAM_ERROR = 1005
    BUFFER_OVERFLOW = 1006
    INVALID_STATE = 1007
    PROTOCOL_VIOLATION = 1008
    SESSION_EXPIRED = 1009

class ErrorScope(IntEnum):
    SESSION = 0x00
    CONNECTION = 0x01
