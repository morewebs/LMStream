# LMStream gRPC Transport Binding

> **Status:** Normative Standard  
> **Source of Truth:** Complements `SPEC.md` and `bindings/lmstream.proto`.

This document specifies the normative transport binding for carrying LMStream frames over gRPC and HTTP/2 (Decision D15).

---

## 1. Overview

gRPC is the standard RPC framework for high-throughput server-to-server microservices, model gateways, and distributed inference clusters. By modeling LMStream frames as opaque bytes in a lightweight wrapper, LMStream reuses HTTP/2's native multiplexing and per-stream backpressure without creating a secondary schema definition.

---

## 2. Service Definition & Envelope

The binding is defined by the following Protocol Buffers definition in [`bindings/lmstream.proto`](lmstream.proto):

```protobuf
syntax = "proto3";
package lmstream.v1;

// One raw LMStream frame (8-byte header + payload), opaque to gRPC.
message Frame {
  bytes frame = 1;  // MUST NOT exceed 65,535 bytes; MUST NOT be gRPC-compressed.
}

service LMStream {
  // Connection lifetime. StreamID-0 frames only:
  // server's first message is SETTINGS; then PING/PONG, connection ERROR.
  rpc Control(stream Frame) returns (stream Frame);

  // One call per LMStream session. First client message is OPEN.
  // Every frame carries the session StreamID; receivers validate it.
  rpc Session(stream Frame) returns (stream Frame);
}
```

---

## 3. Framing & Buffer Size Limits

1. **One Frame Per Message**: Exactly one LMStream frame **MUST** correspond to exactly one gRPC `Frame` message (`frame` field).
2. **Compression Prohibition**: gRPC-level compression (`grpc-encoding`) **MUST NOT** be applied to LMStream messages. Compression is reserved at the LMStream protocol layer via the `COMPRESSED` header flag.
3. **Configured Message Size Limits**: Both client and server gRPC channel configurations **MUST** configure maximum inbound and outbound message sizes to at least **65,539 bytes**:
   $$\text{Max Envelope Size} = 65,535 \text{ (max LMStream frame)} + 1 \text{ (tag byte)} + 3 \text{ (varint length)} = 65,539 \text{ bytes}$$

---

## 4. Connection Handshake & Control RPC

1. **Control RPC**: The client **MUST** invoke `lmstream.v1.LMStream/Control` upon establishing the transport channel.
2. **Initial SETTINGS**: The server's first message on `Control` **MUST** be an 18-byte `SETTINGS (0x0F)` frame with `StreamID = 0`.
3. **StreamID 0 Exclusivity**: All frames sent or received on `Control` **MUST** have `StreamID = 0`. Any non-zero `StreamID` on `Control` **MUST** result in an `ERROR 1008` and termination of the RPC.
4. **MaxConcurrentSessions**: The server enforces `MaxConcurrentSessions` across the connection. Servers **SHOULD** configure HTTP/2 `MAX_CONCURRENT_STREAMS` $\ge \text{MaxConcurrentSessions} + 1$.

---

## 5. Session RPC Mapping

1. **One RPC Per Session**: Each new generation session opens an independent `lmstream.v1.LMStream/Session` call.
2. **Initial Client Message**: The first message sent by the client on `Session` **MUST** be an `OPEN (0x01)` frame carrying an odd `StreamID`.
3. **Frame StreamID Invariant**: All subsequent frames exchanged on that RPC **MUST** carry the same `StreamID`. Receivers **MUST** validate that incoming frames match the session's assigned `StreamID`.
4. **Per-Session Flow Control**: HTTP/2 stream-level `WINDOW_UPDATE` provides native per-session backpressure. A stalled or paused session does not backpressure or block sibling session streams.

---

## 6. Teardown & Status Mapping

1. **Client Half-Close**: If a client half-closes its request stream on `Session` without previously sending `CANCEL`, the server **MUST** treat this as an implicit `CANCEL`.
2. **Server Half-Close**: The server half-closes its response stream only after transmitting `END (0x08)` or a session-scoped `ERROR (0x09)`.
3. **gRPC Status Codes**: gRPC status codes map transport-level failures only:

| gRPC Status Code | LMStream Context |
|---|---|
| `OK (0)` | Normal stream completion |
| `CANCELLED (1)` | Client aborted the RPC |
| `DEADLINE_EXCEEDED (4)` | Pause TTL exceeded or request timeout |
| `UNAVAILABLE (14)` | Transport channel disconnected or broker restart |

---

## 7. Keepalive

LMStream-level `PING (0x10)` and `PONG (0x11)` frames operate continuously on the `Control` RPC per Decision D14. Native HTTP/2 `PING` frames **MAY** supplement transport liveness.

---

## 8. Limitations (Normative)

- **Browser Incompatibility**: Browsers cannot initiate bidirectional gRPC streaming (`grpc-web` supports server-streaming only). Browser clients **MUST** use WebSocket, WebTransport, or SSE.
- **HTTP/2 Transport HOL**: While HTTP/2 provides independent stream flow control, underlying TCP packet loss can still introduce transport-layer HOL blocking. High-packet-loss environments **SHOULD** use WebTransport/QUIC or gRPC-over-HTTP/3.
- **Server-Initiated Sessions**: Server-initiated sessions (even StreamIDs per D3) are deferred to `LMStream-1.1`.

---

## 9. Binding Conformance Requirements

A compliant gRPC implementation **MUST**:
1. Serve the `lmstream.v1.LMStream` service interface without modifying message field structures.
2. Send `SETTINGS` on `Control` as the first server message.
3. Validate that all frames on `Control` carry `StreamID = 0`.
4. Validate that all frames on `Session` carry the session's allocated `StreamID`.
5. Support frame payloads up to 65,527 bytes without truncation.
