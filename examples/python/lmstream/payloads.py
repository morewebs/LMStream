import struct
from dataclasses import dataclass
from typing import Optional
from .enums import Opcode, ToolFlags, FinishReason, ErrorCode, ErrorScope
from .frame import LMStreamError

@dataclass
class SettingsPayload:
    version: int
    max_frame_size: int
    pause_buffer_cap: int
    heartbeat_ms: int
    max_concurrent_sessions: int

def encode_settings(p: SettingsPayload) -> bytes:
    return struct.pack("<BIIIHBH", p.version, p.max_frame_size, p.pause_buffer_cap, p.heartbeat_ms, p.max_concurrent_sessions, 0, 0)

def decode_settings(b: bytes) -> SettingsPayload:
    if len(b) != 18:
        raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", f"SETTINGS length {len(b)} != 18")
    v, max_f, pause_c, hb, max_s, r1, r2 = struct.unpack("<BIIIHBH", b)
    return SettingsPayload(v, max_f, pause_c, hb, max_s)

@dataclass
class PingPongPayload:
    timestamp_ms: int

def encode_ping_pong(p: PingPongPayload) -> bytes:
    return struct.pack("<Q", p.timestamp_ms)

def decode_ping_pong(b: bytes) -> PingPongPayload:
    if len(b) != 8:
        raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", f"PING/PONG length {len(b)} != 8")
    (ts,) = struct.unpack("<Q", b)
    return PingPongPayload(ts)

@dataclass
class OpenAckPayload:
    session_id: int
    model: str

def encode_open_ack(p: OpenAckPayload) -> bytes:
    m = p.model.encode("utf-8")
    return struct.pack("<IH", p.session_id, len(m)) + m

def decode_open_ack(b: bytes) -> OpenAckPayload:
    if len(b) < 6:
        raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", "OPEN_ACK too short")
    sid, mlen = struct.unpack("<IH", b[:6])
    if len(b) < 6 + mlen:
        raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", "Truncated model name")
    return OpenAckPayload(sid, b[6:6+mlen].decode("utf-8"))

@dataclass
class ContentPayload:
    choice_index: int
    text: str

def encode_content(p: ContentPayload) -> bytes:
    return bytes([p.choice_index]) + p.text.encode("utf-8")

def decode_content(b: bytes) -> ContentPayload:
    if len(b) < 1:
        raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", "CONTENT missing choice")
    return ContentPayload(b[0], b[1:].decode("utf-8"))

@dataclass
class ToolCallPayload:
    choice_index: int
    call_index: int
    flags: int
    id: Optional[str] = None
    name: Optional[str] = None
    args_delta: str = ""

def encode_tool_call(p: ToolCallPayload) -> bytes:
    is_start = bool(p.flags & ToolFlags.START)
    if is_start:
        id_b = (p.id or "").encode("utf-8")
        name_b = (p.name or "").encode("utf-8")
        args_b = p.args_delta.encode("utf-8")
        h = struct.pack("<HBBH", p.call_index, p.flags, len(id_b), len(name_b))
        return bytes([p.choice_index]) + h + id_b + name_b + args_b
    else:
        args_b = p.args_delta.encode("utf-8")
        h = struct.pack("<HB", p.call_index, p.flags)
        return bytes([p.choice_index]) + h + args_b

def decode_tool_call(b: bytes) -> ToolCallPayload:
    if len(b) < 4:
        raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", "TOOL_CALL too short")
    choice = b[0]
    call_idx, flags = struct.unpack("<HB", b[1:4])
    if (flags & ToolFlags.RESERVED_MASK) != 0:
        raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", f"TOOL_CALL reserved flags non-zero: 0x{flags:x}")
    is_start = bool(flags & ToolFlags.START)
    if is_start:
        if len(b) < 7:
            raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", "TOOL_CALL START missing fields")
        id_len, name_len = struct.unpack("<BH", b[4:7])
        id_end = 7 + id_len
        name_end = id_end + name_len
        if len(b) < name_end:
            raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", "Truncated TOOL_CALL metadata")
        id_str = b[7:id_end].decode("utf-8")
        name_str = b[id_end:name_end].decode("utf-8")
        args_str = b[name_end:].decode("utf-8")
        return ToolCallPayload(choice, call_idx, flags, id_str, name_str, args_str)
    else:
        args_str = b[4:].decode("utf-8")
        return ToolCallPayload(choice, call_idx, flags, args_delta=args_str)

