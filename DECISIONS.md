# LMStream Architectural Decisions (DECISIONS.md)

This document records all architectural decisions for the LMStream protocol specification.
Every normative requirement in `SPEC.md` and related documents traces to these decisions.

---

### D1 — `OPEN` Payload Format

**Question:** How is the session initiation payload structured on the wire?

**Options:**
- A) Compact fixed binary struct.
- B) UTF-8 JSON request document with provider-agnostic schema and optional authentication/metadata fields.
- C) Protocol Buffers binary serialization.

**Choice:** B (UTF-8 JSON request document).

**Rationale:** `OPEN` occurs strictly on the session establishment cold path (once per generation request). The latency and bandwidth benefits of binary framing do not apply here. Using a standardized JSON document allows flexible model configuration, provider-agnostic request parameters, tool definitions, and optional auth metadata without requiring fragile binary schema versioning on the wire.

**Spec impact:** `SPEC.md` §4.3 defines `OPEN` payload as UTF-8 encoded JSON.

---

### D2 — Connection-Scoped Control Frames

**Question:** How are connection-scoped control frames distinguished from session-scoped frames?

**Options:**
- A) A dedicated flag bit in the frame header.
- B) Distinct opcode ranges for connection-level vs. session-level operations.
- C) Reserve **StreamID 0** for connection-scoped frames (`SETTINGS`, `PING`, `PONG`, connection-scoped `ERROR`).

**Choice:** C (Reserve StreamID 0).

**Rationale:** Follows established HTTP/2 (RFC 7540) and QUIC (RFC 9000) design patterns. Stream multiplexers naturally route StreamID 0 directly to connection management state, avoiding special-casing in frame decoders. Stream-level operations always use non-zero StreamIDs.

**Spec impact:** `SPEC.md` §2 and §5 designate StreamID 0 exclusively for connection control. Non-control opcodes on StreamID 0 MUST trigger connection `ERROR 1008`.

---

### D3 — StreamID Allocation & Multiplexing

**Question:** How are StreamIDs assigned to avoid collision in multiplexed bidirectional environments?

**Options:**
- A) Random 32-bit UUIDs/integers.
- B) Uncoordinated sequential allocation with collision arbitration.
- C) Client-initiated sessions allocate odd StreamIDs monotonically starting at 1; server-initiated sessions allocate even StreamIDs monotonically starting at 2.

**Choice:** C (Client = odd from 1; Server = even from 2).

**Rationale:** Directly aligns with HTTP/2 stream allocation. Eliminates round-trip coordination for stream creation and guarantees disjoint identifier spaces. StreamIDs monotonically increase and cannot be reused on the same connection.

**Spec impact:** `SPEC.md` §5 defines stream allocation invariants and exhaustion handling.

---

### D4 — Unknown Opcode Policy

**Question:** How must an endpoint behave when receiving an unrecognized opcode?

**Options:**
- A) Silently discard all unrecognized opcodes.
- B) Immediately terminate the connection on any unrecognized opcode.
- C) Core range (`0x01–0x2F`): MUST emit `ERROR 1008 (Protocol Violation)` and terminate connection. Extension range (`0x30–0xEF`): MUST ignore and discard the frame. Control/experimental range (`0xF0–0xFF`): MUST ignore unless negotiated.

**Choice:** C.

**Rationale:** Enforces strict protocol compliance on the core specification to prevent subtle bugs and corrupt streams from going undetected, while providing graceful forward-compatibility for protocol extensions.

**Spec impact:** `SPEC.md` §3 and §6 mandate strict rejection for unknown core opcodes and safe skipping for unknown extension opcodes.

---

### D5 — `STEER` Payload Format

**Question:** How should runtime prompt steering instructions be formatted on the wire?

**Options:**
- A) JSON object envelope with metadata.
- B) Binary layout: `[TextLen: u16 LE | UTF-8 String]`.

**Choice:** B (`[TextLen: u16 LE | UTF-8 String]`).

