# LMStream Wire Protocol Specification

> **Specification Version:** `LMStream-1.0-draft`  
> **Status:** Normative Standard  
> **Repository:** [https://github.com/morewebs/lmstream](https://github.com/morewebs/lmstream)

---

## Table of Contents

- [1. Introduction](#1-introduction)
  - [1.1. Motivation](#11-motivation)
  - [1.2. Target Audience](#12-target-audience)
  - [1.3. Non-Goals](#13-non-goals)
  - [1.4. Conformance Language](#14-conformance-language)
- [2. Frame Header & Binary Layout](#2-frame-header--binary-layout)
  - [2.1. Fixed Header Structure](#21-fixed-header-structure)
  - [2.2. Header Fields](#22-header-fields)
  - [2.3. Frame Size & Derivation of 65,527 Bytes](#23-frame-size--derivation-of-65527-bytes)
  - [2.4. Flags and the BOUNDARY Invariant](#24-flags-and-the-boundary-invariant)
- [3. Opcode Registry](#3-opcode-registry)
  - [3.1. Registry Ranges](#31-registry-ranges)
  - [3.2. Core Opcodes Table](#32-core-opcodes-table)
  - [3.3. Unknown Opcode Policy](#33-unknown-opcode-policy)
- [4. Payload Formats](#4-payload-formats)
  - [4.1. Data Payloads (CONTENT, REASONING, TOOL_CALL)](#41-data-payloads)
  - [4.2. Accounting Payloads (USAGE, METRICS, END, ERROR)](#42-accounting-payloads)
  - [4.3. Control Payloads (OPEN, OPEN_ACK, CANCEL, PAUSE, RESUME, STEER, REWIND, SETTINGS, PING, PONG)](#43-control-payloads)
- [5. Sessions & Multiplexing](#5-sessions--multiplexing)
  - [5.1. StreamID Allocation & Invariants](#51-streamid-allocation--invariants)
  - [5.2. Session Lifecycle & Terminal Ordering Sequence](#52-session-lifecycle--terminal-ordering-sequence)
  - [5.3. Interleaving & Head-of-Line Independence](#53-interleaving--head-of-line-independence)
- [6. Error Handling](#6-error-handling)
  - [6.1. Error Catalog (1001–1009)](#61-error-catalog-10011009)
  - [6.2. Error Scopes & Teardown Rules](#62-error-scopes--teardown-rules)
- [7. Flow Control & Steering](#7-flow-control--steering)
  - [7.1. PAUSE and RESUME Semantics](#71-pause-and-resume-semantics)
  - [7.2. Dynamic STEER Delivery](#72-dynamic-steer-delivery)
  - [7.3. Server-Emitted REWIND Semantics](#73-server-emitted-rewind-semantics)
- [8. Protocol Versioning & Negotiation](#8-protocol-versioning--negotiation)
- [9. Security Summary](#9-security-summary)
- [10. Registry Summary](#10-registry-summary)
- [Appendix A. Worked Wire Examples](#appendix-a-worked-wire-examples)
- [Appendix B. Provider Mapping (Informative)](#appendix-b-provider-mapping-informative)

---

## 1. Introduction

LMStream is a binary streaming wire protocol designed specifically for Large Language Model (LLM) inference outputs, multi-turn agent interactions, and AI gateway communication.

### 1.1. Motivation

Server-Sent Events (SSE) and chunked HTTP/1.1 JSON streams have become the de facto transport for LLM outputs. However, SSE suffers from severe structural deficiencies:
1. **Unidirectional Limitations**: SSE is strictly server-to-client. Bidirectional operations — such as client-initiated cancellation, flow pause, and dynamic steering — require separate out-of-band HTTP requests that arrive unsynchronized with the generation token stream.
2. **Head-of-Line Blocking & Absence of Multiplexing**: SSE cannot multiplex concurrent completions or tool executions across a single transport connection, forcing clients to open dozens of redundant TCP/TLS connections.
3. **Bandwidth Inefficiency**: Repeated JSON envelopes (`{"choices":[{"delta":{"content":"..."}}]}`) inflate token payloads by 400–1000%, wasting mobile bandwidth and causing unnecessary JSON parsing churn.
4. **Lack of Standardized Accounting & Telemetry**: Token consumption, cache hit ratios, time-to-first-token (TTFT), generation speed, and failover retries are currently conveyed through vendor-specific headers or custom JSON fragments.

LMStream solves these deficiencies with an 8-byte binary frame header, multiplexed streams, bi-directional control, zero-copy UTF-8 boundaries, and standardized accounting payloads.

### 1.2. Target Audience

This specification is normative for:
- **LLM Gateway & Proxy Authors**: Engineers building high-throughput routing, caching, and rate-limiting infrastructure (e.g., Cloudflare AI Gateway, LiteLLM, vLLM, TensorRT-LLM).
- **Agent Orchestration Frameworks**: Frameworks coordinating multi-step, multi-tool agent loops requiring sub-millisecond cancellation, pause, and steering.
- **Client SDK Maintainers**: Implementers building native clients in TypeScript, Python, Go, Rust, Swift, and other languages.

### 1.3. Non-Goals

LMStream deliberately scopes out the following responsibilities:
- **Not an Authentication/Authorization Framework**: LMStream relies on transport-layer security (TLS, mTLS) and token authentication (e.g., API keys passed in `OPEN` payloads or transport headers).
- **Not a Secret Key Management Service**: Encryption at rest, key rotation, and secret vaults are out of scope.
- **Not a Provider-Specific Inference API**: LMStream specifies the wire framing, stream multiplexing, and common semantic types; it does not dictate prompt schemas, temperature parameters, or model weights.

### 1.4. Conformance Language

The key words **"MUST"**, **"MUST NOT"**, **"REQUIRED"**, **"SHALL"**, **"SHALL NOT"**, **"SHOULD"**, **"SHOULD NOT"**, **"RECOMMENDED"**, **"NOT RECOMMENDED"**, **"MAY"**, and **"OPTIONAL"** in this document are to be interpreted as described in BCP 14 [RFC 2119] [RFC 8174].

---

## 2. Frame Header & Binary Layout

All communication in LMStream consists of discrete binary frames. Every frame begins with a fixed 8-byte header followed by an optional payload.

### 2.1. Fixed Header Structure

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

### 2.2. Header Fields

| Field | Offset (Bytes) | Width (Bytes) | Type | Description |
|---|---|---|---|---|
| `StreamID` | 0 | 4 | `u32 LE` | Stream identifier. `0` = connection control; `> 0` = session. |
| `Opcode` | 4 | 1 | `u8` | Identifies frame type and payload format. |
| `Flags` | 5 | 1 | `u8` | Bitfield modifiers. Bit 0 = `BOUNDARY`. Bits 1–7 reserved. |
| `Length` | 6 | 2 | `u16 LE` | Byte length of the following payload (`0` to `65,527`). |
| `Payload` | 8 | `Length` | `bytes` | Opcode-specific payload data. |

### 2.3. Frame Size & Derivation of 65,527 Bytes

The maximum possible value representable by a 16-bit unsigned integer is $2^{16} - 1 = 65,535$ bytes. To guarantee that an entire frame (header plus payload) fits strictly within a standard single 64 KiB network memory buffer ($65,536$ bytes) without exceeding $65,535$ bytes total:

$$\text{Max Payload Length} = 65,535 - 8 = 65,527 \text{ bytes}$$

Senders **MUST NOT** emit a frame whose `Length` field exceeds `65,527`. Receivers receiving a frame with `Length > 65,527` **MUST** treat this as a protocol violation and emit connection-scoped `ERROR 1008`.

### 2.4. Flags and the BOUNDARY Invariant

The `Flags` byte (offset 5) contains bitfield flags that modify the parsing or rendering of the payload:

```text
Bit:    7   6   5   4   3   2   1   0
      +---+---+---+---+---+---+---+---+
      | R | R | R | R | R | R | C | B |
      +---+---+---+---+---+---+---+---+
        R = Reserved (MUST be 0)
        C = COMPRESSED (Reserved for future compression, 0x02)
        B = BOUNDARY (0x01)
```

- **Bit 0 (`0x01`): `BOUNDARY`**:
  - `BOUNDARY = 1`: The payload ends precisely on a complete, valid UTF-8 Unicode codepoint boundary. The client **MAY** render or consume the accumulated string immediately.
  - `BOUNDARY = 0`: The payload terminates mid-codepoint (i.e. contains a partial UTF-8 sequence). The client **MUST** buffer the trailing incomplete bytes and concatenate them with the subsequent frame's payload before rendering.
  - **Scope of BOUNDARY**: The `BOUNDARY` flag applies **STRICTLY** to `CONTENT` (`0x03`) and `REASONING` (`0x04`) frames. Senders **MUST NOT** set `BOUNDARY` on other opcodes (it MUST be 0). Explicitly, `TOOL_CALL` does not use the `BOUNDARY` header flag; tool calls use internal flags (`START`, `CONT`, `END`).
- **Bit 1 (`0x02`): `COMPRESSED`**: Reserved for future compression negotiation. In `LMStream-1.0`, senders **MUST** set this bit to 0.
- **Bits 2–7 (`0x04`–`0x80`): Reserved**: Senders **MUST** set reserved bits to 0.
- **Enforcement**: Receivers encountering any non-zero reserved flag bit **MUST** emit connection-scoped `ERROR 1008 (Protocol Violation)` and terminate the connection.

---

## 3. Opcode Registry

### 3.1. Registry Ranges

Opcode numbers (0x00–0xFF) are partitioned into three distinct operational ranges:

- **`0x01–0x2F`**: **Core Protocol Range**. Normative opcodes defined in this specification. Unrecognized opcodes in this range indicate wire corruption and **MUST** trigger connection-scoped `ERROR 1008`.
- **`0x30–0xEF`**: **Extension Range**. Reserved for standard extensions and vendor additions registered in `registry.md`. Receivers **MUST** safely ignore and skip unrecognized frames in this range.
- **`0xF0–0xFF`**: **Control & Experimental Range**. Reserved for private experimentation and transport-level framing tests. Ignored unless explicitly negotiated.

### 3.2. Core Opcodes Table

| Opcode (Hex) | Name | Direction | Payload Structure | Terminal Ordering Rules |
|---|---|---|---|---|
| `0x01` | `OPEN` | Client → Server | UTF-8 JSON request | First frame on client stream |
| `0x02` | `OPEN_ACK` | Server → Client | SessionID + Model name | First frame returned by server |
| `0x03` | `CONTENT` | Server → Client | ChoiceIndex + UTF-8 text | Active generation phase |
| `0x04` | `REASONING` | Server → Client | ChoiceIndex + UTF-8 text | Active generation phase |
| `0x05` | `TOOL_CALL` | Server → Client | ChoiceIndex + CallIndex + Flags + Args | Active generation phase |
| `0x06` | `USAGE` | Server → Client | Fixed 20 bytes token usage | Terminal phase (precedes END) |
| `0x07` | `METRICS` | Server → Client | Fixed 20 bytes telemetry | Terminal phase (precedes END) |
| `0x08` | `END` | Server → Client | FinishReason + ChoiceIndex | Terminal frame for session |
| `0x09` | `ERROR` | Bidirectional | Code + UpstreamStatus + Scope + Msg | Closes session or connection |
| `0x0A` | `CANCEL` | Client → Server | Zero length | May be sent during ACTIVE/PAUSED |
| `0x0B` | `PAUSE` | Client → Server | Zero length | Halts server emission |
| `0x0C` | `RESUME` | Client → Server | Zero length | Resumes server emission |
| `0x0D` | `STEER` | Client → Server | Length-prefixed UTF-8 text | Injects steering instruction |
| `0x0E` | `REWIND` | Server → Client | TargetOp + Choice + ByteOffset | Rewinds stream channel buffer |
| `0x0F` | `SETTINGS` | Bidirectional | Fixed 18 bytes configuration | StreamID 0 only (handshake) |
| `0x10` | `PING` | Bidirectional | 8-byte timestamp (u64 LE) | StreamID 0 only (heartbeat) |
| `0x11` | `PONG` | Bidirectional | 8-byte timestamp (u64 LE) | StreamID 0 only (heartbeat response) |

### 3.3. Unknown Opcode Policy

Per Decision D4:
- When a receiver parses an `Opcode` in the core range (`0x01–0x2F`) that it does not recognize, it **MUST** immediately emit a connection-scoped `ERROR 1008 (Protocol Violation)` and close the connection.
- When a receiver parses an `Opcode` in the extension range (`0x30–0xEF`) that it does not recognize, it **MUST** skip past `Length` payload bytes and continue processing subsequent frames.

---

## 4. Payload Formats

All payload integer fields **MUST** be encoded in Little-Endian byte order.

### 4.1. Data Payloads

#### 4.1.1. `CONTENT` (`0x03`) and `REASONING` (`0x04`)

Carries incremental text tokens for generation content or chain-of-thought reasoning.

```text
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  ChoiceIndex  |             UTF-8 Text Delta Data            ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- `ChoiceIndex` (`u8`, offset 0): Completion choice index. In v1, senders **MUST** emit `0x00`. Receivers **MUST** accept any value `0x00–0xFF` (Decision D7).
- `Text Delta Data` (`bytes`, offset 1 to `Length`): Raw UTF-8 bytes of generated text.
- The `BOUNDARY` flag in the frame header indicates whether the text delta ends on a complete codepoint boundary.

#### 4.1.2. `TOOL_CALL` (`0x05`)

Carries tool invocation calls with support for fragmented streaming of tool arguments.

```text
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  ChoiceIndex  |          CallIndex            |   ToolFlags   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|     IdLen     |            NameLen            |  CallId ...   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|      ...      |              ToolName ...                     |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      ArgsDelta (raw JSON)                    ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- `ChoiceIndex` (`u8`, offset 0): In v1, `0x00`.
- `CallIndex` (`u16 LE`, offset 1): Zero-indexed identifier for the tool call within the current choice.
- `ToolFlags` (`u8`, offset 3):
  - Bit 0 (`0x01`): `START`. Indicates initial frame of this tool call. Contains `IdLen`, `NameLen`, `CallId`, and `ToolName`.
  - Bit 1 (`0x02`): `CONT`. Indicates continuation frame containing additional raw arguments.
  - Bit 2 (`0x04`): `END`. Indicates final frame of this tool call.
  - Bits 3–7: Reserved (MUST be 0).
  - Note: A single-frame tool call **MUST** have both `START` and `END` set (`ToolFlags = 0x05`).

When `START` (`0x01`) is set:
- `IdLen` (`u8`, offset 4): Length of tool call ID string in bytes.
- `NameLen` (`u16 LE`, offset 5): Length of tool name string in bytes.
- `CallId` (offset 7): Tool invocation identifier (e.g. `"call_abc123"`).
- `ToolName` (offset `7 + IdLen`): Function or tool name (e.g. `"get_weather"`).
- `ArgsDelta` (offset `7 + IdLen + NameLen` to `Length`): Raw JSON argument delta fragment.

When `START` (`0x01`) is NOT set (`CONT` or `END` alone):
- `ArgsDelta` begins immediately at offset 4 and extends to `Length`.

**Normative Invariant**: Function names **MUST NOT** be fragmented across frames. The complete `ToolName` **MUST** be delivered in the `START` frame. Arguments (`ArgsDelta`) **MUST** be passed through unparsed as raw JSON fragments; clients concatenate fragments across frames and perform a single JSON parse upon receiving `ToolFlags & END`.

---

### 4.2. Accounting Payloads

#### 4.2.1. `USAGE` (`0x06`)

Conveys cumulative token counts for billing and quota management. Fixed 20 bytes.

```text
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         PromptTokens                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       CompletionTokens                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          TotalTokens                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         CachedTokens                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| AttemptCount  |   Reserved1   |           Reserved2           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- `PromptTokens` (`u32 LE`, offset 0): Input tokens consumed.
- `CompletionTokens` (`u32 LE`, offset 4): Generated output tokens.
- `TotalTokens` (`u32 LE`, offset 8): Total tokens billed (`PromptTokens + CompletionTokens`).
- `CachedTokens` (`u32 LE`, offset 12): Prompt tokens read from provider KV cache.
- `AttemptCount` (`u8`, offset 16): Number of upstream provider attempts (1 = direct success; > 1 indicates failover retries occurred).
- `Reserved1` (`u8`, offset 17): MUST be 0.
- `Reserved2` (`u16 LE`, offset 18): MUST be 0.
- **Cumulative Invariant**: When failovers or retries occur (`AttemptCount > 1`), token counts **MUST** reflect the aggregate cumulative usage across all attempts.

#### 4.2.2. `METRICS` (`0x07`)

Conveys runtime performance telemetry and routing audit metadata. Fixed 20 bytes.

```text
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                            TTFTMs                             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                        TotalDurationMs                        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                         TokensPerSec                          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                       ObfuscatedKeyID                         |
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- `TTFTMs` (`u32 LE`, offset 0): Time-to-first-token in milliseconds.
- `TotalDurationMs` (`u32 LE`, offset 4): Total inference wall-clock duration in milliseconds.
- `TokensPerSec` (`u32 LE`, offset 8): Rolling generation speed scaled by 100 (e.g., `8550` represents `85.50` tokens/sec).
- `ObfuscatedKeyID` (`u64 LE`, offset 12): 64-bit truncated SHA-256 hash of the routing key or credential, enabling telemetry aggregation without exposing API credentials.

#### 4.2.3. `END` (`0x08`)

Concludes session generation cleanly.

```text
 0                   1
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| FinishReason  |  ChoiceIndex  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- `FinishReason` (`u8`, offset 0):
  - `0x00`: `STOP` — Natural stop sequence or end-of-text token reached.
  - `0x01`: `LENGTH` — Maximum context length or `max_tokens` limit reached.
  - `0x02`: `TOOL_CALLS` — Model generated tool calls requiring client execution.
  - `0x03`: `CONTENT_FILTER` — Upstream safety filter flagged and halted generation.
  - `0x04`: `CANCELLED` — Session terminated due to client `CANCEL`.
- `ChoiceIndex` (`u8`, offset 1): In v1, `0x00`.

#### 4.2.4. `ERROR` (`0x09`)

Notifies peer of an operational or protocol failure.

```text
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|             Code              |        UpstreamStatus         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  ChoiceIndex  |     Scope     |            MsgLen             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                     Message (UTF-8)                          ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- `Code` (`u16 LE`, offset 0): LMStream error code (1001–1009).
- `UpstreamStatus` (`u16 LE`, offset 2): HTTP status code returned by upstream provider (e.g., 429, 500, 503), or `0` if internal.
- `ChoiceIndex` (`u8`, offset 4): Choice index or `0x00`.
- `Scope` (`u8`, offset 5):
  - `0x00`: `SESSION` scope. The session closes; the underlying connection remains healthy.
  - `0x01`: `CONNECTION` scope. The entire transport connection closes immediately.
- `MsgLen` (`u16 LE`, offset 6): Byte length of human-readable error message.
- `Message` (offset 8 to `8 + MsgLen`): UTF-8 explanatory error string.

---

### 4.3. Control Payloads

#### 4.3.1. `OPEN` (`0x01`)

Client initiates a new session on an odd-numbered StreamID.
- **Payload**: Raw UTF-8 encoded JSON document conforming to provider-agnostic request parameters (`model`, `messages`, `tools`, `metadata`, etc.).

#### 4.3.2. `OPEN_ACK` (`0x02`)

Server confirms session initiation.

```text
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           SessionID                           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           ModelLen            |          Model ...            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- `SessionID` (`u32 LE`, offset 0): Confirms the session StreamID.
- `ModelLen` (`u16 LE`, offset 4): Byte length of model name string.
- `Model` (offset 6 to `6 + ModelLen`): Resolved canonical model identifier string (e.g. `"claude-3-5-sonnet"`).

#### 4.3.3. `CANCEL` (`0x0A`), `PAUSE` (`0x0B`), `RESUME` (`0x0C`)

Client flow control frames.
- **Payload**: MUST be zero-length (`Length = 0`). Senders **MUST NOT** include payload bytes; receivers **MUST** reject non-zero length with `ERROR 1008`.

#### 4.3.4. `STEER` (`0x0D`)

Client injects mid-generation prompt instructions into the active model stream.

```text
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|            TextLen            |          UTF-8 Text          ...
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- `TextLen` (`u16 LE`, offset 0): Length of steering text.
- `UTF-8 Text` (offset 2 to `2 + TextLen`): Plain text steering instruction (Decision D5).

#### 4.3.5. `REWIND` (`0x0E`)

Server signals a rollback of channel output due to speculative decoding rollback or upstream failover.

```text
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| TargetOpcode  |  ChoiceIndex  |           Reserved            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                          ByteOffset                           |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

- `TargetOpcode` (`u8`, offset 0): Channel to rewind (`0x03` CONTENT, `0x04` REASONING, or `0x05` TOOL_CALL).
- `ChoiceIndex` (`u8`, offset 1): In v1, `0x00`.
- `Reserved` (`u16 LE`, offset 2): MUST be 0.
- `ByteOffset` (`u32 LE`, offset 4): Cumulative byte offset to rewind to. Client truncates accumulated channel buffer to this length.
- **Tool-Call Discard Invariant**: If `TargetOpcode = 0x05` and `ByteOffset = 0`, the client **MUST** completely discard all partially received tool call fragments for that choice.

#### 4.3.6. `SETTINGS` (`0x0F`)

Negotiates connection operational parameters. Fixed 18 bytes. MUST be sent on **StreamID 0**.

```text
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|    Version    |                 MaxFrameSize                  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|     ...       |                PauseBufferCap                 |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|     ...       |                  HeartbeatMs                  |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|     ...       |    MaxConcurrentSessions      |   Reserved1   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|   Reserved2   |
+-+-+-+-+-+-+-+-+
```

Byte offsets:
- `Version` (`u8`, offset 0): Protocol version (`0x01` for v1).
- `MaxFrameSize` (`u32 LE`, offset 1): Negotiated frame size cap (default `65,535`).
- `PauseBufferCap` (`u32 LE`, offset 5): Maximum queued bytes per paused session (default `1,048,576` = 1 MiB).
- `HeartbeatMs` (`u32 LE`, offset 9): Heartbeat interval in milliseconds (default `15,000`).
- `MaxConcurrentSessions` (`u16 LE`, offset 13): Maximum active concurrent sessions (default `100`).
- `Reserved1` (`u8`, offset 15): MUST be 0.
- `Reserved2` (`u16 LE`, offset 16): MUST be 0.

#### 4.3.7. `PING` (`0x10`) and `PONG` (`0x11`)

Connection-level keepalive heartbeat. MUST be sent on **StreamID 0**. Fixed 8 bytes.
- `TimestampMs` (`u64 LE`, offset 0): Millisecond Unix epoch timestamp. `PONG` echoes back the identical 8 bytes.

---

## 5. Sessions & Multiplexing

### 5.1. StreamID Allocation & Invariants

- **StreamID 0**: Dedicated strictly to connection-level frames (`SETTINGS`, `PING`, `PONG`, connection `ERROR`). Any data opcode (`CONTENT`, etc.) received on StreamID 0 **MUST** cause connection `ERROR 1008`.
- **Client Sessions**: MUST allocate monotonically increasing odd numbers (`1, 3, 5, 7, ...`).
- **Server-Initiated Sessions**: Reserved for even numbers (`2, 4, 6, ...`). (Deferred in v1).
- StreamIDs **MUST NOT** be reused on the same connection. When a stream exhausts available IDs ($2^{31}-1$), the client **MUST** open a new connection.

### 5.2. Session Lifecycle & Terminal Ordering Sequence

A compliant server **MUST** adhere to the following ordering sequence on any session stream:
1. `OPEN_ACK` (acknowledges receipt of `OPEN`)
2. Generation phase: Arbitrary interleaving of `CONTENT`, `REASONING`, `TOOL_CALL`, `REWIND`.
3. Terminal accounting phase:
   - Zero or one `USAGE` frame.
   - Zero or one `METRICS` frame.
   - Exactly one `END` frame (or session-scoped `ERROR`).

Once `END` or session-scoped `ERROR` is sent or received, the stream transitions to the `TERMINATED` state. No further frames may be emitted on that `StreamID`.

### 5.3. Interleaving & Head-of-Line Independence

Frames from distinct active `StreamID`s **MAY** be freely interleaved over a single connection. A stall or pause on StreamID $A$ **MUST NOT** impede the transmission of frames on StreamID $B$.

---

## 6. Error Handling

### 6.1. Error Catalog (1001–1009)

| Code | Name | Scope Default | Description |
|---|---|---|---|
| `1001` | Bad Request | Session | Malformed `OPEN` payload, invalid JSON schema, or illegal parameters. |
| `1002` | Authentication Failed | Connection | Missing, expired, or rejected credentials. |
| `1003` | Rate Limited | Session | Upstream provider 429; includes Retry-After if available. |
| `1004` | Model Overloaded | Session | Upstream provider 503 or queue saturated. |
| `1005` | Upstream Error | Session | Upstream provider 500/502 unrecoverable failure. |
| `1006` | Buffer Overflow | Session | Paused session buffer exceeded `PauseBufferCap`. |
| `1007` | Invalid State | Session | Frame received in violation of state machine (e.g. `CONTENT` after `END`). |
| `1008` | Protocol Violation | Connection | Corrupt header, reserved flag non-zero, unknown core opcode, length limit exceeded. |
| `1009` | Session Expired | Session | Paused session exceeded server retention TTL (Decision D9). |

### 6.2. Error Scopes & Teardown Rules

- **`Scope = 0x00 (SESSION)`**: Terminates the specific `StreamID`. All queued frames for that session are discarded. All other active sessions and the connection remain intact.
- **`Scope = 0x01 (CONNECTION)`**: Immediately tears down the transport connection. Any pending frames on all streams are aborted.

---

## 7. Flow Control & Steering

### 7.1. PAUSE and RESUME Semantics

- When a client sends `PAUSE` (`0x0B`) on an active stream, the server **MUST** buffer newly generated tokens from upstream.
- Senders **MUST NOT** drop tokens while paused up to `PauseBufferCap` (negotiated in `SETTINGS`).
- If buffered bytes exceed `PauseBufferCap`, the server **MUST** drop the session with `ERROR 1006 (Buffer Overflow)`.
- If a session remains paused longer than server TTL, the server **MUST** emit `ERROR 1009 (Session Expired)`.
- On receiving `RESUME` (`0x0C`), the server drains its buffer in FIFO order with no data loss.

### 7.2. Dynamic STEER Delivery

- A client sends `STEER` (`0x0D`) to inject live instructions (e.g., `"be more concise"`, `"format as python"`) into an ongoing completion.
- The server appends this steering text to the model prompt sampling context. `STEER` does not trigger an implicit rewind; prior emitted tokens remain valid.

### 7.3. Server-Emitted REWIND Semantics

- Sent when an upstream gateway performs speculative token rollback or fails over to a secondary provider.
- Specifies `ByteOffset`. The client **MUST** truncate its channel buffer to `ByteOffset`.
- If `TargetOpcode = 0x05 (TOOL_CALL)` and `ByteOffset = 0`, the client **MUST** discard the current partial tool call.

---

## 8. Protocol Versioning & Negotiation

- Handshake is conducted via `SETTINGS` (`0x0F`) frame with `Version = 0x01`.
- On WebSocket transports, clients negotiate subprotocol `Sec-WebSocket-Protocol: lmstream-v1`. If the server rejects the subprotocol, the connection fails immediately without silent downgrade.

---

## 9. Security Summary

- All LMStream transports **MUST** run over Transport Layer Security (TLS 1.3+ / QUIC).
- Authentication tokens transmitted in `OPEN` frames are protected by the TLS envelope.
- `ObfuscatedKeyID` in `METRICS` prevents leakage of secret credentials in logging infrastructure.
- Fixed maximum frame size ($65,527$ bytes) and strict reserved bit validation protect against buffer overflow and denial-of-service amplification attacks.

---

## 10. Registry Summary

All opcodes, error codes, and flags are formally cataloged in [`registry.md`](registry.md). Requests for new opcodes in the extension range (`0x30–0xEF`) follow the governance process outlined in [`GOVERNANCE.md`](GOVERNANCE.md).

---

## Appendix A. Worked Wire Examples

*(All examples below are byte-verified in Task 6.4 against the reference codec)*

### A.1. Minimal CONTENT Frame

A `CONTENT` frame on StreamID 1 with `BOUNDARY = 1`, `ChoiceIndex = 0`, carrying text `"Hello"` (5 UTF-8 bytes).

Payload: `0x00` (ChoiceIndex) + `0x48 0x65 0x6C 0x6C 0x6F` (`"Hello"`) = 6 bytes payload.  
Header: StreamID = 1 (`0x01 0x00 0x00 0x00`), Opcode = 3 (`0x03`), Flags = 1 (`0x01`), Length = 6 (`0x06 0x00`).

<!-- VERIFIED: minimal-content -->
```text
01 00 00 00 03 01 06 00 00 48 65 6c 6c 6f
```

### A.2. PING Frame

A `PING` frame on StreamID 0 with timestamp `1700000000000` (`0x0000018BDCA4D800` in LE: `00 d8 a4 dc 8b 01 00 00`).

Header: StreamID = 0 (`0x00 0x00 0x00 0x00`), Opcode = 16 (`0x10`), Flags = 0 (`0x00`), Length = 8 (`0x08 0x00`).

<!-- VERIFIED: ping-frame -->
```text
00 00 00 00 10 00 08 00 00 d8 a4 dc 8b 01 00 00
```

### A.3. CANCEL Frame

A zero-length `CANCEL` frame on StreamID 3.

Header: StreamID = 3 (`0x03 0x00 0x00 0x00`), Opcode = 10 (`0x0A`), Flags = 0 (`0x00`), Length = 0 (`0x00 0x00`).

<!-- VERIFIED: cancel-frame -->
```text
03 00 00 00 0a 00 00 00
```

### A.4. END Frame

An `END` frame on StreamID 1 with `FinishReason = STOP (0x00)`, `ChoiceIndex = 0`.

Payload: `0x00 0x00` = 2 bytes.  
Header: StreamID = 1 (`0x01 0x00 0x00 0x00`), Opcode = 8 (`0x08`), Flags = 0 (`0x00`), Length = 2 (`0x02 0x00`).

<!-- VERIFIED: end-frame -->
```text
01 00 00 00 08 00 02 00 00 00
```

---

## Appendix B. Provider Mapping (Informative)

See [`semantics/provider-mapping.md`](semantics/provider-mapping.md) for detailed informative mappings from OpenAI, DeepSeek, and Anthropic streaming APIs into standard LMStream frames.
