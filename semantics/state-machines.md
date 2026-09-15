# LMStream State Machines

> **Status:** Normative Standard  
> **Source of Truth:** Complements `SPEC.md` §5, §6, and §7.

This document normatively specifies the connection and session lifecycles for LMStream implementations, including formal state transition tables and frame exchange sequence diagrams.

---

## 1. Connection State Machine

A LMStream connection governs the underlying transport link (WebSocket, WebTransport/QUIC, or gRPC). Connection-level frames (`SETTINGS`, `PING`, `PONG`, connection `ERROR`) operate strictly on **StreamID 0**.

### 1.1. States

- **`IDLE`**: Initial state prior to transport establishment.
- **`CONNECTING`**: Transport layer handshake in progress (e.g. WebSocket upgrade, QUIC handshake, gRPC Control RPC invocation).
- **`HANDSHAKE`**: Transport established. Waiting for server `SETTINGS` frame.
- **`ESTABLISHED`**: `SETTINGS` frame exchanged. Multiplexed sessions may now be opened.
- **`CLOSING`**: Connection teardown initiated (via connection-scoped `ERROR` or transport close).
- **`CLOSED`**: Transport is disconnected. No further data may be transmitted.

### 1.2. Transition Table

| Current State | Event / Frame Received | Action | Next State |
|---|---|---|---|
| `IDLE` | Client initiates connection | Open transport with subprotocol `lmstream-v1` | `CONNECTING` |
| `CONNECTING` | Transport open success | Server sends `SETTINGS` on StreamID 0 | `HANDSHAKE` |
| `CONNECTING` | Transport failure / Subprotocol reject | Abort connection | `CLOSED` |
| `HANDSHAKE` | Client receives `SETTINGS` (StreamID 0) | Validate Version=1, store caps, client may send `SETTINGS` | `ESTABLISHED` |
| `HANDSHAKE` | Non-SETTINGS frame on StreamID 0 | Emit `ERROR 1008` (Scope=CONNECTION) | `CLOSING` |
| `ESTABLISHED` | `PING` received on StreamID 0 | Immediately emit `PONG` with identical timestamp | `ESTABLISHED` |
| `ESTABLISHED` | Client opens session (StreamID > 0) | Route to Session State Machine | `ESTABLISHED` |
| `ESTABLISHED` | Connection `ERROR 1008` / Transport Close | Abort all sessions, close transport | `CLOSING` |
| `CLOSING` | Transport flush & close | Clean up resources | `CLOSED` |

---

## 2. Session State Machine

Every individual generation request runs as an independent session identified by a non-zero `StreamID` (odd numbers for client-initiated sessions).

### 2.1. States

- **`IDLE`**: StreamID is unused.
- **`OPENING`**: Client emitted `OPEN`. Awaiting server `OPEN_ACK`.
- **`ACTIVE`**: Generation in progress. Server emitting `CONTENT`, `REASONING`, `TOOL_CALL`, or `REWIND`.
- **`PAUSED`**: Client emitted `PAUSE`. Server buffering generated deltas up to `PauseBufferCap`.
- **`TERMINATING`**: Terminal sequence initiated (`USAGE`, `METRICS`, or pending `END`).
- **`TERMINATED`**: Terminal frame (`END` or session-scoped `ERROR`) sent/received. StreamID closed permanently.

### 2.2. Session Transition Table

