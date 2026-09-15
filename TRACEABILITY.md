# LMStream Normative Requirement Traceability Matrix (TRACEABILITY.md)

> **Status:** Normative Traceability Matrix  
> **Source of Truth:** Maps all normative statements in `SPEC.md` to test vector IDs in `vectors/`.

---

## 1. Frame Header & Binary Layout (§2)

| Section | Normative Statement | Verification Vector / Status |
|---|---|---|
| §2.1 | Frame begins with fixed 8-byte header followed by payload | All golden & edge vectors (`golden-*`, `edge-*`) |
| §2.2 | Multi-byte integers MUST be Little-Endian | `golden-settings-*`, `golden-usage-*`, `golden-metrics-*` |
| §2.3 | Payload length MUST NOT exceed 65,527 bytes | Verified: `golden-content-max-payload` (65,527B pass), `invalid-length-exceeds-max` (65,528B fail) |
| §2.4 | `BOUNDARY = 1` indicates frame ends on complete UTF-8 codepoint | `golden-content-*`, `edge-utf8-2byte-split-p2`, `edge-utf8-3byte-split-p2`, `edge-utf8-4byte-split-p3` |
| §2.4 | `BOUNDARY = 0` indicates trailing incomplete UTF-8 bytes | `golden-content-boundary-0-partial`, `edge-utf8-2byte-split-p1`, `edge-utf8-3byte-split-p1`, `edge-utf8-4byte-split-p1` |
| §2.4 | BOUNDARY applies strictly to `CONTENT` and `REASONING` | Verified in schema & `golden-tool-*` |
| §2.4 | Reserved flags (Bits 1–7) MUST be zero on send; non-zero causes `ERROR 1008` | `invalid-reserved-flag-bit1`, `invalid-reserved-flag-bit2`, `invalid-reserved-flag-bit7` |

---

## 2. Opcode Registry (§3)

| Section | Normative Statement | Verification Vector / Status |
|---|---|---|
| §3.2 | Core opcodes 0x01–0x11 supported | `golden-*` coverage across all core opcodes |
| §3.3 | Unknown opcode in core range (0x01–0x2F) MUST trigger `ERROR 1008` | `invalid-unknown-core-opcode-00`, `invalid-unknown-core-opcode-20`, `invalid-unknown-core-opcode-2f` |
| §3.3 | Unknown opcode in extension range (0x30–0xEF) MUST be skipped | Not vector-testable at L1 codec (tested in L2 harness) |

---

## 3. Data & Accounting Payloads (§4.1 & §4.2)

| Section | Normative Statement | Verification Vector / Status |
|---|---|---|
| §4.1.1 | `ChoiceIndex = 0` emitted in v1; receivers accept any `0x00–0xFF` | `golden-content-choice-1`, `edge-content-max-choice-index` |
| §4.1.2 | `TOOL_CALL` `START` flag carries complete unfragmented `ToolName` | `golden-tool-single-frame`, `golden-tool-frag-start` |
| §4.1.2 | Raw JSON args delta passthrough | `golden-tool-frag-cont`, `golden-tool-frag-end`, `edge-tool-args-*` |
| §4.2.1 | `USAGE` 20-byte fixed layout | `golden-usage-zeros`, `golden-usage-standard`, `golden-usage-large`, `invalid-usage-truncated` |
| §4.2.1 | `AttemptCount > 1` reflects cumulative tokens across retries | `golden-usage-failover-attempts` |
| §4.2.1 | `USAGE` reserved bytes MUST be zero | `invalid-usage-reserved-nonzero` |
| §4.2.2 | `METRICS` 20-byte fixed layout with `TokensPerSec` x 100 | `golden-metrics-fast`, `golden-metrics-slow`, `invalid-metrics-truncated` |
| §4.2.3 | `END` finish reasons 0x00–0x04 | `golden-end-stop`, `golden-end-length`, `golden-end-tool_calls`, `golden-end-content_filter`, `golden-end-cancelled` |
| §4.2.4 | `ERROR` code, upstream status, scope, and length-checked message | `golden-error-*`, `invalid-error-msglen-mismatch` |

---

## 4. Control Payloads (§4.3)

| Section | Normative Statement | Verification Vector / Status |
|---|---|---|
| §4.3.1 | `OPEN` payload is UTF-8 JSON document | `golden-open-minimal`, `golden-open-rich`, `golden-open-tools` |
| §4.3.2 | `OPEN_ACK` confirms StreamID and resolved model | `golden-open-ack-1`, `golden-open-ack-3` |
| §4.3.3 | `CANCEL`, `PAUSE`, `RESUME` MUST have zero length | `golden-cancel-*`, `golden-pause-*`, `golden-resume-*`, `invalid-cancel-nonzero-payload`, `invalid-pause-nonzero-payload`, `invalid-resume-nonzero-payload` |
| §4.3.4 | `STEER` length-prefixed UTF-8 instruction | `golden-steer-concise`, `golden-steer-french`, `golden-steer-format` |
| §4.3.5 | `REWIND` channel rollback with offset-0 tool discard invariant | `golden-rewind-content-zero`, `golden-rewind-content-offset`, `golden-rewind-tool-discard`, `invalid-rewind-reserved-nonzero` |
| §4.3.6 | `SETTINGS` 18-byte fixed layout on StreamID 0 | `golden-settings-default`, `golden-settings-custom`, `invalid-settings-on-stream1`, `invalid-settings-truncated` |
| §4.3.7 | `PING`/`PONG` 8-byte timestamp on StreamID 0 | `golden-ping-*`, `golden-pong-*` |

---

## 5. Sessions, Multiplexing & Flow Control (§5, §6, §7)

| Section | Normative Statement | Verification Vector / Status |
|---|---|---|
| §5.1 | StreamID 0 reserved for connection frames | `invalid-data-on-stream0`, `invalid-settings-on-stream1` |
| §5.1 | Client sessions odd, server sessions even | Verified in scenario vectors (`scenario-1`, `scenario-7`) |
| §5.2 | Terminal ordering: DATA -> USAGE -> METRICS -> END | `scenario-1-golden-happy-path` |
| §5.3 | Interleaved sessions on single connection | `scenario-7-interleaved-multiplexing` |
| §6.2 | Scope 0x00 terminates session; connection survives | `scenario-3-pause-overflow`, `scenario-4-pause-ttl-expiry` |
| §6.2 | Scope 0x01 terminates connection | `scenario-8-connection-teardown` |
| §7.1 | PAUSE lossless buffering and RESUME FIFO draining | `scenario-2-pause-resume` |
| §7.1 | Pause buffer overflow triggers `ERROR 1006` | `scenario-3-pause-overflow` |
| §7.1 | Pause TTL expiry triggers `ERROR 1009` | `scenario-4-pause-ttl-expiry` |
| §7.2 | Dynamic STEER mid-generation | `scenario-5-dynamic-steer` |
| §7.3 | REWIND speculative failover with tool discard | `scenario-6-rewind-failover` |

---

## 6. Transport & Security Statements (Not Vector-Testable)

The following normative statements govern network-level or deployment configurations and cannot be verified via raw binary frame vectors:
- TLS 1.3 requirement on public networks (`SECURITY.md` §2.1).
- WebSocket subprotocol `lmstream-v1` negotiation (`bindings/websocket.md` §2). Tested via L2 conformance runner.
- QUIC stream multiplexing and HTTP/3 CONNECT (`bindings/webtransport-quic.md`).
- HTTP/2 `MAX_CONCURRENT_STREAMS` configuration (`bindings/grpc.md` §4).
