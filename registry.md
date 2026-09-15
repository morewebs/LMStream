# LMStream Protocol Registry

> **Status:** Normative Standard  
> **Source of Truth:** Defines numerical registries and range allocations for LMStream.

---

## 1. Opcode Registry

### 1.1. Allocation Policy

| Range (Hex) | Range (Dec) | Classification | Unknown Opcode Behavior | Registration Policy |
|---|---|---|---|---|
| `0x00` | `0` | Reserved | MUST trigger `ERROR 1008` | Never allocated |
| `0x01–0x2F` | `1–47` | Core Protocol | MUST trigger `ERROR 1008` | Requires Standards Track RFC |
| `0x30–0xEF` | `48–239` | Standard Extensions | MUST be safely skipped | Specification Required / Review |
| `0xF0–0xFF` | `240–255` | Experimental / Private | Ignored unless negotiated | Private Use (no registration) |

### 1.2. Registered Core Opcodes

| Hex | Name | Direction | Payload Description | Normative Reference |
|---|---|---|---|---|
| `0x01` | `OPEN` | C → S | UTF-8 JSON request configuration | `SPEC.md` §4.3.1 |
| `0x02` | `OPEN_ACK` | S → C | SessionID (u32 LE) + Model name | `SPEC.md` §4.3.2 |
| `0x03` | `CONTENT` | S → C | ChoiceIndex (u8) + Text delta | `SPEC.md` §4.1.1 |
| `0x04` | `REASONING` | S → C | ChoiceIndex (u8) + Text delta | `SPEC.md` §4.1.1 |
| `0x05` | `TOOL_CALL` | S → C | ChoiceIndex + CallIndex + Flags + Args | `SPEC.md` §4.1.2 |
| `0x06` | `USAGE` | S → C | 20-byte cumulative token counters | `SPEC.md` §4.2.1 |
| `0x07` | `METRICS` | S → C | 20-byte TTFT & duration telemetry | `SPEC.md` §4.2.2 |
| `0x08` | `END` | S → C | FinishReason (u8) + ChoiceIndex (u8) | `SPEC.md` §4.2.3 |
| `0x09` | `ERROR` | Bidi | Code + UpstreamStatus + Scope + Msg | `SPEC.md` §4.2.4 |
| `0x0A` | `CANCEL` | C → S | Zero-length (Length = 0) | `SPEC.md` §4.3.3 |
| `0x0B` | `PAUSE` | C → S | Zero-length (Length = 0) | `SPEC.md` §4.3.3 |
| `0x0C` | `RESUME` | C → S | Zero-length (Length = 0) | `SPEC.md` §4.3.3 |
| `0x0D` | `STEER` | C → S | TextLen (u16 LE) + UTF-8 instruction | `SPEC.md` §4.3.4 |
| `0x0E` | `REWIND` | S → C | TargetOp (u8) + ByteOffset (u32 LE) | `SPEC.md` §4.3.5 |
| `0x0F` | `SETTINGS` | Bidi / S → C | 18-byte connection configuration | `SPEC.md` §4.3.6 |
| `0x10` | `PING` | Bidi | 8-byte millisecond timestamp (u64 LE) | `SPEC.md` §4.3.7 |
| `0x11` | `PONG` | Bidi | 8-byte echoed timestamp (u64 LE) | `SPEC.md` §4.3.7 |

---

## 2. Header Flags Registry

| Bit Position | Mask | Name | Permitted Opcodes | Description |
|---|---|---|---|---|
| Bit 0 | `0x01` | `FLAG_BOUNDARY` | `CONTENT`, `REASONING` | `1` = clean UTF-8 boundary; `0` = trailing partial sequence |
| Bit 1 | `0x02` | `FLAG_COMPRESSED` | Reserved | Reserved for negotiated compression algorithms |
| Bits 2–7 | `0x04–0x80` | Reserved | None | MUST be set to 0; non-zero causes `ERROR 1008` |

---

## 3. Tool Flags Registry (Payload Offset 3)

| Bit Position | Mask | Name | Description |
|---|---|---|---|
| Bit 0 | `0x01` | `TOOL_START` | Initial frame of tool call; contains Id, Name, and initial Args |
| Bit 1 | `0x02` | `TOOL_CONT` | Intermediate frame; contains raw argument delta |
| Bit 2 | `0x04` | `TOOL_END` | Terminal frame; signals complete argument stream |
| Bits 3–7 | `0x08–0x80` | Reserved | MUST be set to 0 |

---

## 4. Error Code Registry

### 4.1. Core Catalog (1001–1009)

| Code | Name | Default Scope | Description |
|---|---|---|---|
| `1001` | `BAD_REQUEST` | Session | Malformed `OPEN` payload, invalid parameters, or unparseable JSON |
| `1002` | `AUTH_FAILED` | Connection | Missing, invalid, or expired authentication credentials |
| `1003` | `RATE_LIMITED` | Session | Upstream provider rate limit reached (HTTP 429) |
| `1004` | `MODEL_OVERLOADED` | Session | Upstream provider overloaded or capacity exhausted (HTTP 503) |
| `1005` | `UPSTREAM_ERROR` | Session | Unrecoverable error from upstream inference service (HTTP 500/502) |
| `1006` | `BUFFER_OVERFLOW` | Session | Paused session buffer exceeded `PauseBufferCap` |
| `1007` | `INVALID_STATE` | Session | Frame received that violates state machine rules |
| `1008` | `PROTOCOL_VIOLATION` | Connection | Frame length > 65,527, reserved bit non-zero, unknown core opcode |
| `1009` | `SESSION_EXPIRED` | Session | Paused session exceeded server retention timeout TTL |

### 4.2. Range Allocations

- **`1000–1999`**: Core protocol errors. Requires specification revision.
- **`2000–2999`**: Standard extension errors.
- **`3000–3999`**: Gateway / Vendor-specific application errors.

---

## 5. Finish Reason Registry

| Value (Hex) | Name | Description |
|---|---|---|
| `0x00` | `STOP` | Model emitted natural end-of-sequence token |
| `0x01` | `LENGTH` | Output truncated due to `max_tokens` or model context limit |
| `0x02` | `TOOL_CALLS` | Generation halted to wait for client tool execution |
| `0x03` | `CONTENT_FILTER` | Output flagged and halted by safety moderation filters |
| `0x04` | `CANCELLED` | Session aborted due to client `CANCEL` |
| `0x05–0xFF` | Reserved | Future allocation |

---

## 6. Compression Algorithm Registry (Reserved)

| ID (Hex) | Algorithm | Notes |
|---|---|---|
| `0x00` | `NONE` | Uncompressed raw payloads |
| `0x01` | `ZSTD` | Zstandard block compression |
| `0x02` | `SNAPPY` | Google Snappy compression |
| `0x03` | `GZIP` | Deflate / Gzip |
