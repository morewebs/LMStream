# LMStream: Open Binary Streaming Protocol for LLMs

[![CI](https://github.com/morewebs/lmstream/actions/workflows/ci.yml/badge.svg)](https://github.com/morewebs/lmstream/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Spec License: CC BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Standard: LMStream-1.0](https://img.shields.io/badge/Standard-LMStream--1.0-blue.svg)](SPEC.md)

LMStream is an open standard binary wire protocol designed specifically for Large Language Model (LLM) inference streams, AI agent orchestration, and multi-tenant model gateways.

---

## Why LMStream?

Server-Sent Events (SSE) has hit a hard ceiling:
- **Unidirectional**: No native way to pause, cancel, or steer active inference in-band.
- **Unmultiplexed**: Requires a separate TCP/TLS connection for every concurrent tool or agent call.
- **JSON Bloat**: Inflates token bandwidth by 400%–1000% with repetitive JSON envelopes.
- **Unstandardized Telemetry**: Token accounting, TTFT, and failovers are fragmented across provider-specific headers.

LMStream replaces SSE with an 8-byte binary header, full-duplex control, native multiplexing, and standardized accounting.

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

## Worked Wire Example

A `CONTENT` frame on StreamID 1 carrying `"Hello"` (5 bytes UTF-8) with `BOUNDARY = 1` and `ChoiceIndex = 0`:

```text
01 00 00 00 03 01 06 00 00 48 65 6c 6c 6f
│           │  │  │     │  └─ "Hello" (UTF-8)
│           │  │  │     └──── ChoiceIndex = 0
│           │  │  └────────── Length = 6 (2 bytes LE)
│           │  └───────────── Flags = 0x01 (BOUNDARY = 1, clean UTF-8 boundary)
│           └──────────────── Opcode = 0x03 (CONTENT)
└──────────────────────────── StreamID = 1 (4 bytes LE)
```

---

## TypeScript Quick Example

```typescript
import { WebSocket } from "ws";
import { decodeFrame, encodeFrame, Opcode, LMStreamSession } from "@lmstream/reference";

const ws = new WebSocket("wss://gateway.example.com/v1/stream", ["lmstream-v1"]);
const session = new LMStreamSession(1);

ws.on("open", () => {
  // Initiate session
  const openPayload = new TextEncoder().encode(JSON.stringify({ model: "gpt-4o" }));
  ws.send(encodeFrame({
    header: { streamId: 1, opcode: Opcode.OPEN, flags: 0, length: openPayload.length },
    payload: openPayload,
  }));
});

ws.on("message", (data: Buffer) => {
  const frame = decodeFrame(new Uint8Array(data));
  session.handleFrame(frame);

  console.log("Current text:", session.contentAccumulator);
});
```

---

## Repository Map

- **Specification**:
  - [`SPEC.md`](SPEC.md): Normative protocol standard and single source of truth.
  - [`DECISIONS.md`](DECISIONS.md): Architectural decision records (D1–D15).
  - [`CONVENTIONS.md`](CONVENTIONS.md): Terminology, endianness, and naming rules.
  - [`registry.md`](registry.md): Numerical registries for opcodes, flags, errors, and finish reasons.
  - [`SECURITY.md`](SECURITY.md): Threat model, buffer exhaustion mitigations, and TLS requirements.
  - [`GOVERNANCE.md`](GOVERNANCE.md): Specification lifecycle, errata, and release policy.
  - [`TRACEABILITY.md`](TRACEABILITY.md): Mapping of all normative requirements to test vectors.

- **Transport Bindings**:
  - [`bindings/websocket.md`](bindings/websocket.md): RFC 6455 full-duplex binding (`lmstream-v1`).
  - [`bindings/webtransport-quic.md`](bindings/webtransport-quic.md): HTTP/3 QUIC stream multiplexing.
  - [`bindings/sse.md`](bindings/sse.md): Server-Sent Events JSON fallback profile.
  - [`bindings/grpc.md`](bindings/grpc.md) & [`bindings/lmstream.proto`](bindings/lmstream.proto): gRPC Control + Session envelope.

- **Semantics**:
  - [`semantics/state-machines.md`](semantics/state-machines.md): Connection and session transition tables.
  - [`semantics/flow-control.md`](semantics/flow-control.md): Lossless pause, buffer caps, and dynamic steering.
  - [`semantics/client-algorithms.md`](semantics/client-algorithms.md): Normative pseudocode for UTF-8 boundary assembly, tool call streaming, and rewind.
  - [`semantics/provider-mapping.md`](semantics/provider-mapping.md): Informative mappings from OpenAI, Anthropic, and DeepSeek SSE.

- **Test Vectors & Conformance**:
  - [`vectors/`](vectors/): 145 canonical test vectors across `golden/`, `invalid/`, `edge/`, and `scenarios/`.
  - [`conformance/runner-protocol.md`](conformance/runner-protocol.md): Conformance certification protocol.

- **Reference Implementations**:
  - [`examples/typescript/`](examples/typescript/): Canonical codec, vector generator, mock server, and client demo.
  - [`examples/python/`](examples/python/): Stdlib-only Python codec, validator, and client demo.
  - [`examples/go/`](examples/go/): Pure Go codec and test vector validator.
  - [`examples/rust/`](examples/rust/): Zero-dependency Rust codec and test vector validator.

---

## Licensing

- **Specifications & Documentation**: Creative Commons Attribution 4.0 International ([CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/)).
- **Code, Tools, & Reference Implementations**: [MIT License](LICENSE).