**Rationale:** Steering occurs dynamically during active generation (hot path). A compact binary length-prefixed UTF-8 string avoids JSON parsing overhead in gateways and inference engines, ensuring sub-millisecond propagation into the model's token sampling loop.

**Spec impact:** `SPEC.md` §4.3 defines `STEER` payload layout.

---

### D6 — `SETTINGS` Frame Layout

**Question:** What is the binary structure of the connection initialization `SETTINGS` frame?

**Options:**
- A) Variable-length list of key-value tuples.
- B) JSON configuration dictionary.
- C) Fixed 18-byte binary layout: `Version (u8) | MaxFrameSize (u32 LE) | PauseBufferCap (u32 LE) | HeartbeatMs (u32 LE) | MaxConcurrentSessions (u16 LE) | Reserved (u8) | Reserved (u8)`.

**Choice:** C (Fixed 18-byte binary layout).

**Rationale:** The initial handshake must be parsed deterministically with zero memory allocation or decoding ambiguity. Fixed-width fields prevent buffer overflow risks and establish baseline operational limits before any session data flows.

**Spec impact:** `SPEC.md` §4.3 defines `SETTINGS` payload layout and negotiation rules.

---

### D7 — Multi-Choice Representation (`n > 1`)

**Question:** How does LMStream represent completions with multiple choices/branches?

**Options:**
- A) Disallow multi-choice in LMStream; require separate sessions.
- B) Allocate distinct StreamIDs for each choice index.
- C) Senders MUST emit `ChoiceIndex = 0` in v1; receivers MUST accept and expose any `ChoiceIndex` (`0x00–0xFF`).

**Choice:** C.

**Rationale:** Streaming `n > 1` completions is rare in modern agent workflows due to GPU latency and cost. However, reserving an 8-bit `ChoiceIndex` in all data payloads (`CONTENT`, `REASONING`, `TOOL_CALL`, `END`) ensures complete wire compatibility for branching without changing frame layouts in v2.

**Spec impact:** `SPEC.md` §4 data frames mandate `ChoiceIndex` byte at payload offset 0.

---

### D8 — Server-Sent Events (SSE) Binding Profile

**Question:** How does LMStream bind to Server-Sent Events (SSE) given SSE's unidirectional, text-based limitations?

**Options:**
- A) Base64-encode raw binary frames into standard SSE `data:` fields.
- B) Define a normative JSON event profile mapping each S→C opcode to an SSE event name (`event: content`, `event: reasoning`, etc.), with no C→S capability.

**Choice:** B (Normative JSON event profile).

**Rationale:** SSE is widely used in legacy browser and mobile apps where binary WebSockets or WebTransport may be blocked. Base64 adds 33% overhead and still requires binary decoders. A structured JSON event mapping provides natural SSE interoperability while making the absence of client-to-server frames explicit.

**Spec impact:** `bindings/sse.md` specifies the event names and JSON envelopes.

---

### D9 — PAUSE TTL Expiry Handling

**Question:** What action is taken when a paused session exceeds the server's maximum retention timeout (TTL)?

**Options:**
- A) Silent drop of the session.
- B) Generic connection error `1000 General Error`.
- C) Terminate the session with session-scoped `ERROR 1009 (Session Expired)`. Connection remains active; client MAY re-OPEN.

**Choice:** C (`ERROR 1009 Session Expired`).

**Rationale:** Clear differentiation between transient network issues, memory buffer exhaustion (`ERROR 1006`), and inactivity timeouts (`ERROR 1009`). Session-scoped error leaves the underlying transport connection open for other active sessions.

**Spec impact:** `SPEC.md` §6 defines error code 1009; `semantics/flow-control.md` details eviction.

---

### D10 — WebSocket Frame Mapping & Fragmentation

**Question:** Are senders permitted to fragment a single LMStream frame across multiple WebSocket binary frames?

**Options:**
- A) Senders MAY fragment freely; receivers must assemble.
- B) Senders MUST NOT fragment a LMStream frame across multiple WS messages (1 LMStream frame = 1 WS binary message); receivers MUST support reassembly if intermediaries fragment.

**Choice:** B.