@dataclass
class UsagePayload:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cached_tokens: int
    attempt_count: int

def encode_usage(p: UsagePayload) -> bytes:
    return struct.pack("<IIIIBBH", p.prompt_tokens, p.completion_tokens, p.total_tokens, p.cached_tokens, p.attempt_count, 0, 0)

def decode_usage(b: bytes) -> UsagePayload:
    if len(b) != 20:
        raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", f"USAGE length {len(b)} != 20")
    pt, ct, tt, cached, attempts, r1, r2 = struct.unpack("<IIIIBBH", b)
    if r1 != 0 or r2 != 0:
        raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", "USAGE reserved fields non-zero")
    return UsagePayload(pt, ct, tt, cached, attempts)

@dataclass
class MetricsPayload:
    ttft_ms: int
    total_duration_ms: int
    tokens_per_sec: int
    obfuscated_key_id: int

def encode_metrics(p: MetricsPayload) -> bytes:
    return struct.pack("<IIIQ", p.ttft_ms, p.total_duration_ms, p.tokens_per_sec, p.obfuscated_key_id)

def decode_metrics(b: bytes) -> MetricsPayload:
    if len(b) != 20:
        raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", f"METRICS length {len(b)} != 20")
    ttft, dur, tok_sec, key_id = struct.unpack("<IIIQ", b)
    return MetricsPayload(ttft, dur, tok_sec, key_id)

@dataclass
class EndPayload:
    finish_reason: FinishReason
    choice_index: int

def encode_end(p: EndPayload) -> bytes:
    return bytes([int(p.finish_reason), p.choice_index])

def decode_end(b: bytes) -> EndPayload:
    if len(b) != 2:
        raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", f"END length {len(b)} != 2")
    return EndPayload(FinishReason(b[0]), b[1])

@dataclass
class ErrorPayload:
    code: ErrorCode
    upstream_status: int
    choice_index: int
    scope: ErrorScope
    message: str

def encode_error(p: ErrorPayload) -> bytes:
    m = p.message.encode("utf-8")
    return struct.pack("<HHBBH", int(p.code), p.upstream_status, p.choice_index, int(p.scope), len(m)) + m

def decode_error(b: bytes) -> ErrorPayload:
    if len(b) < 8:
        raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", f"ERROR length {len(b)} < 8")
    code, status, choice, scope, msg_len = struct.unpack("<HHBBH", b[:8])
    if len(b) < 8 + msg_len:
        raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", "Truncated ERROR message")
    return ErrorPayload(ErrorCode(code), status, choice, ErrorScope(scope), b[8:8+msg_len].decode("utf-8"))

@dataclass
class SteerPayload:
    text: str

def encode_steer(p: SteerPayload) -> bytes:
    t = p.text.encode("utf-8")
    return struct.pack("<H", len(t)) + t

def decode_steer(b: bytes) -> SteerPayload:
    if len(b) < 2:
        raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", "STEER missing length")
    (tlen,) = struct.unpack("<H", b[:2])
    if len(b) < 2 + tlen:
        raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", "Truncated STEER text")
    return SteerPayload(b[2:2+tlen].decode("utf-8"))

@dataclass
class RewindPayload:
    target_opcode: Opcode
    choice_index: int
    byte_offset: int

def encode_rewind(p: RewindPayload) -> bytes:
    return struct.pack("<BBHI", int(p.target_opcode), p.choice_index, 0, p.byte_offset)

def decode_rewind(b: bytes) -> RewindPayload:
    if len(b) != 8:
        raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", f"REWIND length {len(b)} != 8")
    target, choice, res, offset = struct.unpack("<BBHI", b)
    if res != 0:
        raise LMStreamError(ErrorCode.PROTOCOL_VIOLATION, "connection", "REWIND reserved non-zero")
    return RewindPayload(Opcode(target), choice, offset)
