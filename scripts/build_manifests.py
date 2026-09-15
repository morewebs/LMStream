#!/usr/bin/env python3
"""
build_manifests.py
Generates the normative LMStream test vector manifests:
- vectors/golden/manifest.json (>= 60 vectors)
- vectors/invalid/manifest.json (>= 15 vectors)
- vectors/edge/manifest.json (>= 20 vectors)
- vectors/scenarios/manifest.json (>= 8 scenarios)
"""

import json
import os
import struct

def make_header(stream_id: int, opcode: int, flags: int, length: int) -> bytes:
    # StreamID u32 LE, Opcode u8, Flags u8, Length u16 LE
    return struct.pack("<IBBH", stream_id, opcode, flags, length)

def make_frame(stream_id: int, opcode: int, flags: int, payload: bytes) -> bytes:
    return make_header(stream_id, opcode, flags, len(payload)) + payload

def build_golden_vectors():
    vectors = []

    def add(vec_id: str, desc: str, stream_id: int, opcode_name: str, opcode: int, flags: int, payload: bytes, details: dict):
        raw = make_frame(stream_id, opcode, flags, payload)
        vectors.append({
            "id": vec_id,
            "description": desc,
            "raw_hex": raw.hex(),
            "frame": {
                "stream_id": stream_id,
                "opcode": opcode_name,
                "flags": flags,
                "length": len(payload),
                "payload": details
            }
        })

    # 1. SETTINGS (0x0F) - 18 bytes
    # Version(u8), MaxFrameSize(u32), PauseBufferCap(u32), HeartbeatMs(u32), MaxConcurrentSessions(u16), Res1(u8), Res2(u16)
    s1_payload = struct.pack("<BIIIHBH", 1, 65535, 1048576, 15000, 100, 0, 0)
    add("golden-settings-default", "Default connection handshake SETTINGS frame",
        0, "SETTINGS", 0x0F, 0, s1_payload, {
            "version": 1, "max_frame_size": 65535, "pause_buffer_cap": 1048576,
            "heartbeat_ms": 15000, "max_concurrent_sessions": 100
        })

    s2_payload = struct.pack("<BIIIHBH", 1, 32768, 524288, 30000, 250, 0, 0)
    add("golden-settings-custom", "Custom operational SETTINGS frame",
        0, "SETTINGS", 0x0F, 0, s2_payload, {
            "version": 1, "max_frame_size": 32768, "pause_buffer_cap": 524288,
            "heartbeat_ms": 30000, "max_concurrent_sessions": 250
        })

    # 2. PING (0x10) - 8 bytes u64 LE
    ping1 = struct.pack("<Q", 0)
    add("golden-ping-zero", "PING frame with timestamp 0", 0, "PING", 0x10, 0, ping1, {"timestamp_ms": 0})
    
    ping2 = struct.pack("<Q", 1700000000000)
    add("golden-ping-timestamp", "PING frame with standard millisecond epoch", 0, "PING", 0x10, 0, ping2, {"timestamp_ms": 1700000000000})

    ping3 = struct.pack("<Q", 0xFFFFFFFFFFFFFFFF)
    add("golden-ping-max", "PING frame with max u64 timestamp", 0, "PING", 0x10, 0, ping3, {"timestamp_ms": 18446744073709551615})

    # 3. PONG (0x11) - 8 bytes u64 LE
    pong1 = struct.pack("<Q", 1700000000000)
    add("golden-pong-standard", "PONG frame echoing timestamp", 0, "PONG", 0x11, 0, pong1, {"timestamp_ms": 1700000000000})

    pong2 = struct.pack("<Q", 42)
    add("golden-pong-small", "PONG frame with small timestamp", 0, "PONG", 0x11, 0, pong2, {"timestamp_ms": 42})

    # 4. OPEN (0x01) - JSON payload
    open_p1 = json.dumps({"model": "gpt-4o"}).encode("utf-8")
    add("golden-open-minimal", "Minimal OPEN frame with model identifier", 1, "OPEN", 0x01, 0, open_p1, {"json": json.loads(open_p1)})

    open_p2 = json.dumps({"model": "claude-3-5-sonnet", "messages": [{"role": "user", "content": "Hello"}], "temperature": 0.5}).encode("utf-8")
    add("golden-open-rich", "OPEN frame with messages and inference parameters", 3, "OPEN", 0x01, 0, open_p2, {"json": json.loads(open_p2)})

    open_p3 = json.dumps({"model": "deepseek-r1", "tools": [{"name": "calculator"}]}).encode("utf-8")
    add("golden-open-tools", "OPEN frame requesting tools", 5, "OPEN", 0x01, 0, open_p3, {"json": json.loads(open_p3)})

    # 5. OPEN_ACK (0x02) - SessionID u32 LE, ModelLen u16 LE, Model string
    ack1_m = b"gpt-4o"
    ack1 = struct.pack("<IH", 1, len(ack1_m)) + ack1_m
    add("golden-open-ack-1", "OPEN_ACK confirming StreamID 1", 1, "OPEN_ACK", 0x02, 0, ack1, {"session_id": 1, "model": "gpt-4o"})

    ack2_m = b"claude-3-5-sonnet-20241022"
    ack2 = struct.pack("<IH", 3, len(ack2_m)) + ack2_m
    add("golden-open-ack-3", "OPEN_ACK confirming StreamID 3", 3, "OPEN_ACK", 0x02, 0, ack2, {"session_id": 3, "model": "claude-3-5-sonnet-20241022"})

    # 6. CONTENT (0x03) - ChoiceIndex u8, Data raw UTF-8
    # Various text representations
    add("golden-content-empty", "Empty text CONTENT frame", 1, "CONTENT", 0x03, 1, bytes([0]), {"choice_index": 0, "text": ""})
    add("golden-content-single-char", "Single character CONTENT frame", 1, "CONTENT", 0x03, 1, bytes([0]) + b"A", {"choice_index": 0, "text": "A"})
    add("golden-content-word", "Standard single-word CONTENT frame", 1, "CONTENT", 0x03, 1, bytes([0]) + b"Hello", {"choice_index": 0, "text": "Hello"})
    add("golden-content-punctuation", "Punctuation and whitespace CONTENT frame", 1, "CONTENT", 0x03, 1, bytes([0]) + b", world!\n", {"choice_index": 0, "text": ", world!\n"})
    add("golden-content-2byte-utf8", "2-byte UTF-8 character CONTENT frame", 1, "CONTENT", 0x03, 1, bytes([0]) + "café".encode("utf-8"), {"choice_index": 0, "text": "café"})
    add("golden-content-3byte-utf8", "3-byte UTF-8 character CONTENT frame", 1, "CONTENT", 0x03, 1, bytes([0]) + "€100".encode("utf-8"), {"choice_index": 0, "text": "€100"})
    add("golden-content-4byte-emoji", "4-byte UTF-8 emoji CONTENT frame", 1, "CONTENT", 0x03, 1, bytes([0]) + "🚀🔥".encode("utf-8"), {"choice_index": 0, "text": "🚀🔥"})
    add("golden-content-multilingual", "Multilingual mixed CONTENT frame", 1, "CONTENT", 0x03, 1, bytes([0]) + "Hello 世界 🌍".encode("utf-8"), {"choice_index": 0, "text": "Hello 世界 🌍"})
    add("golden-content-choice-1", "CONTENT frame with non-zero choice index", 1, "CONTENT", 0x03, 1, bytes([1]) + b"Alternative", {"choice_index": 1, "text": "Alternative"})

    # CONTENT with BOUNDARY = 0 (ending on partial UTF-8 sequence)
    # Euro sign € is 0xE2 0x82 0xAC. We emit 0xE2 0x82 (2 bytes of 3)
    partial_euro = bytes([0]) + b"price: " + bytes([0xE2, 0x82])
    add("golden-content-boundary-0-partial", "CONTENT frame terminating with incomplete UTF-8 bytes (BOUNDARY=0)",
        1, "CONTENT", 0x03, 0, partial_euro, {"choice_index": 0, "raw_prefix": "price: ", "incomplete_bytes": "e282"})

    # 7. REASONING (0x04) - ChoiceIndex u8, Data raw UTF-8
    add("golden-reasoning-intro", "REASONING frame with thought introduction", 1, "REASONING", 0x04, 1, bytes([0]) + b"Thinking through step 1...", {"choice_index": 0, "text": "Thinking through step 1..."})
    add("golden-reasoning-math", "REASONING frame with LaTeX formula", 1, "REASONING", 0x04, 1, bytes([0]) + "Let $x = \\sqrt{2}$.".encode("utf-8"), {"choice_index": 0, "text": "Let $x = \\sqrt{2}$."})
    add("golden-reasoning-multiline", "REASONING frame multiline block", 1, "REASONING", 0x04, 1, bytes([0]) + b"Plan:\n1. Verify\n2. Execute", {"choice_index": 0, "text": "Plan:\n1. Verify\n2. Execute"})

    # 8. TOOL_CALL (0x05)
    # ChoiceIndex u8, CallIndex u16 LE, ToolFlags u8
    # If START (0x01): IdLen u8, NameLen u16 LE, CallId, Name, Args
    # If not START: Args directly
    
    # 8a: Single-frame complete tool call (START | END = 0x05)
    call_id = b"call_abc123"
    tool_name = b"get_weather"
    tool_args = b'{"location":"San Francisco, CA"}'
    tc_single = struct.pack("<HBBH", 0, 0x05, len(call_id), len(tool_name))
    tc_single_payload = bytes([0]) + tc_single + call_id + tool_name + tool_args
    add("golden-tool-single-frame", "Single-frame complete tool invocation (START|END)",
        1, "TOOL_CALL", 0x05, 0, tc_single_payload, {
            "choice_index": 0, "call_index": 0, "flags": 5, "id": "call_abc123",
            "name": "get_weather", "args": '{"location":"San Francisco, CA"}'
        })

    # 8b: Single-frame with empty args
    tc_empty_args = bytes([0]) + struct.pack("<HBBH", 1, 0x05, 7, 8) + b"call_01" + b"get_time" + b""
    add("golden-tool-empty-args", "Tool call with empty arguments",
        1, "TOOL_CALL", 0x05, 0, tc_empty_args, {
            "choice_index": 0, "call_index": 1, "flags": 5, "id": "call_01",
            "name": "get_time", "args": ""
        })

    # 8c: 3-part fragmented tool call
    # Part 1: START (0x01)
    p1_args = b'{"query":"'
    tc_p1 = bytes([0]) + struct.pack("<HBBH", 0, 0x01, 8, 6) + b"call_999" + b"search" + p1_args
    add("golden-tool-frag-start", "Fragmented tool call part 1 (START)",
        1, "TOOL_CALL", 0x05, 0, tc_p1, {
            "choice_index": 0, "call_index": 0, "flags": 1, "id": "call_999",
            "name": "search", "args_delta": '{"query":"'
        })
    # Part 2: CONT (0x02)
    p2_args = b'lmstream protocol'
    tc_p2 = bytes([0]) + struct.pack("<HB", 0, 0x02) + p2_args
    add("golden-tool-frag-cont", "Fragmented tool call part 2 (CONT)",
        1, "TOOL_CALL", 0x05, 0, tc_p2, {
            "choice_index": 0, "call_index": 0, "flags": 2, "args_delta": 'lmstream protocol'
        })
    # Part 3: END (0x04)
    p3_args = b'"}'
    tc_p3 = bytes([0]) + struct.pack("<HB", 0, 0x04) + p3_args
    add("golden-tool-frag-end", "Fragmented tool call part 3 (END)",
        1, "TOOL_CALL", 0x05, 0, tc_p3, {
            "choice_index": 0, "call_index": 0, "flags": 4, "args_delta": '"}'
        })

    # 9. USAGE (0x06) - 20 bytes
    # PromptTokens(u32), CompletionTokens(u32), TotalTokens(u32), CachedTokens(u32), AttemptCount(u8), Res1(u8), Res2(u16)
    u1 = struct.pack("<IIIIBBH", 0, 0, 0, 0, 1, 0, 0)
    add("golden-usage-zeros", "USAGE frame with zero tokens", 1, "USAGE", 0x06, 0, u1, {
        "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "cached_tokens": 0, "attempt_count": 1
    })

    u2 = struct.pack("<IIIIBBH", 150, 42, 192, 32, 1, 0, 0)
    add("golden-usage-standard", "Standard USAGE token accounting frame", 1, "USAGE", 0x06, 0, u2, {
        "prompt_tokens": 150, "completion_tokens": 42, "total_tokens": 192, "cached_tokens": 32, "attempt_count": 1
    })

    u3 = struct.pack("<IIIIBBH", 128000, 4096, 132096, 64000, 1, 0, 0)
    add("golden-usage-large", "Large context USAGE accounting frame", 1, "USAGE", 0x06, 0, u3, {
        "prompt_tokens": 128000, "completion_tokens": 4096, "total_tokens": 132096, "cached_tokens": 64000, "attempt_count": 1
    })

    u4 = struct.pack("<IIIIBBH", 500, 100, 600, 0, 3, 0, 0)
    add("golden-usage-failover-attempts", "Cumulative USAGE with 3 provider retry attempts", 1, "USAGE", 0x06, 0, u4, {
        "prompt_tokens": 500, "completion_tokens": 100, "total_tokens": 600, "cached_tokens": 0, "attempt_count": 3
    })

    # 10. METRICS (0x07) - 20 bytes
    # TTFTMs(u32), TotalDurationMs(u32), TokensPerSec(u32), ObfuscatedKeyID(u64)
    m1 = struct.pack("<IIIQ", 45, 230, 8550, 0x1234567890ABCDEF)
    add("golden-metrics-fast", "METRICS frame for fast token generation", 1, "METRICS", 0x07, 0, m1, {
        "ttft_ms": 45, "total_duration_ms": 230, "tokens_per_sec": 8550, "obfuscated_key_id": 0x1234567890ABCDEF
    })

    m2 = struct.pack("<IIIQ", 1200, 9500, 2430, 0xCAFEBABEDEADBEEF)
    add("golden-metrics-slow", "METRICS frame for long inference generation", 1, "METRICS", 0x07, 0, m2, {
        "ttft_ms": 1200, "total_duration_ms": 9500, "tokens_per_sec": 2430, "obfuscated_key_id": 0xCAFEBABEDEADBEEF
    })

    m3 = struct.pack("<IIIQ", 0, 10, 0, 0)
    add("golden-metrics-minimal", "METRICS frame with minimal durations", 1, "METRICS", 0x07, 0, m3, {
        "ttft_ms": 0, "total_duration_ms": 10, "tokens_per_sec": 0, "obfuscated_key_id": 0
    })

    # 11. END (0x08) - FinishReason u8, ChoiceIndex u8
    for r_val, r_name in [(0x00, "STOP"), (0x01, "LENGTH"), (0x02, "TOOL_CALLS"), (0x03, "CONTENT_FILTER"), (0x04, "CANCELLED")]:
        add(f"golden-end-{r_name.lower()}", f"END frame with finish reason {r_name}",
            1, "END", 0x08, 0, bytes([r_val, 0]), {"finish_reason": r_name, "choice_index": 0})

    add("golden-end-choice-1", "END frame with choice index 1", 1, "END", 0x08, 0, bytes([0x00, 1]), {"finish_reason": "STOP", "choice_index": 1})

    # 12. ERROR (0x09) - Code u16, UpstreamStatus u16, ChoiceIndex u8, Scope u8, MsgLen u16, Msg
    error_cases = [
        (1001, 400, 0, 0, "Malformed request JSON", "bad-request"),
        (1002, 401, 0, 1, "Authentication token rejected", "auth-failed"),
        (1003, 429, 0, 0, "Rate limit exceeded. Retry-After: 30", "rate-limited"),
        (1004, 503, 0, 0, "Model queue saturated", "model-overloaded"),
        (1005, 500, 0, 0, "Inference engine segmentation fault", "upstream-error"),
        (1006, 0, 0, 0, "Paused buffer exceeded 1MB cap", "buffer-overflow"),
        (1007, 0, 0, 0, "Unexpected CONTENT frame after END", "invalid-state"),
        (1008, 0, 0, 1, "Reserved header bit non-zero", "protocol-violation"),
        (1009, 0, 0, 0, "Session paused state expired after 60s", "session-expired"),
    ]
    for code, status, choice, scope, msg, name in error_cases:
        msg_b = msg.encode("utf-8")
        err_p = struct.pack("<HHBBH", code, status, choice, scope, len(msg_b)) + msg_b
        add(f"golden-error-{name}", f"ERROR {code} {name}", 1, "ERROR", 0x09, 0, err_p, {
            "code": code, "upstream_status": status, "choice_index": choice,
            "scope": "CONNECTION" if scope == 1 else "SESSION", "message": msg
        })

    # 13. CANCEL (0x0A) - Zero length
    add("golden-cancel-stream1", "Client CANCEL on StreamID 1", 1, "CANCEL", 0x0A, 0, b"", {})
    add("golden-cancel-stream3", "Client CANCEL on StreamID 3", 3, "CANCEL", 0x0A, 0, b"", {})

    # 14. PAUSE (0x0B) - Zero length
    add("golden-pause-stream1", "Client PAUSE on StreamID 1", 1, "PAUSE", 0x0B, 0, b"", {})
    add("golden-pause-stream5", "Client PAUSE on StreamID 5", 5, "PAUSE", 0x0B, 0, b"", {})

    # 15. RESUME (0x0C) - Zero length
    add("golden-resume-stream1", "Client RESUME on StreamID 1", 1, "RESUME", 0x0C, 0, b"", {})
    add("golden-resume-stream5", "Client RESUME on StreamID 5", 5, "RESUME", 0x0C, 0, b"", {})

    # 16. STEER (0x0D) - TextLen u16 LE, UTF-8 text
    st1 = b"be concise"
    add("golden-steer-concise", "STEER frame instructing concise output",
        1, "STEER", 0x0D, 0, struct.pack("<H", len(st1)) + st1, {"text": "be concise"})
    
    st2 = "réponds en français".encode("utf-8")
    add("golden-steer-french", "STEER frame with UTF-8 accents",
        1, "STEER", 0x0D, 0, struct.pack("<H", len(st2)) + st2, {"text": "réponds en français"})

    st3 = b"Format response as a markdown table with 3 columns."
    add("golden-steer-format", "STEER frame directing markdown table output",
        3, "STEER", 0x0D, 0, struct.pack("<H", len(st3)) + st3, {"text": "Format response as a markdown table with 3 columns."})

    # 17. REWIND (0x0E) - TargetOpcode u8, ChoiceIndex u8, Reserved u16, ByteOffset u32 LE (8 bytes)
    rw1 = struct.pack("<BBHI", 0x03, 0, 0, 0)
    add("golden-rewind-content-zero", "REWIND CONTENT to byte offset 0", 1, "REWIND", 0x0E, 0, rw1, {
        "target_opcode": "CONTENT", "choice_index": 0, "byte_offset": 0
    })

    rw2 = struct.pack("<BBHI", 0x03, 0, 0, 48)
    add("golden-rewind-content-offset", "REWIND CONTENT to byte offset 48", 1, "REWIND", 0x0E, 0, rw2, {
        "target_opcode": "CONTENT", "choice_index": 0, "byte_offset": 48
    })

    rw3 = struct.pack("<BBHI", 0x04, 0, 0, 120)
    add("golden-rewind-reasoning-offset", "REWIND REASONING to byte offset 120", 1, "REWIND", 0x0E, 0, rw3, {
        "target_opcode": "REASONING", "choice_index": 0, "byte_offset": 120
    })

    rw4 = struct.pack("<BBHI", 0x05, 0, 0, 0)
    add("golden-rewind-tool-discard", "REWIND TOOL_CALL to offset 0 (discard invariant)", 1, "REWIND", 0x0E, 0, rw4, {
        "target_opcode": "TOOL_CALL", "choice_index": 0, "byte_offset": 0
    })

    # Additional diverse payload vectors to reach target >= 60:
    # Multiple content frames with varying lengths and codepoints
    add("golden-content-code-snippet", "CONTENT containing code snippet with escaped quotes",
        1, "CONTENT", 0x03, 1, bytes([0]) + b'print("Hello \\"World\\"")\n', {"choice_index": 0, "text": 'print("Hello \\"World\\"")\n'})
    
    add("golden-content-tab-cr", "CONTENT with tab and carriage return characters",
        1, "CONTENT", 0x03, 1, bytes([0]) + b"Col1\tCol2\r\nVal1\tVal2", {"choice_index": 0, "text": "Col1\tCol2\r\nVal1\tVal2"})

    # Large payload CONTENT frame (1024 bytes)
    chunk_1k = b"A" * 1023
    add("golden-content-1kb", "CONTENT frame carrying 1024-byte payload (choice=0 + 1023 bytes)",
        1, "CONTENT", 0x03, 1, bytes([0]) + chunk_1k, {"choice_index": 0, "length": 1024})

    # Max allowed payload frame: 65,527 bytes
    max_chunk = b"X" * 65526
    add("golden-content-max-payload", "CONTENT frame with maximum permissible payload length (65,527 bytes)",
        1, "CONTENT", 0x03, 1, bytes([0]) + max_chunk, {"choice_index": 0, "length": 65527})

    return vectors