**Rationale:** 1:1 mapping between LMStream frames and WebSocket binary messages drastically minimizes allocation and copies in modern engines. However, standard RFC 6455 intermediaries may re-frame messages, so compliant receivers must reassemble.

**Spec impact:** `bindings/websocket.md` specifies sender prohibition and receiver tolerance.

---

### D11 — SSE Event Envelope Structure

**Question:** What is the exact payload structure for events in the SSE binding?

**Options:**
- A) Verbose OpenAI-compatible delta objects.
- B) Compact JSON object per event with field names directly matching LMStream payload fields (`c` for content, `r` for reasoning, `idx` for choice, `usage`, `metrics`).

**Choice:** B (Compact 1:1 JSON object).

**Rationale:** Minimizes serialization overhead and maintains exact semantic fidelity with LMStream binary frames.

**Spec impact:** `bindings/sse.md` documents envelope field mappings.

---

### D12 — Reference Implementation Language & Vector Generation

**Question:** Which language generates canonical test vectors and serves as the reference client?

**Options:**
- A) Python.
- B) Rust.
- C) **TypeScript** generates canonical vectors and serves as reference client; Python, Go, and Rust serve as independent validation implementations.

**Choice:** C.

**Rationale:** Node.js (≥ 22) provides zero-dependency native WebSocket support and strict typing. Web and TypeScript developers represent the majority of LLM API consumers. Validating generated vectors against independent Python, Go, and Rust implementations guarantees the specification is free of language-specific assumptions.

**Spec impact:** Tooling and conformance test suite architecture (`examples/`, `vectors/`).

---

### D13 — Standard & Code Licensing

**Question:** What license applies to LMStream specifications versus implementations?

**Options:**
- A) Apache 2.0 for all files.
- B) MIT for all files.
- C) **Documentation and Specifications:** Creative Commons Attribution 4.0 International ([CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/)).  
  **Code, Tools, & Test Harness:** [MIT License](LICENSE).

**Choice:** C.

**Rationale:** Standard industry practice for open standards (W3C / IETF / OpenAPI). Ensures open, unencumbered implementation and distribution of code while maintaining clear attribution and integrity for standard documents.

**Spec impact:** `LICENSE` file updated with dual licensing terms.

---

### D14 — Heartbeat & Keepalive Architecture

**Question:** How are heartbeats and connection liveness maintained across varied transports?

**Options:**
- A) Transport-specific keepalive only (WS ping, QUIC ping, HTTP/2 ping).
- B) Protocol-level `PING` and `PONG` frames on **StreamID 0** across all bidirectional transports; transport keepalives MAY supplement.

**Choice:** B (LMStream `PING`/`PONG` on StreamID 0).

**Rationale:** Intermediate proxies and gateways often terminate or fail to forward transport-level keepalives. Uniform application-level `PING`/`PONG` guarantees true end-to-end liveness detection across WebSocket, WebTransport, and gRPC.

**Spec impact:** `SPEC.md` §4.3 defines `PING`/`PONG` payload (8-byte unix timestamp millisecond u64 LE).

---

### D15 — gRPC Transport Binding

**Question:** Should gRPC be supported in v1, and how are LMStream frames carried over gRPC?

**Options:**
- A) Defer to post-v1 extension.
- B) Single multiplexed bidirectional RPC carrying all frames.
- C) **Per-session Session RPC + Control RPC** (mirroring WebTransport topology); frames carried as opaque bytes in a single-field wrapper message (`message Frame { bytes frame = 1; }`).
- D) Model individual LMStream payloads as Protobuf message types.

**Choice:** C.

**Rationale:** gRPC is ubiquitous in server-to-server inference clusters, model gateways, and agent orchestration meshes. Carrying frames as opaque bytes preserves `SPEC.md` as the single source of truth without duplicating the vector surface in protobuf. Using separate Control and Session RPCs reuses HTTP/2's native per-stream multiplexing and flow control, eliminating head-of-line blocking between concurrent sessions.

**Spec impact:** `bindings/grpc.md` and `bindings/lmstream.proto`. No changes required to `SPEC.md` or test vectors.
