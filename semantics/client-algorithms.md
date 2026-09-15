# LMStream Client Algorithms

> **Status:** Normative Standard  
> **Source of Truth:** Complements `SPEC.md` §2, §4, and §7.

This document specifies normative algorithms that **MUST** be implemented with identical behavior across all LMStream client libraries (TypeScript, Python, Go, Rust).

---

## 1. UTF-8 Boundary Assembly Algorithm

In streaming network systems, multi-byte UTF-8 sequences (2 to 4 bytes per character) can be split across frame boundaries. LMStream uses the header `BOUNDARY` flag (Bit 0 of `Flags`) to eliminate redundant UTF-8 scanning on frames that end on valid codepoints, while specifying deterministic assembly when `BOUNDARY = 0`.

### 1.1. Invariants

- If `Flags & 0x01 == 1` (`BOUNDARY = 1`): The entire payload ends cleanly on a valid UTF-8 boundary. The client decodes and renders immediately.
- If `Flags & 0x01 == 0` (`BOUNDARY = 0`): The payload ends mid-sequence. The client separates the trailing partial UTF-8 sequence, buffers it, and prepends it to the subsequent frame on that channel.

### 1.2. Normative Pseudocode

```python
class Utf8BoundaryAssembler:
    def __init__(self):
        self.pending_bytes = bytearray()

    def process_frame(self, flags: int, payload_data: bytes) -> str:
        """
        Processes a raw text delta payload (excluding the ChoiceIndex byte).
        Returns the decoded string safe for immediate rendering.
        """
        # If we had incomplete bytes from a prior BOUNDARY=0 frame, prepend them
        if len(self.pending_bytes) > 0:
            buffer = self.pending_bytes + bytearray(payload_data)
            self.pending_bytes.clear()
        else:
            buffer = bytearray(payload_data)

        # Fast path: sender declared complete boundary and no pending bytes were split
        if (flags & 0x01) == 1:
            # Entire buffer is valid UTF-8
            return buffer.decode("utf-8")

        # BOUNDARY == 0: Inspect the end of buffer to find incomplete trailing bytes
        # A UTF-8 sequence can have up to 3 trailing bytes from a 4-byte character
        valid_len = len(buffer)
        i = len(buffer) - 1
        trailing_count = 0

        # Scan backwards up to 3 bytes looking for a leading byte (0b11xxxxxx)
        while i >= 0 and trailing_count < 3:
            byte = buffer[i]
            if (byte & 0x80) == 0:
                # ASCII byte (0xxxxxxx) - valid single byte boundary
                break
            elif (byte & 0xC0) == 0x80:
                # Continuation byte (10xxxxxx)
                trailing_count += 1
                i -= 1
            elif (byte & 0xE0) == 0xC0:
                # 2-byte leader: requires 1 continuation byte
                needed = 1
                if trailing_count < needed:
                    valid_len = i
                break
            elif (byte & 0xF0) == 0xE0:
                # 3-byte leader: requires 2 continuation bytes
                needed = 2
                if trailing_count < needed:
                    valid_len = i
                break
            elif (byte & 0xF8) == 0xF0:
                # 4-byte leader: requires 3 continuation bytes
                needed = 3
                if trailing_count < needed:
                    valid_len = i
                break
            else:
                break

        # Save incomplete trailing bytes for next frame
        if valid_len < len(buffer):
            self.pending_bytes = buffer[valid_len:]
            buffer = buffer[:valid_len]

        return buffer.decode("utf-8")
```

---

## 2. Tool Call Reassembly Algorithm

Tool call arguments arrive fragmented across multiple `TOOL_CALL` (`0x05`) frames. Clients **MUST NOT** parse JSON incrementally; arguments **MUST** be concatenated as raw strings and parsed exactly once when the `END` flag arrives.

### 2.1. Invariants

1. A tool invocation starts with `ToolFlags & 0x01` (`START`). It defines `CallId` and `ToolName`.
2. Senders **MUST NOT** fragment `ToolName`. `ToolName` is always complete on the `START` frame.
3. Continuation frames (`ToolFlags & 0x02`, `CONT`) carry raw string slices of `ArgsDelta`.
4. Final frames (`ToolFlags & 0x04`, `END`) carry the final string slice of `ArgsDelta`. Upon receiving `END`, the client parses `AccumulatedArgs` using standard JSON parser.
5. If a single frame has both `START` and `END` (`0x05`), it contains the complete tool call.

