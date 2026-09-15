# Implementing a LMStream Client

A step-by-step checklist of normative requirements (MUSTs) for building a compliant LMStream client library.

---

## 1. Connection & Handshake

1. **Subprotocol Negotiation**: When establishing a WebSocket connection, you **MUST** request `Sec-WebSocket-Protocol: lmstream-v1` and abort if rejected (`bindings/websocket.md` §2).
2. **Await Server Settings**: You **MUST** wait for the server's initial `SETTINGS (0x0F)` frame on `StreamID 0` before emitting any session requests (`SPEC.md` §5.1).
3. **Heartbeat Maintenance**: If the server emits a `PING` frame on `StreamID 0`, you **MUST** respond with an identical `PONG` frame echoing the timestamp within `HeartbeatMs` (`SPEC.md` §4.3.7).

---

## 2. Session StreamID Allocation

1. **Odd Numbers Only**: Client-initiated sessions **MUST** allocate odd StreamIDs monotonically: $1, 3, 5, 7, \dots$ (`SPEC.md` §5.1).
2. **No StreamID Recycling**: You **MUST NOT** reuse a StreamID on the same connection (`SPEC.md` §5.1).

---

## 3. Client Algorithms

1. **UTF-8 Assembly**:
   - If `BOUNDARY = 1`, render text immediately.
   - If `BOUNDARY = 0`, buffer trailing partial bytes and prepend to the next frame on that channel (`semantics/client-algorithms.md` §1).
2. **Tool-Call Reassembly**:
   - Do NOT parse JSON per chunk.
   - Buffer raw `ArgsDelta` string fragments.
   - Parse JSON exactly once when `ToolFlags & END` (`0x04`) arrives (`semantics/client-algorithms.md` §2).
3. **Rewind Handling**:
   - On receiving `REWIND`, truncate channel text buffer to `ByteOffset`.
   - If `TargetOpcode = TOOL_CALL` and `ByteOffset = 0`, discard all partial tool calls for that choice index (`semantics/client-algorithms.md` §3).

---

## 4. Flow Control

1. **Pause & Resume**: Emit zero-length `PAUSE (0x0B)` or `RESUME (0x0C)` frames (`SPEC.md` §4.3.3).
2. **Steer**: Deliver text deltas using `[TextLen: u16 LE | UTF-8]` (`SPEC.md` §4.3.4).
3. **Cancel**: Emit zero-length `CANCEL (0x0A)` to abort the session (`SPEC.md` §4.3.3).