def build_invalid_vectors():
    vectors = []
    def add(vec_id: str, desc: str, raw_bytes: bytes, exp_code: int, scope: str):
        vectors.append({
            "id": vec_id,
            "description": desc,
            "raw_hex": raw_bytes.hex(),
            "expected_error": {
                "code": exp_code,
                "scope": scope
            }
        })

    # 1. Length > 65527: Length field set to 65528
    h_overflow = struct.pack("<IBBH", 1, 0x03, 1, 65528) + bytes([0]) * 10
    add("invalid-length-exceeds-max", "Payload length field exceeds 65,527 cap", h_overflow, 1008, "connection")

    # 2. Reserved flag bit 1 set (COMPRESSED)
    f_res1 = make_frame(1, 0x03, 0x02, bytes([0]) + b"test")
    add("invalid-reserved-flag-bit1", "Reserved header flag bit 1 (COMPRESSED) is non-zero", f_res1, 1008, "connection")

    # 3. Reserved flag bit 2 set
    f_res2 = make_frame(1, 0x03, 0x04, bytes([0]) + b"test")
    add("invalid-reserved-flag-bit2", "Reserved header flag bit 2 is non-zero", f_res2, 1008, "connection")

    # 4. Reserved flag bit 7 set
    f_res7 = make_frame(1, 0x03, 0x80, bytes([0]) + b"test")
    add("invalid-reserved-flag-bit7", "Reserved header flag bit 7 is non-zero", f_res7, 1008, "connection")

    # 5. Unknown core opcode 0x00
    f_op0 = make_frame(1, 0x00, 0, b"")
    add("invalid-unknown-core-opcode-00", "Reserved core opcode 0x00 received", f_op0, 1008, "connection")

    # 6. Unknown core opcode 0x20 (in range 0x01-0x2F)
    f_op20 = make_frame(1, 0x20, 0, b"data")
    add("invalid-unknown-core-opcode-20", "Unassigned core range opcode 0x20 received", f_op20, 1008, "connection")

    # 7. Unknown core opcode 0x2F
    f_op2f = make_frame(1, 0x2F, 0, b"data")
    add("invalid-unknown-core-opcode-2f", "Unassigned core range opcode 0x2F received", f_op2f, 1008, "connection")

    # 8. Data frame on StreamID 0
    f_sid0 = make_frame(0, 0x03, 1, bytes([0]) + b"data")
    add("invalid-data-on-stream0", "CONTENT frame transmitted on StreamID 0", f_sid0, 1008, "connection")

    # 9. SETTINGS frame on non-zero StreamID
    f_set_sid1 = make_frame(1, 0x0F, 0, struct.pack("<BIIIHBH", 1, 65535, 1048576, 15000, 100, 0, 0))
    add("invalid-settings-on-stream1", "SETTINGS frame transmitted on StreamID 1", f_set_sid1, 1008, "connection")

    # 10. Truncated SETTINGS payload (17 bytes instead of 18)
    f_set_short = make_frame(0, 0x0F, 0, bytes([1]) * 17)
    add("invalid-settings-truncated", "SETTINGS payload is 17 bytes (expected 18)", f_set_short, 1008, "connection")

    # 11. Truncated USAGE payload (19 bytes instead of 20)
    f_u_short = make_frame(1, 0x06, 0, bytes([0]) * 19)
    add("invalid-usage-truncated", "USAGE payload is 19 bytes (expected 20)", f_u_short, 1008, "connection")

    # 12. Truncated METRICS payload (19 bytes instead of 20)
    f_m_short = make_frame(1, 0x07, 0, bytes([0]) * 19)
    add("invalid-metrics-truncated", "METRICS payload is 19 bytes (expected 20)", f_m_short, 1008, "connection")

    # 13. Non-zero payload on CANCEL
    f_can_nonz = make_frame(1, 0x0A, 0, b"cancel_reason")
    add("invalid-cancel-nonzero-payload", "CANCEL frame carries non-zero payload", f_can_nonz, 1008, "connection")

    # 14. Non-zero payload on PAUSE
    f_pause_nonz = make_frame(1, 0x0B, 0, b"pause_now")
    add("invalid-pause-nonzero-payload", "PAUSE frame carries non-zero payload", f_pause_nonz, 1008, "connection")

    # 15. Non-zero payload on RESUME
    f_res_nonz = make_frame(1, 0x0C, 0, b"resume_now")
    add("invalid-resume-nonzero-payload", "RESUME frame carries non-zero payload", f_res_nonz, 1008, "connection")

    # 16. Inner MsgLen mismatch in ERROR frame
    # Declares MsgLen = 20, but only provides 5 bytes
    err_bad_len = struct.pack("<HHBBH", 1001, 400, 0, 0, 20) + b"hello"
    f_err_bad = make_frame(1, 0x09, 0, err_bad_len)
    add("invalid-error-msglen-mismatch", "ERROR frame MsgLen exceeds actual payload slice", f_err_bad, 1008, "connection")

    # 17. Non-zero reserved field in USAGE
    u_bad_res = struct.pack("<IIIIBBH", 10, 10, 20, 0, 1, 0xFF, 0)
    f_u_bad = make_frame(1, 0x06, 0, u_bad_res)
    add("invalid-usage-reserved-nonzero", "USAGE frame has non-zero Reserved byte", f_u_bad, 1008, "connection")

    # 18. Non-zero reserved field in REWIND
    rw_bad_res = struct.pack("<BBHI", 0x03, 0, 0xFFFF, 10)
    f_rw_bad = make_frame(1, 0x0E, 0, rw_bad_res)
    add("invalid-rewind-reserved-nonzero", "REWIND frame has non-zero Reserved field", f_rw_bad, 1008, "connection")

    return vectors

