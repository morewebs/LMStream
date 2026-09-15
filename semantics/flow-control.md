# LMStream Flow Control & Steering

> **Status:** Normative Standard  
> **Source of Truth:** Complements `SPEC.md` §4.3 and §7.

This document normatively specifies the mechanics of session flow control (`PAUSE`, `RESUME`), buffer limits, timeout eviction, dynamic prompt steering (`STEER`), and server rollbacks (`REWIND`).

---

## 1. Flow Control Contract: PAUSE and RESUME

In agentic and interactive workflows, clients frequently need to halt output generation (e.g., to await user confirmation, throttle client rendering, or synchronize external tool invocations) without aborting the session.

### 1.1. Invariants

1. **Explicit Signalling**: The client pauses a stream by sending a zero-length `PAUSE` frame (`0x0B`, `Length = 0`) on that session's `StreamID`.
2. **Lossless Buffering**: Upon receipt of `PAUSE`, the server **MUST NOT** discard upstream LLM tokens. The server **MUST** queue newly generated frames in an internal FIFO memory buffer.
3. **Accounting Independence**: Background token consumption continues during pause until the upstream provider completes or pauses. Token counts in `USAGE` and wall-clock times in `METRICS` continue accumulating normally.
4. **Resumption**: When the client sends `RESUME` (`0x0C`, `Length = 0`), the server **MUST** drain the queued frames in strict FIFO order to the client before transmitting newly generated frames.

---

## 2. Buffer Limits & Eviction

Unbounded pausing poses severe server memory exhaustion risks. LMStream mitigates this through negotiated buffer caps and retention timers.

### 2.1. Buffer Capacity (`PauseBufferCap`)

- The maximum buffered bytes allowed per paused session is negotiated in the initial `SETTINGS` handshake via `PauseBufferCap` (default: `1,048,576` bytes = 1 MiB).
- **Overflow Invariant**: If the total byte size of queued payloads for a paused session exceeds `PauseBufferCap`, the server **MUST** immediately terminate the session by transmitting:
  - Opcode: `ERROR (0x09)`
  - Code: `1006 (Buffer Overflow)`
  - Scope: `0x00 (SESSION)`
  - Message: `"Paused stream buffer exceeded negotiated capacity"`
- **Connection Survival**: An `ERROR 1006` is strictly session-scoped. The underlying connection and all other concurrent sessions **MUST NOT** be terminated.

### 2.2. Pause Retention Timeout (TTL) & ERROR 1009

- Servers enforce a maximum duration that a session may remain in the `PAUSED` state (default: 60 seconds, or implementation-configured TTL).
- If no `RESUME` or `CANCEL` is received before the timer expires, the server **MUST** evict the session and transmit:
  - Opcode: `ERROR (0x09)`
  - Code: `1009 (Session Expired)` (Decision D9)
  - Scope: `0x00 (SESSION)`
  - Message: `"Session paused state expired due to inactivity"`
- **Client Recovery**: Upon receiving `ERROR 1009`, the client **MAY** open a new session (`OPEN`) using a fresh `StreamID` and resubmit its request context.

---

## 3. Dynamic Steering Semantics (`STEER`)

Dynamic steering allows an orchestrator or user to guide an ongoing generation loop without discarding prior output.

### 3.1. Wire Format & Delivery

The client emits `STEER` (`0x0D`) on an active session:
- Payload: `[TextLen: u16 LE | UTF-8 String]` (Decision D5).

### 3.2. Server Execution Rules

1. **Context Insertion**: Upon receiving `STEER`, the server immediately passes the steering text to the model sampling controller or appends it to the active generation prompt prefix.
2. **Subsequent Output Only**: `STEER` takes effect on tokens generated **after** receipt. It does not rewind, erase, or modify tokens already transmitted.
3. **No Implicit Rewind**: A `STEER` frame **MUST NOT** trigger a channel rewind. If a rewind is required, the server **MUST** explicitly emit a `REWIND` frame prior to streaming redirected content.

---

## 4. Server-Emitted Rewind Semantics (`REWIND`)

The `REWIND` (`0x0E`) frame provides a standard wire mechanism for servers to roll back generated tokens.

### 4.1. Use Cases

- **Speculative Decoding Rollback**: Speculative draft tokens rejected by the verification model.
- **Provider Failover**: An upstream provider fails mid-stream; the gateway falls back to a secondary provider and rewinds to the last verified checkpoint.

### 4.2. Invariants

- **Channel Truncation**: The client maintains the cumulative byte length of text received on each channel (`CONTENT`, `REASONING`). On receiving `REWIND`, the client **MUST** truncate that channel's accumulated buffer to `ByteOffset`.
- **Offset Zero Tool Discard**: If `TargetOpcode = 0x05 (TOOL_CALL)` and `ByteOffset = 0`, the client **MUST** discard all partially assembled state for that tool call index.
- **Unidirectional in v1**: In `LMStream-1.0`, `REWIND` is **Server → Client ONLY**. Clients **MUST NOT** emit `REWIND` to the server; servers receiving `REWIND` **MUST** reject it with `ERROR 1008`.
