# Changelog

All notable changes to the LMStream specification, transport bindings, and reference implementations will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0-rc1] - 2026-09-15

### Added
- **Core Specification (`SPEC.md`)**:
  - Fixed 8-byte frame header (`StreamID`, `Opcode`, `Flags`, `Length`).
  - Derivation of 65,527-byte maximum payload cap.
  - Normative `BOUNDARY` flag polarity (`1` = complete codepoint, `0` = trailing incomplete bytes).
  - Complete core opcode registry (`0x01–0x11`) with unknown-opcode handling rules (D4).
  - Fixed-layout accounting frames: `USAGE` (20B) and `METRICS` (20B).
  - In-band flow control: zero-length `CANCEL`, `PAUSE`, `RESUME`.
  - Dynamic prompt steering (`STEER`) with binary length prefix.
  - Server-emitted speculative rollback (`REWIND`) with offset-0 tool discard invariant.
- **Architectural Decisions (`DECISIONS.md`)**:
  - Signed resolutions for decisions D1 through D15.
- **Transport Bindings**:
  - WebSocket (`bindings/websocket.md`): `lmstream-v1` subprotocol, 1:1 message mapping, HOL statement.
  - WebTransport / QUIC (`bindings/webtransport-quic.md`): HTTP/3 CONNECT, dedicated control stream, per-session QUIC streams.
  - Server-Sent Events (`bindings/sse.md`): JSON event profile for S→C opcodes.
  - gRPC (`bindings/grpc.md`, `bindings/lmstream.proto`): Control + Session envelope.
- **Normative Semantics**:
  - State machines (`semantics/state-machines.md`).
  - Flow control and buffer capacity eviction (`semantics/flow-control.md`).
  - Client algorithms for UTF-8 boundary assembly and tool call reassembly (`semantics/client-algorithms.md`).
  - Informative provider mapping (`semantics/provider-mapping.md`).
- **Test Vectors & Manifests**:
  - 145 canonical test vectors (69 golden, 18 invalid, 22 edge, 8 scenarios).
  - JSON Schema definition (`vectors/schema/manifest-schema.json`).
  - Normative requirement traceability matrix (`TRACEABILITY.md`).
- **Reference Implementations**:
  - **TypeScript**: Canonical codec, vector generator, mock server, client session state machine, WebSocket & gRPC demos.
  - **Python**: Stdlib-only codec, vector runner, and WebSocket client demo.
  - **Go**: Pure Go codec and test vector runner.
  - **Rust**: Zero-dependency crate codec and test vector runner.
- **Conformance & CI**:
  - Conformance protocol specification (`conformance/runner-protocol.md`).
  - Multi-platform GitHub Actions CI matrix (`.github/workflows/ci.yml`).
- **Documentation**:
  - Quickstart guide, Frame reference, Implementing a client/server guides, SSE comparison, FAQ.