def build_edge_vectors():
    vectors = []
    def add(vec_id: str, desc: str, raw_bytes: bytes, details: dict):
        vectors.append({
            "id": vec_id,
            "description": desc,
            "raw_hex": raw_bytes.hex(),
            "details": details
        })

    # 1-3. 2-byte UTF-8 character split: 'é' (0xC3 0xA9)
    # Part 1: terminates with 0xC3 (BOUNDARY=0)
    f_split2_1 = make_frame(1, 0x03, 0, bytes([0]) + b"caf" + bytes([0xC3]))
    add("edge-utf8-2byte-split-p1", "2-byte UTF-8 char split at byte 1 (BOUNDARY=0)", f_split2_1, {"char": "é", "split_index": 1})
    # Part 2: starts with 0xA9 (BOUNDARY=1)
    f_split2_2 = make_frame(1, 0x03, 1, bytes([0]) + bytes([0xA9]) + b" latte")
    add("edge-utf8-2byte-split-p2", "2-byte UTF-8 char completed (BOUNDARY=1)", f_split2_2, {"char": "é", "split_index": 2})

    # 4-6. 3-byte UTF-8 character split: '€' (0xE2 0x82 0xAC)
    # Split at byte 1: 0xE2
    f_split3_1 = make_frame(1, 0x03, 0, bytes([0]) + b"cost: " + bytes([0xE2]))
    add("edge-utf8-3byte-split-p1", "3-byte UTF-8 char split at byte 1", f_split3_1, {"char": "€", "split_index": 1})
    # Split at byte 2: 0x82 0xAC
    f_split3_2 = make_frame(1, 0x03, 1, bytes([0]) + bytes([0x82, 0xAC]) + b"50")
    add("edge-utf8-3byte-split-p2", "3-byte UTF-8 char completed", f_split3_2, {"char": "€", "split_index": 3})

    # Split 3-byte char across three separate frames!
    f_split3_tri1 = make_frame(1, 0x03, 0, bytes([0]) + bytes([0xE2]))
    f_split3_tri2 = make_frame(1, 0x03, 0, bytes([0]) + bytes([0x82]))
    f_split3_tri3 = make_frame(1, 0x03, 1, bytes([0]) + bytes([0xAC]))
    add("edge-utf8-3byte-tri-1", "3-byte UTF-8 split across 3 frames (part 1)", f_split3_tri1, {})
    add("edge-utf8-3byte-tri-2", "3-byte UTF-8 split across 3 frames (part 2)", f_split3_tri2, {})
    add("edge-utf8-3byte-tri-3", "3-byte UTF-8 split across 3 frames (part 3)", f_split3_tri3, {})

    # 7-10. 4-byte UTF-8 emoji split: '🚀' (0xF0 0x9F 0x99 0x80)
    # Split at byte 1: 0xF0
    f_split4_1 = make_frame(1, 0x03, 0, bytes([0]) + bytes([0xF0]))
    add("edge-utf8-4byte-split-p1", "4-byte emoji split at byte 1", f_split4_1, {"char": "🚀", "split_index": 1})
    # Split at byte 2: 0x9F
    f_split4_2 = make_frame(1, 0x03, 0, bytes([0]) + bytes([0x9F]))
    add("edge-utf8-4byte-split-p2", "4-byte emoji split at byte 2", f_split4_2, {"char": "🚀", "split_index": 2})
    # Split at byte 3: 0x99 0x80
    f_split4_3 = make_frame(1, 0x03, 1, bytes([0]) + bytes([0x99, 0x80]))
    add("edge-utf8-4byte-split-p3", "4-byte emoji completed at byte 4", f_split4_3, {"char": "🚀", "split_index": 4})

    # 11-12. Split Unicode escape sequence in tool args: '\\u00' then '41'
    tc_esc1 = bytes([0]) + struct.pack("<HB", 0, 0x02) + b'{"code":"\\u00'
    tc_esc2 = bytes([0]) + struct.pack("<HB", 0, 0x04) + b'41"}'
    add("edge-tool-args-split-escape-p1", "Tool args split mid Unicode escape sequence (part 1)",
        make_frame(1, 0x05, 0, tc_esc1), {})
    add("edge-tool-args-split-escape-p2", "Tool args completing Unicode escape sequence (part 2)",
        make_frame(1, 0x05, 0, tc_esc2), {})

    # 13-14. Split JSON key token across tool args: '{"loca' then 'tion":"NYC"}'
    tc_k1 = bytes([0]) + struct.pack("<HB", 0, 0x02) + b'{"loca'
    tc_k2 = bytes([0]) + struct.pack("<HB", 0, 0x04) + b'tion":"NYC"}'
    add("edge-tool-args-split-key-p1", "Tool args split mid JSON key token (part 1)",
        make_frame(1, 0x05, 0, tc_k1), {})
    add("edge-tool-args-split-key-p2", "Tool args completing JSON key token (part 2)",
        make_frame(1, 0x05, 0, tc_k2), {})

    # 15-16. Minimal tool call with empty strings for id and name
    tc_min = bytes([0]) + struct.pack("<HBBH", 0, 0x05, 0, 0) + b'{}'
    add("edge-tool-empty-id-name", "Tool call with 0-length ID and 0-length name",
        make_frame(1, 0x05, 0, tc_min), {})

    # 17. BOUNDARY=1 after BOUNDARY=0 with empty delta
    f_b0_empty_next = make_frame(1, 0x03, 1, bytes([0]))
    add("edge-boundary1-empty-payload", "BOUNDARY=1 frame with empty text delta", f_b0_empty_next, {})

    # 18-20. Large UTF-8 sequence at end of frame
    long_prefix = b"Z" * 1000
    f_edge_long_split = make_frame(1, 0x03, 0, bytes([0]) + long_prefix + bytes([0xF0, 0x9F]))
    add("edge-1k-boundary0-emoji-split", "1KB payload ending on split 4-byte emoji", f_edge_long_split, {})

    # 21. Max CallIndex tool call (CallIndex = 65,535)
    tc_max_idx = bytes([0]) + struct.pack("<HBBH", 65535, 0x05, 2, 4) + b"id" + b"func" + b'{}'
    add("edge-tool-max-call-index", "Tool call with maximum 16-bit CallIndex (65,535)",
        make_frame(1, 0x05, 0, tc_max_idx), {})

    # 22. Multiple choices: ChoiceIndex = 255
    f_max_choice = make_frame(1, 0x03, 1, bytes([255]) + b"Choice 255 text")
    add("edge-content-max-choice-index", "CONTENT frame with maximum choice index (255)", f_max_choice, {})

    # 23. Surrogate pair split across frames in tool args: \uD83D and \uDE00
    tc_surr1 = bytes([0]) + struct.pack("<HB", 0, 0x02) + b'{"emoji":"\\uD83D'
    tc_surr2 = bytes([0]) + struct.pack("<HB", 0, 0x04) + b'\\uDE00"}'
    add("edge-tool-args-surrogate-split-p1", "Tool args split mid surrogate pair (part 1)",
        make_frame(1, 0x05, 0, tc_surr1), {})
    add("edge-tool-args-surrogate-split-p2", "Tool args completing surrogate pair (part 2)",
        make_frame(1, 0x05, 0, tc_surr2), {})

    # 24. Empty reasoning payload (ChoiceIndex = 0 only)
    f_reason_empty = make_frame(1, 0x04, 1, bytes([0]))
    add("edge-reasoning-empty", "REASONING frame with empty delta", f_reason_empty, {})

    return vectors

