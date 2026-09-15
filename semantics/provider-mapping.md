# LMStream Provider Mapping (Informative)

> **Status:** Informative Guide  
> **Target Audience:** Gateway Authors, Proxy Implementers, Adapter SDKs

This document provides recommended patterns for converting legacy Server-Sent Events (SSE) and JSON streams from major LLM providers (OpenAI, Anthropic, DeepSeek) into native LMStream binary frames.

---

## 1. Field Mapping Reference

| Provider Field / Event | LMStream Opcode | Target Field / Handling |
|---|---|---|
| OpenAI `choices[0].delta.content` | `CONTENT (0x03)` | UTF-8 text delta, `ChoiceIndex = 0` |
| DeepSeek `choices[0].delta.reasoning_content` | `REASONING (0x04)` | UTF-8 reasoning delta, `ChoiceIndex = 0` |
| Anthropic `content_block_delta` (`type: text_delta`) | `CONTENT (0x03)` | UTF-8 text delta |
| Anthropic `content_block_delta` (`type: thinking_delta`) | `REASONING (0x04)` | Thinking tokens / chain-of-thought text |
| OpenAI `choices[0].delta.tool_calls` | `TOOL_CALL (0x05)` | Fragmented argument streaming |
| Anthropic `input_json_delta` | `TOOL_CALL (0x05)` | `ArgsDelta` string concatenation |
| OpenAI `usage` | `USAGE (0x06)` | `PromptTokens`, `CompletionTokens`, `TotalTokens` |
| Anthropic `message_start` & `message_delta` usage | `USAGE (0x06)` | Combine `input_tokens` and `output_tokens` |
| Finish / Stop reasons | `END (0x08)` | Map string reason to `FinishReason` enum |

---

## 2. OpenAI & DeepSeek Mapping Details

### 2.1. Content & Reasoning Deltas

```text
SSE line: data: {"choices":[{"delta":{"content":"Hello world"},"index":0}]}
--> LMStream: CONTENT (StreamID=1, Flags=0x01, ChoiceIndex=0, Data="Hello world")

SSE line: data: {"choices":[{"delta":{"reasoning_content":"Step 1..."},"index":0}]}
--> LMStream: REASONING (StreamID=1, Flags=0x01, ChoiceIndex=0, Data="Step 1...")
```

### 2.2. Fragmented Function Name Buffering

OpenAI SSE chunks may occasionally fragment `tool_calls[i].function.name` across adjacent deltas (e.g. chunk 1: `{"function":{"name":"get_"}}`, chunk 2: `{"name":"weather"}}`).

**Gateway Invariant**: LMStream `TOOL_CALL` mandates that `ToolName` **MUST NOT** be fragmented on the wire. A gateway converting OpenAI SSE to LMStream **MUST** buffer incoming tool call deltas until the function name is fully received before emitting the `START` frame (`ToolFlags = 0x01`). Subsequent argument deltas are streamed immediately as `CONT` frames.

### 2.3. Injecting `stream_options.include_usage`

OpenAI does not stream usage metadata by default. When an OpenAI-compatible client opens a LMStream session, the gateway adapter **SHOULD** inject `"stream_options": {"include_usage": true}` into the forwarded request payload so that upstream emits the terminal usage chunk required to populate LMStream `USAGE (0x06)`.

---

## 3. Anthropic Messages API Mapping

### 3.1. Split Token Usage

Anthropic delivers token accounting split across two separate events:
1. `message_start`: contains `message.usage.input_tokens` and `cache_read_input_tokens`.
2. `message_delta`: contains `usage.output_tokens`.

The LMStream gateway adapter **MUST** store `PromptTokens` and `CachedTokens` from `message_start`, hold them until `message_delta` arrives, and then emit the single unified 20-byte `USAGE (0x06)` frame prior to `END (0x08)`.

### 3.2. `input_json_delta` to `TOOL_CALL`

Anthropic streams tool calls as `content_block_start` (providing tool `id` and `name`) followed by one or more `content_block_delta` events of type `input_json_delta`:

- `content_block_start` $\rightarrow$ Emit LMStream `TOOL_CALL` with `ToolFlags = START (0x01)`.
- `content_block_delta (partial_json)` $\rightarrow$ Emit LMStream `TOOL_CALL` with `ToolFlags = CONT (0x02)`.
- `content_block_stop` $\rightarrow$ Emit LMStream `TOOL_CALL` with `ToolFlags = END (0x04)`.

---

## 4. Finish Reason Mapping

| Provider Finish Reason | LMStream `FinishReason` | Enum Value |
|---|---|---|
| `"stop"`, `"end_turn"` | `STOP` | `0x00` |
| `"length"`, `"max_tokens"` | `LENGTH` | `0x01` |
| `"tool_calls"` | `TOOL_CALLS` | `0x02` |
| `"content_filter"`, `"safety"` | `CONTENT_FILTER` | `0x03` |
| Client abort / canceled | `CANCELLED` | `0x04` |
