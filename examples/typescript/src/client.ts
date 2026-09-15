import {
  Opcode,
  HeaderFlags,
  ToolFlags,
  FinishReason,
  ErrorCode,
  decodeFrame,
  encodeFrame,
  decodeSettings,
  decodeOpenAck,
  decodeContent,
  decodeToolCall,
  decodeUsage,
  decodeMetrics,
  decodeEnd,
  decodeError,
  decodeRewind,
  encodePingPong,
  Frame,
  SettingsPayload,
  UsagePayload,
  MetricsPayload,
  EndPayload,
  ErrorPayload,
  ToolCallPayload,
} from "./codec/index.js";

export class Utf8BoundaryAssembler {
  private pendingBytes = new Uint8Array(0);

  public process(flags: number, payloadData: Uint8Array): string {
    let buf: Uint8Array;
    if (this.pendingBytes.length > 0) {
      buf = new Uint8Array(this.pendingBytes.length + payloadData.length);
      buf.set(this.pendingBytes, 0);
      buf.set(payloadData, this.pendingBytes.length);
      this.pendingBytes = new Uint8Array(0);
    } else {
      buf = payloadData;
    }

    if ((flags & HeaderFlags.BOUNDARY) !== 0) {
      return new TextDecoder().decode(buf);
    }

    // BOUNDARY = 0: find incomplete UTF-8 tail
    let validLen = buf.length;
    let i = buf.length - 1;
    let trailingCount = 0;

    while (i >= 0 && trailingCount < 3) {
      const b = buf[i];
      if ((b & 0x80) === 0) {
        break;
      } else if ((b & 0xc0) === 0x80) {
        trailingCount++;
        i--;
      } else if ((b & 0xe0) === 0xc0) {
        if (trailingCount < 1) validLen = i;
        break;
      } else if ((b & 0xf0) === 0xe0) {
        if (trailingCount < 2) validLen = i;
        break;
      } else if ((b & 0xf8) === 0xf0) {
        if (trailingCount < 3) validLen = i;
        break;
      } else {
        break;
      }
    }

    if (validLen < buf.length) {
      this.pendingBytes = buf.slice(validLen);
      buf = buf.subarray(0, validLen);
    }

    return new TextDecoder().decode(buf);
  }
}

export interface CompletedToolCall {
  choiceIndex: number;
  callIndex: number;
  id: string;
  name: string;
  arguments: any;
}

export class ToolCallAssembler {
  private active = new Map<
    string,
    { choiceIndex: number; callIndex: number; id: string; name: string; argsChunks: string[] }
  >();

  public process(p: ToolCallPayload): CompletedToolCall | null {
    const key = `${p.choiceIndex}:${p.callIndex}`;
    const isStart = (p.flags & ToolFlags.START) !== 0;
    const isEnd = (p.flags & ToolFlags.END) !== 0;

    if (isStart) {
      this.active.set(key, {
        choiceIndex: p.choiceIndex,
        callIndex: p.callIndex,
        id: p.id ?? "",
        name: p.name ?? "",
        argsChunks: p.argsDelta ? [p.argsDelta] : [],
      });
    } else {
      const existing = this.active.get(key);
      if (!existing) {
        throw new Error(`Non-START frame for unknown tool call ${key}`);
      }
      if (p.argsDelta) {
        existing.argsChunks.push(p.argsDelta);
      }
    }

    if (isEnd) {
      const entry = this.active.get(key)!;
      this.active.delete(key);
      const fullArgsStr = entry.argsChunks.join("");
      const parsedArgs = fullArgsStr ? JSON.parse(fullArgsStr) : {};
      return {
        choiceIndex: entry.choiceIndex,
        callIndex: entry.callIndex,
        id: entry.id,
        name: entry.name,
        arguments: parsedArgs,
      };
    }

    return null;
  }

  public discardForChoice(choiceIndex: number) {
    for (const [key, val] of this.active.entries()) {
      if (val.choiceIndex === choiceIndex) {
        this.active.delete(key);
      }
    }
  }
}

export class LMStreamSession {
  public readonly streamId: number;
  public contentAssembler = new Utf8BoundaryAssembler();
  public reasoningAssembler = new Utf8BoundaryAssembler();
  public toolAssembler = new ToolCallAssembler();
  public contentAccumulator = "";
  public reasoningAccumulator = "";
  public completedTools: CompletedToolCall[] = [];
  public usage?: UsagePayload;
  public metrics?: MetricsPayload;
  public end?: EndPayload;
  public error?: ErrorPayload;

  constructor(streamId: number) {
    this.streamId = streamId;
  }

  public handleFrame(frame: Frame) {
    switch (frame.header.opcode) {
      case Opcode.CONTENT: {
        const payloadData = frame.payload.subarray(1); // skip ChoiceIndex
        const text = this.contentAssembler.process(frame.header.flags, payloadData);
        this.contentAccumulator += text;
        break;
      }
      case Opcode.REASONING: {
        const payloadData = frame.payload.subarray(1); // skip ChoiceIndex
        const text = this.reasoningAssembler.process(frame.header.flags, payloadData);
        this.reasoningAccumulator += text;
        break;
      }
      case Opcode.TOOL_CALL: {
        const p = decodeToolCall(frame.payload);
        const completed = this.toolAssembler.process(p);
        if (completed) {
          this.completedTools.push(completed);
        }
        break;
      }
      case Opcode.USAGE:
        this.usage = decodeUsage(frame.payload);
        break;
      case Opcode.METRICS:
        this.metrics = decodeMetrics(frame.payload);
        break;
      case Opcode.END:
        this.end = decodeEnd(frame.payload);
        break;
      case Opcode.ERROR:
        this.error = decodeError(frame.payload);
        break;
      case Opcode.REWIND: {
        const rw = decodeRewind(frame.payload);
        if (rw.targetOpcode === Opcode.CONTENT) {
          this.contentAccumulator = this.contentAccumulator.slice(0, rw.byteOffset);
        } else if (rw.targetOpcode === Opcode.TOOL_CALL && rw.byteOffset === 0) {
          this.toolAssembler.discardForChoice(rw.choiceIndex);
        }
        break;
      }
    }
  }
}
