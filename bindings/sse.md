# LMStream Server-Sent Events (SSE) Binding

> **Status:** Normative Standard  
> **Source of Truth:** Complements `SPEC.md`.

This document specifies the Server-Sent Events (SSE) profile for LMStream (Decisions D8 and D11), providing a text/JSON fallback for environments where full-duplex binary transports are unavailable.

---

## 1. Overview

Server-Sent Events (W3C SSE) provides unidirectional, text-based streaming over standard HTTP/1.1 and HTTP/2 connections. Because SSE is strictly unidirectional (Server → Client), client control frames (`CANCEL`, `PAUSE`, `RESUME`, `STEER`) cannot be transmitted over the SSE stream.

---

## 2. Establishment

1. **Client Request**:
   ```http
   GET /v1/stream HTTP/1.1
   Accept: text/event-stream
   Cache-Control: no-cache
   ```
2. **Server Response**:
   ```http
   HTTP/1.1 200 OK
   Content-Type: text/event-stream; charset=utf-8
   Cache-Control: no-cache
   Connection: keep-alive
   ```

---

## 3. Normative Limitations: Absence of Client-to-Server Frames

> [!WARNING]
> **Normative Transport Limitation**:  
> In this binding, all Client → Server LMStream frames (`CANCEL`, `PAUSE`, `RESUME`, `STEER`, `PING`) are **UNAVAILABLE**.
> - **Cancellation**: The client aborts generation strictly by terminating the underlying HTTP connection.
> - **Pause / Resume**: Impossible over standard SSE.
> - **Dynamic Steering**: Impossible over standard SSE.

---

## 4. Event Envelope & JSON Profile (Decisions D8 & D11)

Each Server → Client LMStream frame is mapped to a named SSE event with a single compact JSON object in the `data:` field.

```text
event: <opcode_name>
data: {"sid": 1, ...}

```

### 4.1. Field Mapping Table

| LMStream Opcode | SSE Event Name | JSON Payload Fields |
|---|---|---|
| `SETTINGS (0x0F)` | `settings` | `{"v": 1, "max_frame": 65535, "pause_cap": 1048576, "heartbeat_ms": 15000}` |
| `OPEN_ACK (0x02)` | `open_ack` | `{"sid": 1, "model": "gpt-4o"}` |
| `CONTENT (0x03)` | `content` | `{"sid": 1, "idx": 0, "b": 1, "c": "Hello"}` |
| `REASONING (0x04)` | `reasoning` | `{"sid": 1, "idx": 0, "b": 1, "r": "Step 1..."}` |
| `TOOL_CALL (0x05)` | `tool_call` | `{"sid": 1, "idx": 0, "call_idx": 0, "flags": 5, "id": "call_1", "name": "weather", "args": "{\"city\":"}` |
| `USAGE (0x06)` | `usage` | `{"sid": 1, "prompt": 12, "comp": 45, "total": 57, "cached": 0, "attempts": 1}` |
| `METRICS (0x07)` | `metrics` | `{"sid": 1, "ttft_ms": 140, "duration_ms": 520, "tok_sec": 8550, "key_id": "a1b2c3d4"}` |
| `REWIND (0x0E)` | `rewind` | `{"sid": 1, "target": 3, "idx": 0, "offset": 10}` |
| `END (0x08)` | `end` | `{"sid": 1, "idx": 0, "reason": "stop"}` |
| `ERROR (0x09)` | `error` | `{"sid": 1, "code": 1005, "status": 500, "scope": "session", "msg": "Provider failed"}` |

---

## 5. Handshake & Initial Events

1. The server **MUST** emit `event: settings` as the very first event on the SSE stream.
2. The server **MUST** follow with `event: open_ack` prior to emitting content deltas.
3. The stream terminates with `event: end` or `event: error`, after which the server closes the HTTP connection.

---

## 6. Binding Conformance Requirements

A compliant SSE server **MUST**:
1. Emit `event: settings` before any session events.
2. Use the exact JSON field names defined in the mapping table.
3. Terminate the stream cleanly with `event: end` or `event: error`.