| Current State | Trigger / Frame Received | Action | Next State |
|---|---|---|---|
| `IDLE` | Client sends `OPEN` (StreamID $N$, odd) | Send `OPEN` payload, start session timer | `OPENING` |
| `OPENING` | Server receives `OPEN` | Validate JSON payload; if invalid emit `ERROR 1001` | `OPENING` / `TERMINATED` |
| `OPENING` | Server sends `OPEN_ACK` | Return resolved model identifier | `ACTIVE` |
| `ACTIVE` | Server sends `CONTENT` / `REASONING` / `TOOL_CALL` | Stream token deltas to client channel | `ACTIVE` |
| `ACTIVE` | Client sends `STEER` | Server injects text into prompt context | `ACTIVE` |
| `ACTIVE` | Server sends `REWIND` | Client truncates channel buffer to `ByteOffset` | `ACTIVE` |
| `ACTIVE` | Client sends `PAUSE` | Server begins buffering tokens in memory | `PAUSED` |
| `ACTIVE` | Client sends `CANCEL` | Server aborts upstream generation, sends `END (CANCELLED)` | `TERMINATED` |
| `ACTIVE` | Server sends `USAGE` / `METRICS` | Transmit terminal accounting data | `TERMINATING` |
| `ACTIVE` | Server sends `END` | Clean generation finish, close StreamID | `TERMINATED` |
| `ACTIVE` | Upstream failure / Error | Server emits session `ERROR 1003–1005` | `TERMINATED` |
| `PAUSED` | Client sends `RESUME` | Server flushes buffered deltas in FIFO order | `ACTIVE` |
| `PAUSED` | Buffer exceeds `PauseBufferCap` | Server emits session `ERROR 1006 (Buffer Overflow)` | `TERMINATED` |
| `PAUSED` | Pause time exceeds server TTL | Server emits session `ERROR 1009 (Session Expired)` | `TERMINATED` |
| `PAUSED` | Client sends `CANCEL` | Server discards buffer, aborts upstream, sends `END` | `TERMINATED` |
| `TERMINATING` | Server sends `END` | Deliver final finish reason, close stream | `TERMINATED` |
| `TERMINATED` | Any frame on closed StreamID | Silently drop or emit `ERROR 1007 (Invalid State)` | `TERMINATED` |

---

## 3. Frame Sequence Diagrams

### 3.1. Standard Happy Path Generation

```text
Client                                           Server
  |                                                |
  | -------- Transport Connect (lmstream-v1) -----> |
  | <------- SETTINGS (StreamID=0, Ver=1) -------- |
  |                                                |
  | === StreamID 1 Session Initiated ============= |
  | -------- OPEN (StreamID=1, JSON payload) ----> |
  | <------- OPEN_ACK (StreamID=1, "gpt-4o") ----- |
  | <------- CONTENT (StreamID=1, "The ") -------- |
  | <------- CONTENT (StreamID=1, "answer ") ----- |
  | <------- CONTENT (StreamID=1, "is 42.") ------ |
  | <------- USAGE (StreamID=1, 20B counts) ------ |
  | <------- METRICS (StreamID=1, 20B telemetry) - |
  | <------- END (StreamID=1, Finish=STOP) ------- |
  | === StreamID 1 Closed ======================== |
```

### 3.2. Flow Control: Pause, Buffer, and Resume

```text
Client                                           Server
  |                                                |
  | <------- CONTENT (StreamID=1, "Chunk A") ----- |
  | -------- PAUSE (StreamID=1) -----------------> |
  |          [Server buffers "Chunk B" in queue]   |
  |          [Server buffers "Chunk C" in queue]   |
  | -------- RESUME (StreamID=1) ----------------> |
  | <------- CONTENT (StreamID=1, "Chunk B") ----- |
  | <------- CONTENT (StreamID=1, "Chunk C") ----- |
  | <------- END (StreamID=1, Finish=STOP) ------- |
```

### 3.3. Pause Overflow (ERROR 1006)

```text
Client                                           Server
  |                                                |
  | -------- PAUSE (StreamID=1) -----------------> |
  |          [Buffered bytes > PauseBufferCap]     |
  | <------- ERROR (StreamID=1, Code=1006, --------|
  |                 Scope=SESSION, "Overflow")     |
  | === StreamID 1 Closed (Connection alive) ===== |
  |                                                |
  | -------- OPEN (StreamID=3, new session) -----> |  <-- Other streams unaffected
```

### 3.4. Failover & REWIND

```text
Client                                           Server
  |                                                |
  | <------- CONTENT (StreamID=1, "Once upon ") -- |
  | <------- CONTENT (StreamID=1, "a bad token") - |
  |          [Speculative check fails on server]   |
  | <------- REWIND (Target=CONTENT, Offset=10) -- | (Rollback to byte 10 "Once upon ")
  | <------- CONTENT (StreamID=1, "a time...") --- |
  | <------- END (StreamID=1, Finish=STOP) ------- |
```
