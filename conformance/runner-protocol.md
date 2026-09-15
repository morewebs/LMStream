# LMStream Conformance Runner Protocol

> **Status:** Normative Standard  
> **Source of Truth:** Governs official conformance verification and third-party library certification.

This document specifies the official test runner protocol, conformance levels, report formats, and certification criteria for LMStream implementations.

---

## 1. Conformance Levels

Implementations certify conformance across three hierarchical levels:

### Level 1 (L1) — Wire Codec Conformance
- **Target**: Standalone codecs and deserializers.
- **Requirements**:
  - Decode and cleanly re-encode all golden vectors in `vectors/golden/`.
  - Reject all invalid vectors in `vectors/invalid/` with matching error codes.
  - Correctly parse all boundary conditions in `vectors/edge/`.
- **Verdict**: Mandatory for all LMStream libraries.

### Level 2 (L2) — Transport Binding Conformance
- **Target**: Transport clients and server adapters.
- **Requirements**:
  - **L2-WS**: Connect over WebSocket, negotiate `lmstream-v1`, exchange `SETTINGS`, and reproduce the golden interop transcript (`scenario-1`) without frame corruption.
  - **L2-gRPC**: Connect over HTTP/2, exchange `SETTINGS` on `Control` RPC, stream sessions over `Session` RPC without HOL blocking.
- **Verdict**: Mandatory for network clients and gateway proxies.

### Level 3 (L3) — Full End-to-End Interop
- **Target**: Multi-turn agent runtimes and production gateways.
- **Requirements**:
  - Successfully complete multi-stream concurrent generation, live `PAUSE`/`RESUME` flow control, dynamic `STEER`, and speculative `REWIND`.

---

## 2. Conformance Report Schema (JSON)

Conformance runners output test results in a machine-readable JSON format conforming to the following structure:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "implementation": {
    "name": "lmstream-python",
    "version": "1.0.0",
    "language": "python",
    "runtime": "CPython 3.12.10"
  },
  "level": "L1",
  "summary": {
    "total": 145,
    "passed": 145,
    "failed": 0,
    "skipped": 0,
    "duration_ms": 120
  },
  "results": [
    {
      "id": "golden-content-single-char",
      "status": "PASS",
      "duration_ms": 0.4
    }
  ]
}
```

---

## 3. Exit Code Contract

All automated conformance runners **MUST** exit with deterministic status codes:
- **`0`**: **SUCCESS**. All vectors and scenarios passed.
- **`1`**: **FAILURE**. One or more conformance tests failed.
- **`2`**: **CONFIGURATION_ERROR**. Manifest files missing or invalid CLI parameters.

---

## 4. Self-Certification Process

Third-party implementations wishing to advertise LMStream conformance **MUST**:
1. Run their test runner against the canonical vector manifests in `vectors/`.
2. Generate a valid L1 (and optionally L2) JSON report.
3. Submit the report or run as part of the official LMStream CI matrix.