### 2.2. Normative Pseudocode

```python
import json
from typing import Dict, Optional

class ToolCall:
    def __init__(self, choice_index: int, call_index: int, call_id: str, name: str):
        self.choice_index = choice_index
        self.call_index = call_index
        self.call_id = call_id
        self.name = name
        self.args_buffer = []  # List of raw string deltas
        self.completed = False
        self.parsed_arguments = None

class ToolCallAssembler:
    def __init__(self):
        # Key: (choice_index, call_index) -> ToolCall
        self.active_calls: Dict[tuple, ToolCall] = {}

    def process_tool_frame(self, payload: bytes) -> Optional[ToolCall]:
        """
        Decodes a TOOL_CALL (0x05) payload.
        Returns the completed ToolCall if END flag was received, else None.
        """
        choice_index = payload[0]
        call_index = int.from_bytes(payload[1:3], byteorder="little")
        flags = payload[3]

        is_start = bool(flags & 0x01)
        is_cont  = bool(flags & 0x02)
        is_end   = bool(flags & 0x04)

        key = (choice_index, call_index)

        if is_start:
            id_len = payload[4]
            name_len = int.from_bytes(payload[5:7], byteorder="little")
            
            call_id = payload[7 : 7 + id_len].decode("utf-8")
            name = payload[7 + id_len : 7 + id_len + name_len].decode("utf-8")
            args_slice = payload[7 + id_len + name_len :].decode("utf-8")

            call = ToolCall(choice_index, call_index, call_id, name)
            if args_slice:
                call.args_buffer.append(args_slice)
            self.active_calls[key] = call
        else:
            if key not in self.active_calls:
                raise ValueError(f"Received non-START frame for unknown tool call {key}")
            call = self.active_calls[key]
            args_slice = payload[4:].decode("utf-8")
            if args_slice:
                call.args_buffer.append(args_slice)

        if is_end:
            full_args_str = "".join(call.args_buffer)
            # Parse raw JSON string exactly once at END
            call.parsed_arguments = json.loads(full_args_str) if full_args_str else {}
            call.completed = True
            del self.active_calls[key]
            return call

        return None
```

---

## 3. Channel Rewind Handling Algorithm

When the server emits a `REWIND` (`0x0E`) frame, the client rolls back accumulated state.

### 3.1. Invariants

- For `CONTENT` (`0x03`) and `REASONING` (`0x04`), the client maintains a raw byte buffer or character offset. On receiving `REWIND(TargetOpcode, ByteOffset)`, the buffer **MUST** be truncated to `ByteOffset`.
- For `TOOL_CALL` (`0x05`):
  - If `ByteOffset == 0`: All partially received tool calls for that choice **MUST** be discarded from active reassembly state.
  - If `ByteOffset > 0`: Senders **MUST NOT** emit non-zero `ByteOffset` for `TOOL_CALL` in v1 (receivers treat this as `ERROR 1008`).

### 3.2. Normative Pseudocode

```python
class SessionChannelState:
    def __init__(self):
        self.content_bytes = bytearray()
        self.reasoning_bytes = bytearray()
        self.tool_assembler = ToolCallAssembler()

    def handle_rewind(self, target_opcode: int, choice_index: int, byte_offset: int):
        if target_opcode == 0x03:  # CONTENT
            if byte_offset > len(self.content_bytes):
                raise ValueError("Cannot rewind beyond current buffer length")
            self.content_bytes = self.content_bytes[:byte_offset]

        elif target_opcode == 0x04:  # REASONING
            if byte_offset > len(self.reasoning_bytes):
                raise ValueError("Cannot rewind beyond current buffer length")
            self.reasoning_bytes = self.reasoning_bytes[:byte_offset]

        elif target_opcode == 0x05:  # TOOL_CALL
            if byte_offset == 0:
                # Invariant: Discard all partial tool calls for choice
                keys_to_delete = [
                    k for k in self.tool_assembler.active_calls.keys()
                    if k[0] == choice_index
                ]
                for k in keys_to_delete:
                    del self.tool_assembler.active_calls[k]
            else:
                raise ValueError("Non-zero rewind byte offset is unsupported for tool calls in v1")
```
