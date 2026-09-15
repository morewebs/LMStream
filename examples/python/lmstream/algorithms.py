import json
from typing import Dict, List, Optional
from .enums import HeaderFlags, ToolFlags, Opcode
from .payloads import ToolCallPayload, decode_tool_call

class Utf8BoundaryAssembler:
    def __init__(self):
        self.pending_bytes = bytearray()

    def process_frame(self, flags: int, payload_data: bytes) -> str:
        if len(self.pending_bytes) > 0:
            buffer = self.pending_bytes + bytearray(payload_data)
            self.pending_bytes.clear()
        else:
            buffer = bytearray(payload_data)

        if (flags & HeaderFlags.BOUNDARY) != 0:
            return buffer.decode("utf-8")

        valid_len = len(buffer)
        i = len(buffer) - 1
        trailing_count = 0

        while i >= 0 and trailing_count < 3:
            byte = buffer[i]
            if (byte & 0x80) == 0:
                break
            elif (byte & 0xC0) == 0x80:
                trailing_count += 1
                i -= 1
            elif (byte & 0xE0) == 0xC0:
                if trailing_count < 1:
                    valid_len = i
                break
            elif (byte & 0xF0) == 0xE0:
                if trailing_count < 2:
                    valid_len = i
                break
            elif (byte & 0xF8) == 0xF0:
                if trailing_count < 3:
                    valid_len = i
                break
            else:
                break

        if valid_len < len(buffer):
            self.pending_bytes = buffer[valid_len:]
            buffer = buffer[:valid_len]

        return buffer.decode("utf-8")

class ToolCall:
    def __init__(self, choice_index: int, call_index: int, call_id: str, name: str):
        self.choice_index = choice_index
        self.call_index = call_index
        self.call_id = call_id
        self.name = name
        self.args_buffer: List[str] = []
        self.completed = False
        self.arguments: dict = {}

class ToolCallAssembler:
    def __init__(self):
        self.active_calls: Dict[tuple, ToolCall] = {}

    def process_payload(self, p: ToolCallPayload) -> Optional[ToolCall]:
        is_start = bool(p.flags & ToolFlags.START)
        is_end = bool(p.flags & ToolFlags.END)
        key = (p.choice_index, p.call_index)

        if is_start:
            call = ToolCall(p.choice_index, p.call_index, p.id or "", p.name or "")
            if p.args_delta:
                call.args_buffer.append(p.args_delta)
            self.active_calls[key] = call
        else:
            if key not in self.active_calls:
                raise ValueError(f"Non-START frame for unknown tool call {key}")
            call = self.active_calls[key]
            if p.args_delta:
                call.args_buffer.append(p.args_delta)

        if is_end:
            full_str = "".join(call.args_buffer)
            call.arguments = json.loads(full_str) if full_str else {}
            call.completed = True
            del self.active_calls[key]
            return call

        return None

    def discard_for_choice(self, choice_index: int):
        keys = [k for k in self.active_calls.keys() if k[0] == choice_index]
        for k in keys:
            del self.active_calls[k]
