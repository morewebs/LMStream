# LMStream WebTransport / QUIC Transport Binding

> **Status:** Normative Standard  
> **Source of Truth:** Complements `SPEC.md`.

This document specifies the normative transport binding for carrying LMStream frames over WebTransport and QUIC (HTTP/3) streams [RFC 9114, draft-ietf-webtrans-overview].

---

## 1. Overview

WebTransport enables low-latency, multiplexed, bidirectional streaming over HTTP/3 and QUIC. Unlike WebSocket over TCP, QUIC provides independent streams that completely eliminate transport-layer Head-of-Line (HOL) blocking.

---

## 2. Establishment

1. **Protocol Negotiation**: The client initiates an extended HTTP/3 `CONNECT` request with:
   - `:protocol = webtransport`
   - `:path = /lmstream-v1` (or application-defined endpoint)
2. **Session Acceptance**: The server accepts the WebTransport session with an HTTP `200 OK` response.

---

## 3. Dedicated Control Stream & Handshake

1. **Dedicated Control Stream**: Immediately following session establishment, the client **MUST** open a dedicated bidirectional QUIC stream designated as the **Control Stream**.
2. **StreamID 0 Restriction**: The Control Stream is used exclusively for `StreamID 0` frames (`SETTINGS`, `PING`, `PONG`, connection-scoped `ERROR`).
3. **Handshake**: The server's first message on the Control Stream **MUST** be the 18-byte `SETTINGS (0x0F)` frame.

---

## 4. Session Mapping & QUIC Bidirectional Streams

1. **One QUIC Stream Per Session**: Every new LMStream generation session (`StreamID > 0`) is mapped to an independent bidirectional QUIC stream.
2. **StreamID Validation**: Frames emitted on a session QUIC stream **MUST** carry that session's `StreamID` in their 8-byte header. Receivers **MUST** validate that all frames on a session QUIC stream match the assigned `StreamID`.
3. **True HOL Blocking Elimination**: Because each session occupies a distinct QUIC stream, packet drops or backpressure on one session have zero effect on other concurrent sessions.

---

## 5. Frame Mapping

1. **Stream Encoding**: Frames are serialized sequentially as `[8-byte Header | Payload]` on the corresponding QUIC stream.
2. **Size Invariant**: Individual frames **MUST NOT** exceed 65,535 bytes total (payload $\le$ 65,527 bytes).
3. **Datagrams Out of Scope**: WebTransport unreliable datagrams are explicitly out of scope for `LMStream-1.0` (all token and control data requires reliable, ordered delivery).

---

## 6. Keepalive & Teardown

1. **Keepalive**: LMStream `PING` and `PONG` frames operate over the dedicated Control Stream per Decision D14.
2. **Session Teardown**: When a session completes (`END` or session `ERROR`), the sender half-closes the corresponding QUIC stream.
3. **Connection Teardown**: Connection-level errors close the Control Stream and terminate the WebTransport session.

---

## 7. Limitations (Normative)

- **Browser Implementation Maturity**: WebTransport is supported in modern Chromium and Firefox, but client tooling in backend runtimes (e.g. Node.js) remains evolving.
- **TLS Mandate**: WebTransport mandates TLS 1.3 and valid certificates (or pinned WebTransport server certificates).

---

## 8. Binding Conformance Requirements

A compliant WebTransport implementation **MUST**:
1. Allocate a dedicated bidirectional QUIC stream for `StreamID 0` control frames.
2. Exchange `SETTINGS` as the first frame on the Control Stream.
3. Allocate distinct bidirectional QUIC streams for each active session (`StreamID > 0`).
4. Validate that frame `StreamID` matches the assigned session stream.
