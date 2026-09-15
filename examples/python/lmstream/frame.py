import struct
from dataclasses import dataclass
from typing import Tuple
from .enums import Opcode, HeaderFlags, ErrorCode

HEADER_SIZE = 8
MAX_PAYLOAD_SIZE = 65527

class LMStreamError(Exception):
    def __init__(self, code: ErrorCode, scope: str, message: str):
        super().__init__(f"[LMStream {scope.upper()} ERROR {code}] {message}")
        self.code = code
        self.scope = scope
        self.message = message

@dataclass
class FrameHeader:
    stream_id: int
    opcode: Opcode
    flags: int
    length: int

@dataclass
class Frame:
    header: FrameHeader
    payload: bytes

def encode_header(h: FrameHeader) -> bytes:
    if h.length > MAX_PAYLOAD_SIZE:
        raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", f"Payload length {h.length} exceeds cap {MAX_PAYLOAD_SIZE}")
    return struct.pack("<IBBH", h.stream_id, int(h.opcode), h.flags, h.length)

def decode_header(b: bytes) -> FrameHeader:
    if len(b) < HEADER_SIZE:
        raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", f"Buffer too short: {len(b)}")
    stream_id, op_raw, flags, length = struct.unpack("<IBBH", b[:HEADER_SIZE])

    if length > MAX_PAYLOAD_SIZE:
        raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", f"Length {length} > {MAX_PAYLOAD_SIZE}")

    if (flags & HeaderFlags.RESERVED_MASK) != 0:
        raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", f"Reserved flags set: 0x{flags:x}")

    try:
        opcode = Opcode(op_raw)
    except ValueError:
        if 0x00 <= op_raw <= 0x2F:
            raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", f"Unknown core opcode 0x{op_raw:x}")
        opcode = op_raw

    is_conn = opcode in (Opcode.SETTINGS, Opcode.PING, Opcode.PONG, Opcode.ERROR)
    if stream_id == 0 and not is_conn:
        raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", f"Data opcode 0x{op_raw:x} on StreamID 0")

    if stream_id != 0 and opcode in (Opcode.SETTINGS, Opcode.PING, Opcode.PONG):
        raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", f"Control opcode on non-zero StreamID {stream_id}")

    # Validate fixed-size opcode payload lengths
    fixed_lengths = {
        Opcode.SETTINGS: 18,
        Opcode.PING: 8,
        Opcode.PONG: 8,
        Opcode.USAGE: 20,
        Opcode.METRICS: 20,
        Opcode.END: 2,
        Opcode.CANCEL: 0,
        Opcode.PAUSE: 0,
        Opcode.RESUME: 0,
        Opcode.REWIND: 8,
    }
    if opcode in fixed_lengths and length != fixed_lengths[opcode]:
        raise LMStreamError(
            ErrorCode.PROTOCOL_VIOLATION,
            "connection",
            f"Opcode 0x{op_raw:x} requires exact payload length {fixed_lengths[opcode]}, got {length}"
        )

    return FrameHeader(stream_id, opcode, flags, length)

def encode_frame(f: Frame) -> bytes:
    h = f.header
    h.length = len(f.payload)
    return encode_header(h) + f.payload

def decode_frame(b: bytes) -> Frame:
    h = decode_header(b)
    total = HEADER_SIZE + h.length
    if len(b) < total:
        raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", f"Truncated frame: expected {h.length}, got {len(b)-HEADER_SIZE}")
    return Frame(h, b[HEADER_SIZE:total])