def build_scenario_vectors():
    scenarios = []

    # Scenario 1: Golden Interop Transcript (Full Happy Path with Text, Tool, Usage, Metrics, End)
    s1_steps = [
        {"direction": "S->C", "description": "Server emits SETTINGS handshake",
         "raw_hex": make_frame(0, 0x0F, 0, struct.pack("<BIIIHBH", 1, 65535, 1048576, 15000, 100, 0, 0)).hex(),
         "expected_client_state": "ESTABLISHED"},
        {"direction": "C->S", "description": "Client initiates session on StreamID 1",
         "raw_hex": make_frame(1, 0x01, 0, b'{"model":"gpt-4o"}').hex(),
         "expected_client_state": "OPENING"},
        {"direction": "S->C", "description": "Server acknowledges session",
         "raw_hex": make_frame(1, 0x02, 0, struct.pack("<IH", 1, 6) + b"gpt-4o").hex(),
         "expected_client_state": "ACTIVE"},
        {"direction": "S->C", "description": "Server streams reasoning block",
         "raw_hex": make_frame(1, 0x04, 1, bytes([0]) + b"Checking weather...").hex(),
         "expected_client_state": "ACTIVE"},
        {"direction": "S->C", "description": "Server starts tool invocation",
         "raw_hex": make_frame(1, 0x05, 0, bytes([0]) + struct.pack("<HBBH", 0, 0x01, 6, 11) + b"call_1" + b"get_weather" + b'{"city":').hex(),
         "expected_client_state": "ACTIVE"},
        {"direction": "S->C", "description": "Server completes tool invocation",
         "raw_hex": make_frame(1, 0x05, 0, bytes([0]) + struct.pack("<HB", 0, 0x04) + b'"Paris"}').hex(),
         "expected_client_state": "ACTIVE"},
        {"direction": "S->C", "description": "Server emits cumulative token usage",
         "raw_hex": make_frame(1, 0x06, 0, struct.pack("<IIIIBBH", 25, 14, 39, 0, 1, 0, 0)).hex(),
         "expected_client_state": "TERMINATING"},
        {"direction": "S->C", "description": "Server emits performance telemetry",
         "raw_hex": make_frame(1, 0x07, 0, struct.pack("<IIIQ", 95, 340, 9200, 0x1122334455667788)).hex(),
         "expected_client_state": "TERMINATING"},
        {"direction": "S->C", "description": "Server terminates session cleanly with STOP",
         "raw_hex": make_frame(1, 0x08, 0, bytes([0x00, 0])).hex(),
         "expected_client_state": "TERMINATED"},
    ]
    scenarios.append({"id": "scenario-1-golden-happy-path", "description": "Full happy path session exchange", "steps": s1_steps})

    # Scenario 2: Pause and Resume with Lossless Delivery
    s2_steps = [
        {"direction": "S->C", "description": "Server emits first content chunk",
         "raw_hex": make_frame(1, 0x03, 1, bytes([0]) + b"Chunk 1").hex(), "expected_client_state": "ACTIVE"},
        {"direction": "C->S", "description": "Client pauses session",
         "raw_hex": make_frame(1, 0x0B, 0, b"").hex(), "expected_client_state": "PAUSED"},
        {"direction": "C->S", "description": "Client resumes session",
         "raw_hex": make_frame(1, 0x0C, 0, b"").hex(), "expected_client_state": "ACTIVE"},
        {"direction": "S->C", "description": "Server delivers drained chunk in FIFO order",
         "raw_hex": make_frame(1, 0x03, 1, bytes([0]) + b"Chunk 2").hex(), "expected_client_state": "ACTIVE"},
        {"direction": "S->C", "description": "Server concludes session",
         "raw_hex": make_frame(1, 0x08, 0, bytes([0x00, 0])).hex(), "expected_client_state": "TERMINATED"},
    ]
    scenarios.append({"id": "scenario-2-pause-resume", "description": "Client pause and clean resume flow", "steps": s2_steps})

    # Scenario 3: Pause Buffer Overflow (ERROR 1006)
    s3_steps = [
        {"direction": "C->S", "description": "Client pauses session",
         "raw_hex": make_frame(1, 0x0B, 0, b"").hex(), "expected_client_state": "PAUSED"},
        {"direction": "S->C", "description": "Server emits session-scoped ERROR 1006 on buffer overflow",
         "raw_hex": make_frame(1, 0x09, 0, struct.pack("<HHBBH", 1006, 0, 0, 0, 8) + b"Overflow").hex(),
         "expected_client_state": "TERMINATED"},
    ]
    scenarios.append({"id": "scenario-3-pause-overflow", "description": "Session termination on pause buffer overflow", "steps": s3_steps})

    # Scenario 4: Pause TTL Expiry (ERROR 1009)
    s4_steps = [
        {"direction": "C->S", "description": "Client pauses session",
         "raw_hex": make_frame(1, 0x0B, 0, b"").hex(), "expected_client_state": "PAUSED"},
        {"direction": "S->C", "description": "Server emits session-scoped ERROR 1009 when retention TTL expires",
         "raw_hex": make_frame(1, 0x09, 0, struct.pack("<HHBBH", 1009, 0, 0, 0, 15) + b"Session Expired").hex(),
         "expected_client_state": "TERMINATED"},
    ]
    scenarios.append({"id": "scenario-4-pause-ttl-expiry", "description": "Session termination on pause retention TTL expiry", "steps": s4_steps})

    # Scenario 5: Dynamic Prompt Steering
    s5_steps = [
        {"direction": "S->C", "description": "Server streams initial tokens",
         "raw_hex": make_frame(1, 0x03, 1, bytes([0]) + b"The history of computers...").hex(), "expected_client_state": "ACTIVE"},
        {"direction": "C->S", "description": "Client issues mid-generation steering instruction",
         "raw_hex": make_frame(1, 0x0D, 0, struct.pack("<H", 10) + b"be concise").hex(), "expected_client_state": "ACTIVE"},
        {"direction": "S->C", "description": "Server streams post-steer concise continuation",
         "raw_hex": make_frame(1, 0x03, 1, bytes([0]) + b"\nBriefly: invented in 20th century.").hex(), "expected_client_state": "ACTIVE"},
        {"direction": "S->C", "description": "Server terminates cleanly",
         "raw_hex": make_frame(1, 0x08, 0, bytes([0x00, 0])).hex(), "expected_client_state": "TERMINATED"},
    ]
    scenarios.append({"id": "scenario-5-dynamic-steer", "description": "Dynamic client prompt steering mid-stream", "steps": s5_steps})

    # Scenario 6: Rewind on Speculative Failover with Tool Call Discard
    s6_steps = [
        {"direction": "S->C", "description": "Server starts speculative tool call",
         "raw_hex": make_frame(1, 0x05, 0, bytes([0]) + struct.pack("<HBBH", 0, 0x01, 6, 8) + b"call_x" + b"bad_tool" + b'{"a":').hex(),
         "expected_client_state": "ACTIVE"},
        {"direction": "S->C", "description": "Server rolls back and discards partial tool call",
         "raw_hex": make_frame(1, 0x0E, 0, struct.pack("<BBHI", 0x05, 0, 0, 0)).hex(),
         "expected_client_state": "ACTIVE"},
        {"direction": "S->C", "description": "Server emits valid content following rollback",
         "raw_hex": make_frame(1, 0x03, 1, bytes([0]) + b"Corrected answer.").hex(),
         "expected_client_state": "ACTIVE"},
        {"direction": "S->C", "description": "Server completes session",
         "raw_hex": make_frame(1, 0x08, 0, bytes([0x00, 0])).hex(), "expected_client_state": "TERMINATED"},
    ]
    scenarios.append({"id": "scenario-6-rewind-failover", "description": "Rewind rollback discarding partial tool call", "steps": s6_steps})

    # Scenario 7: Two Interleaved Sessions on One Connection
    s7_steps = [
        {"direction": "C->S", "description": "Client opens StreamID 1",
         "raw_hex": make_frame(1, 0x01, 0, b'{"model":"gpt-4o"}').hex(), "expected_client_state": "OPENING"},
        {"direction": "C->S", "description": "Client opens StreamID 3 concurrently",
         "raw_hex": make_frame(3, 0x01, 0, b'{"model":"claude"}').hex(), "expected_client_state": "OPENING"},
        {"direction": "S->C", "description": "Server acks StreamID 1",
         "raw_hex": make_frame(1, 0x02, 0, struct.pack("<IH", 1, 6) + b"gpt-4o").hex(), "expected_client_state": "ACTIVE"},
        {"direction": "S->C", "description": "Server acks StreamID 3",
         "raw_hex": make_frame(3, 0x02, 0, struct.pack("<IH", 3, 6) + b"claude").hex(), "expected_client_state": "ACTIVE"},
        {"direction": "S->C", "description": "Server emits content on StreamID 1",
         "raw_hex": make_frame(1, 0x03, 1, bytes([0]) + b"Stream 1 token").hex(), "expected_client_state": "ACTIVE"},
        {"direction": "S->C", "description": "Server interleaves content on StreamID 3",
         "raw_hex": make_frame(3, 0x03, 1, bytes([0]) + b"Stream 3 token").hex(), "expected_client_state": "ACTIVE"},
        {"direction": "S->C", "description": "Server terminates StreamID 1",
         "raw_hex": make_frame(1, 0x08, 0, bytes([0x00, 0])).hex(), "expected_client_state": "TERMINATED"},
        {"direction": "S->C", "description": "Server continues and terminates StreamID 3",
         "raw_hex": make_frame(3, 0x08, 0, bytes([0x00, 0])).hex(), "expected_client_state": "TERMINATED"},
    ]
    scenarios.append({"id": "scenario-7-interleaved-multiplexing", "description": "Two interleaved concurrent streams on single connection", "steps": s7_steps})

    # Scenario 8: Connection-Level Protocol Violation Teardown
    s8_steps = [
        {"direction": "C->S", "description": "Client sends frame with reserved flag bit set",
         "raw_hex": make_frame(1, 0x03, 0x08, bytes([0]) + b"Bad flag").hex(), "expected_client_state": "ACTIVE"},
        {"direction": "S->C", "description": "Server emits connection-level ERROR 1008 and tears down transport",
         "raw_hex": make_frame(0, 0x09, 0, struct.pack("<HHBBH", 1008, 0, 0, 1, 18) + b"Protocol Violation").hex(),
         "expected_client_state": "CLOSED"},
    ]
    scenarios.append({"id": "scenario-8-connection-teardown", "description": "Connection-level protocol violation teardown", "steps": s8_steps})

    return scenarios

def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    vectors_dir = os.path.join(root, "vectors")

    golden = build_golden_vectors()
    with open(os.path.join(vectors_dir, "golden", "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"version": "1.0", "category": "golden", "count": len(golden), "vectors": golden}, f, indent=2)
    print(f"Generated {len(golden)} golden vectors in vectors/golden/manifest.json")

    invalid = build_invalid_vectors()
    with open(os.path.join(vectors_dir, "invalid", "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"version": "1.0", "category": "invalid", "count": len(invalid), "vectors": invalid}, f, indent=2)
    print(f"Generated {len(invalid)} invalid vectors in vectors/invalid/manifest.json")

    edge = build_edge_vectors()
    with open(os.path.join(vectors_dir, "edge", "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"version": "1.0", "category": "edge", "count": len(edge), "vectors": edge}, f, indent=2)
    print(f"Generated {len(edge)} edge vectors in vectors/edge/manifest.json")

    scenarios = build_scenario_vectors()
    with open(os.path.join(vectors_dir, "scenarios", "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"version": "1.0", "category": "scenario", "count": len(scenarios), "vectors": scenarios}, f, indent=2)
    print(f"Generated {len(scenarios)} scenarios in vectors/scenarios/manifest.json")

if __name__ == "__main__":
    main()
