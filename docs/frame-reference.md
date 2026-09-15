# LMStream Frame Reference

Comprehensive quick-reference for the 8-byte LMStream header, byte offsets, and all opcode layouts.

---

## 1. Frame Header Layout

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

| Field | Offset | Width | Type | Notes |
|---|---|---|---|---|
| `StreamID` | 0 | 4 | `u32 LE` | `0` = connection control; Odd = client session; Even = server |
| `Opcode` | 4 | 1 | `u8` | `0x01–0x2F` Core; `0x30–0xEF` Extension |
| `Flags` | 5 | 1 | `u8` | Bit 0 = `BOUNDARY`; Bits 1–7 = Reserved (MUST be 0) |
| `Length` | 6 | 2 | `u16 LE` | Payload byte length ($0 \le \text{Length} \le 65,527$) |
| `Payload` | 8 | `Length` | `bytes` | Opcode-specific bytes |

---

## 2. Core Opcode Summary

| Hex | Opcode | Direction | Fixed / Dynamic Payload | Description |
|---|---|---|---|---|
| `0x01` | `OPEN` | C → S | Dynamic (JSON) | Request initiation |
| `0x02` | `OPEN_ACK` | S → C | Dynamic | SessionID (u32 LE) + Model name |
| `0x03` | `CONTENT` | S → C | Dynamic | ChoiceIndex (u8) + UTF-8 text delta |
| `0x04` | `REASONING` | S → C | Dynamic | ChoiceIndex (u8) + UTF-8 thought delta |
| `0x05` | `TOOL_CALL` | S → C | Dynamic | Choice + CallIndex + Flags + Args |
| `0x06` | `USAGE` | S → C | Fixed (20B) | Prompt, Comp, Total, Cached tokens |
| `0x07` | `METRICS` | S → C | Fixed (20B) | TTFT, Duration, Tok/s, ObfuscatedKeyID |
| `0x08` | `END` | S → C | Fixed (2B) | FinishReason (u8) + ChoiceIndex (u8) |
| `0x09` | `ERROR` | Bidi | Dynamic | Code + UpstreamStatus + Scope + Msg |
| `0x0A` | `CANCEL` | C → S | Fixed (0B) | Abort stream |
| `0x0B` | `PAUSE` | C → S | Fixed (0B) | Halt stream emission |
| `0x0C` | `RESUME` | C → S | Fixed (0B) | Resume stream emission |
| `0x0D` | `STEER` | C → S | Dynamic | TextLen (u16 LE) + UTF-8 instruction |
| `0x0E` | `REWIND` | S → C | Fixed (8B) | TargetOp + Choice + ByteOffset |
| `0x0F` | `SETTINGS` | Bidi | Fixed (18B) | Version, MaxFrame, PauseCap, Heartbeat |
| `0x10` | `PING` | Bidi | Fixed (8B) | Unix millisecond timestamp (u64 LE) |
| `0x11` | `PONG` | Bidi | Fixed (8B) | Echoed millisecond timestamp (u64 LE) |

---

## 3. Error Code Catalog

- `1001`: `BAD_REQUEST` (malformed JSON or invalid parameters)
- `1002`: `AUTH_FAILED` (unauthorized or expired credentials)
- `1003`: `RATE_LIMITED` (upstream HTTP 429)
- `1004`: `MODEL_OVERLOADED` (upstream HTTP 503)
- `1005`: `UPSTREAM_ERROR` (upstream HTTP 500/502)
- `1006`: `BUFFER_OVERFLOW` (paused buffer exceeded `PauseBufferCap`)
- `1007`: `INVALID_STATE` (state machine violation)
- `1008`: `PROTOCOL_VIOLATION` (corrupt header, reserved flag non-zero, unknown core opcode)
- `1009`: `SESSION_EXPIRED` (pause retention TTL exceeded)
