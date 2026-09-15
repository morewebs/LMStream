# Implementing a LMStream Server / Gateway

A guide for backend authors, proxies, and inference gateways implementing the LMStream protocol.

---

## 1. Initial Connection Handshake

1. **SETTINGS First**: The very first frame emitted by the server on a new connection **MUST** be an 18-byte `SETTINGS (0x0F)` frame on `StreamID 0` (`SPEC.md` §4.3.6).
2. **Cap Advertisement**: Advertise `MaxFrameSize` (up to 65,535), `PauseBufferCap` (default 1 MiB), and `HeartbeatMs` (default 15,000).

---

## 2. Session Lifecycle & Terminal Sequence

For each session request:
1. Receive `OPEN (0x01)` from client. Validate JSON schema. If invalid, return session-scoped `ERROR 1001`.
2. Emit `OPEN_ACK (0x02)` acknowledging the session StreamID and confirming the resolved model string.
3. Stream content: Arbitrarily interleave `CONTENT (0x03)`, `REASONING (0x04)`, `TOOL_CALL (0x05)`.
4. **Terminal Ordering Invariant**:
   - Zero or one `USAGE (0x06)` frame.
   - Zero or one `METRICS (0x07)` frame.
   - Exactly one `END (0x08)` frame (or session-scoped `ERROR`).
   - Never emit frames on that StreamID after `END`.

---

## 3. Tool-Call Invariants

- Senders **MUST NOT** fragment function names. `ToolName` must be complete in the `START` frame (`SPEC.md` §4.1.2).
- Pass raw JSON arguments through as string slices without re-serializing.

---

## 4. Flow Control & Buffer Management

- On receiving `PAUSE (0x0B)`, queue upstream tokens in a FIFO memory buffer without loss (`semantics/flow-control.md` §1).
- If buffered bytes exceed `PauseBufferCap`, terminate the session with session-scoped `ERROR 1006 (Buffer Overflow)`. Keep connection alive.
- If pause duration exceeds server TTL, terminate the session with session-scoped `ERROR 1009 (Session Expired)`.
- On receiving `RESUME (0x0C)`, flush queued frames in strict FIFO order before sending new frames.
