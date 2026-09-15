# LMStream Conventions & Terminology (CONVENTIONS.md)

This document establishes the normative terminology, naming rules, data representation standards, and structural guidelines across all LMStream specifications, transport bindings, and reference implementations.

---

## 1. Conformance Terminology (RFC 2119 / RFC 8174)

The key words **"MUST"**, **"MUST NOT"**, **"REQUIRED"**, **"SHALL"**, **"SHALL NOT"**, **"SHOULD"**, **"SHOULD NOT"**, **"RECOMMENDED"**, **"NOT RECOMMENDED"**, **"MAY"**, and **"OPTIONAL"** in this document and all normative LMStream specifications are to be interpreted as described in BCP 14 [RFC 2119] [RFC 8174] when, and only when, they appear in all capitals.

---

## 2. Document Status & Normative Labeling

Every document and document section in the LMStream standard is explicitly classified:
- **Normative**: Imposes mandatory, binding requirements on compliant implementations. Any deviation constitutes non-conformance. Normative documents include:
  - `SPEC.md`
  - `bindings/websocket.md`
  - `bindings/webtransport-quic.md`
  - `bindings/sse.md`
  - `bindings/grpc.md`
  - `bindings/lmstream.proto`
  - `semantics/state-machines.md`
  - `semantics/flow-control.md`
  - `semantics/client-algorithms.md`
  - `registry.md`
  - `vectors/schema/manifest-schema.json`
- **Informative**: Provides background, architecture, recommendations, or operational guidance without imposing requirements. Conformance testing does not evaluate informative content. Examples include:
  - `semantics/provider-mapping.md`
  - `docs/*`
  - `README.md`
  - Explanatory notes labeled `(Informative)` within normative documents.

---

## 3. Core Terminology & Architectural Concepts

To avoid ambiguity across different network layers and language ecosystems, the following terms MUST be used consistently:

- **Connection**: An active, underlying transport-layer communication channel established between a client and a server (e.g., a single WebSocket connection, a QUIC connection, or a gRPC HTTP/2 channel).
- **Stream**: A multiplexed logical bidirectional byte flow identified by a 32-bit unsigned integer (`StreamID`). StreamID 0 is reserved for connection-scoped control frames (`SETTINGS`, `PING`, `PONG`, connection `ERROR`). Non-zero StreamIDs carry individual LLM sessions.
- **Session**: A logical interaction lifecycle representing a single inference generation cycle. Initiated by an `OPEN` frame on a unique `StreamID`, acknowledged with `OPEN_ACK`, streamed via data frames, and terminated by an `END` or session-scoped `ERROR` frame.
- **Channel**: A semantic sub-stream of generation within a single session (e.g., content channel, reasoning channel, tool call channel).
- **Frame**: The fundamental atomic unit of LMStream data transfer. Every frame consists of an 8-byte fixed header followed by a variable-length payload of 0 to 65,527 bytes.
- **Chunk / Delta**: An application-level incremental piece of output emitted by an LLM (e.g., a text token delta, a tool argument fragment), carried within a frame payload.

---

## 4. Binary Data Representation & Endianness

All multi-byte numeric fields in the LMStream protocol MUST follow strict Little-Endian (LE) byte ordering:

- **`u8`**: 8-bit unsigned integer (1 byte).
- **`u16`**: 16-bit unsigned integer (2 bytes), Little-Endian.
- **`u32`**: 32-bit unsigned integer (4 bytes), Little-Endian.
- **`u64`**: 64-bit unsigned integer (8 bytes), Little-Endian.
- **Float32**: IEEE 754 32-bit single-precision floating point, Little-Endian.
- **Strings**: Variable-length character sequences MUST be encoded as raw UTF-8 bytes without BOM (Byte Order Mark) or null terminators unless explicitly prefixed with a length.

---

## 5. Naming Conventions

- **Opcode Names**: MUST be written in uppercase snake case (`UPPER_SNAKE_CASE`), e.g., `OPEN`, `OPEN_ACK`, `CONTENT`, `REASONING`, `TOOL_CALL`, `USAGE`, `METRICS`, `PAUSE`, `RESUME`, `STEER`, `REWIND`, `SETTINGS`, `PING`, `PONG`, `END`, `ERROR`.
- **Header & Flag Names**: MUST be written in uppercase snake case (`UPPER_SNAKE_CASE`), e.g., `FLAG_BOUNDARY`, `FLAG_START`, `FLAG_CONT`, `FLAG_END`.
- **Payload Field Names**: In specification prose and diagrams, written in PascalCase (e.g., `StreamID`, `ChoiceIndex`, `CallIndex`, `TextLen`, `PromptTokens`).
- **File Names**: Lowercase kebab-case (`file-name.md`, `runner-protocol.md`), except root governance/meta documents which are uppercase (`SPEC.md`, `AGENT.md`, `PLAN.md`, `DECISIONS.md`, `CONVENTIONS.md`, `SECURITY.md`, `GOVERNANCE.md`, `TRACEABILITY.md`, `LICENSE`, `README.md`).

---

## 6. Diagram Standards

All frame layouts and binary structures MUST be depicted using byte-accurate ASCII diagrams with bit or byte offsets clearly marked:

```text
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           StreamID                            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|    Opcode     |     Flags     |            Length             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                     Payload Data (0..65527)                  ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

---

## 7. Protocol & Document Versioning

- **Working Drafts**: Tracked as `draft-lmstream-01`, `draft-lmstream-02`, etc.
- **Formal Release**: Standardized as `LMStream-1.0`. Subsequent backwards-compatible revisions use semantic minor versions (`LMStream-1.1`). Any backwards-incompatible wire change requires a major version increment (`LMStream-2.0`).
- **Wire Version Byte**: The `SETTINGS` frame conveys the active protocol version as `0x01` for `LMStream-1.x`.
- **WebSocket Subprotocol**: Negotiated using the exact string `lmstream-v1`.
