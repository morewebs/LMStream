# LMStream Python Reference Implementation

Pure Python (stdlib-only, zero runtime dependencies) reference codec, client algorithms, and test vector runner.

## Usage

### Run Test Vectors

```bash
python run_vectors.py
```

### Run Client Demo Against Mock Server

```bash
# In terminal 1 (starts TS mock server):
npm run mock-server --prefix ../typescript

# In terminal 2:
python demo.py
```

## Structure

- `lmstream/enums.py`: Protocol enums (Opcode, HeaderFlags, ToolFlags, ErrorCode, FinishReason).
- `lmstream/frame.py`: Frame header and wire serialization with strict validation.
- `lmstream/payloads.py`: Payloads for SETTINGS, CONTENT, TOOL_CALL, USAGE, METRICS, END, ERROR, etc.
- `lmstream/algorithms.py`: Normative UTF-8 boundary and tool-call assembly.
- `run_vectors.py`: Validates all manifests in `vectors/`.
