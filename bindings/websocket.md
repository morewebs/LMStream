# LMStream WebSocket Transport Binding

> **Status:** Normative Standard  
> **Source of Truth:** Complements `SPEC.md`.

This document specifies the normative transport binding for carrying LMStream frames over WebSocket connections (RFC 6455).

---

## 1. Overview

WebSocket provides full-duplex, message-oriented bidirectional streaming over a single TCP connection. It is the primary transport binding for web browsers and edge application gateways.

---

## 2. Establishment & Subprotocol Negotiation

1. **Subprotocol Header**: During the HTTP WebSocket upgrade handshake, the client **MUST** include:
   ```http
   Sec-WebSocket-Protocol: lmstream-v1
   ```
2. **Server Confirmation**: The server **MUST** respond with:
   ```http
   Sec-WebSocket-Protocol: lmstream-v1
   ```
3. **No Downgrade**: If the server does not accept or recognize `lmstream-v1`, the connection **MUST** fail immediately. Endpoints **MUST NOT** silently fall back to raw text or other subprotocols.

---

## 3. Frame Mapping & Fragmentation (Decision D10)

1. **Binary Data Type**: All LMStream frames **MUST** be transmitted as WebSocket **Binary Messages** (`opcode 0x02` in RFC 6455). WebSocket Text Messages (`0x01`) **MUST NOT** be used.
2. **Sender Fragmentation Policy**: Senders **MUST NOT** fragment a single LMStream frame across multiple WebSocket frames. Exactly one LMStream frame **MUST** correspond to exactly one WebSocket binary message.
3. **Receiver Invariant**: Intermediary network proxies may re-frame WebSocket messages. Compliant receivers **MUST** support accumulating fragmented WebSocket frames to reconstruct the underlying LMStream frame.

---

## 4. Session Mapping & Head-of-Line Blocking (Normative)

1. **Multiplexing Topology**: Multiple concurrent LMStream sessions (`StreamID > 0`) are multiplexed over the single underlying WebSocket connection.
2. **Head-of-Line Limitation**: Because WebSocket operates over an ordered TCP stream, the WebSocket binding exhibits transport-level Head-of-Line (HOL) blocking. A packet drop on one session stalls all other sessions at the TCP layer.
3. **Isolation Invariant**: Despite transport-level HOL blocking, session-level faults **MUST NOT** compromise peer sessions. Specifically, if one session pauses and causes buffer overflow, the server **MUST** emit session-scoped `ERROR 1006` on that `StreamID`; the WebSocket connection and all other sessions **MUST** remain active.

---

## 5. Connection-Scope Frames & Handshake

Immediately following WebSocket connection establishment:
1. The server **MUST** emit a `SETTINGS (0x0F)` frame on `StreamID 0` as its first message.
2. The client **MUST** wait for the server `SETTINGS` frame before initiating any session (`OPEN`).
3. Connection-level `PING`, `PONG`, and connection `ERROR` frames are carried on `StreamID 0`.

---

## 6. Keepalive & Heartbeats (Decision D14)

1. **Primary Protocol Heartbeat**: Liveness is verified via LMStream application-level `PING (0x10)` and `PONG (0x11)` frames sent on `StreamID 0`.
2. **Transport Keepalives**: Native WebSocket Ping/Pong frames (`opcode 0x09` / `0x0A`) **MAY** supplement, but do not replace, LMStream-level heartbeats.

---

## 7. Error & Close Code Mapping

When a LMStream connection is closed due to a protocol or transport error, the WebSocket close code **MUST** map as follows:

| LMStream Event / Error | WebSocket Close Code | Close Reason |
|---|---|---|
| Clean Shutdown | `1000 Normal Closure` | Connection concluded |
| Protocol Violation (`1008`) | `1002 Protocol Error` | Malformed header, reserved bits, invalid opcode |
| Auth Failure (`1002`) | `1008 Policy Violation` | Authentication rejected |
| Server Internal Error (`1005`) | `1011 Internal Error` | Upstream failure / Gateway crash |

---

## 8. Limitations (Normative)

- **TCP HoL Blocking**: Applications requiring strict per-stream delivery isolation across high-latency mobile networks **SHOULD** use the WebTransport/QUIC binding.
- **Message Size Limits**: Browsers and reverse proxies (e.g. NGINX, Cloudflare) often enforce default maximum WebSocket message sizes (e.g. 1 MiB or 64 KiB). Senders **MUST** respect the negotiated `MaxFrameSize` in `SETTINGS` (maximum 65,535 bytes total frame length).

---

## 9. Binding Conformance Requirements

A compliant WebSocket implementation **MUST**:
1. Negotiate `lmstream-v1` subprotocol strictly.
2. Deliver server `SETTINGS` on `StreamID 0` as the first message.
3. Transmit all LMStream frames as binary messages.
4. Echo `PING` timestamps on `StreamID 0` via `PONG` within `HeartbeatMs`.
