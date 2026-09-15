# LMStream Security Model & Threat Considerations (SECURITY.md)

> **Status:** Normative Guidelines & Threat Model  
> **Source of Truth:** Complements `SPEC.md` §9.

---

## 1. Threat Model & Mitigations

### 1.1. Resource Exhaustion via PAUSE Buffering

- **Threat**: An adversarial or stalled client opens numerous sessions, issues `PAUSE`, and forces the server to buffer high-throughput token streams from upstream LLMs indefinitely until server memory is exhausted.
- **Mitigations**:
  1. **Negotiated Cap (`PauseBufferCap`)**: Handshake establishes a strict buffer limit (default 1 MiB per session). Exceeding this cap triggers immediate eviction with session-scoped `ERROR 1006 (Buffer Overflow)`.
  2. **Pause Retention Timer (TTL)**: Servers enforce an idle retention timer (default 60 seconds). Sessions remaining paused without `RESUME` or `CANCEL` are evicted with `ERROR 1009 (Session Expired)`.
  3. **Concurrency Caps**: `MaxConcurrentSessions` in `SETTINGS` limits the aggregate number of simultaneous active or paused sessions permitted per connection.

### 1.2. Unbounded Session Creation & StreamID Flooding

- **Threat**: A client floods the server with `OPEN` frames to exhaust file descriptors or server session tracking state.
- **Mitigations**:
  - Servers enforce `MaxConcurrentSessions` (default 100). Any `OPEN` exceeding this concurrent limit **MUST** be rejected with `ERROR 1001` or `ERROR 1007`.
  - StreamIDs are monotonically increasing and cannot be recycled within a connection, preventing race conditions or stream confusion attacks.

### 1.3. Malformed Frame & Frame Injection Attacks

- **Threat**: Attackers send malformed length fields, invalid bit combinations, or unknown core opcodes to cause buffer overruns or deserializer panic.
- **Mitigations**:
  - **Strict Length Cap**: Payload lengths exceeding $65,527$ bytes are invalid by definition and **MUST** trigger connection-scoped `ERROR 1008`.
  - **Reserved Bit Verification**: Any non-zero bit in reserved positions of the header flags or tool flags **MUST** trigger connection-scoped `ERROR 1008`.
  - **Core Opcode Strictness**: Unrecognized opcodes in the core range (`0x01–0x2F`) **MUST** immediately terminate the connection with `ERROR 1008`.

---

## 2. Cryptographic Security & Transport Requirements

### 2.1. Mandatory TLS Encryption

All production LMStream deployments **MUST** run over Transport Layer Security (TLS 1.3 or later / QUIC):
- **WebSockets**: `wss://` strictly required.
- **WebTransport**: Enforces native QUIC TLS 1.3 encryption by specification.
- **gRPC**: TLS with ALPN (`h2`) strictly required on public networks. Cleartext `h2c` is permissible **ONLY** within trusted, private container networks or loopback interfaces.

### 2.2. Credentials in OPEN Payloads

Because `OPEN` payloads carry model request parameters (and optionally user tokens or API keys), carrying LMStream frames over unencrypted transports creates catastrophic credential theft risks. Clients **MUST NOT** transmit sensitive credentials over unencrypted connections.

### 2.3. ObfuscatedKeyID Telemetry Protection

The `METRICS (0x07)` frame conveys an `ObfuscatedKeyID` (64-bit unsigned integer).
- **Design Rationale**: In multi-tenant gateways and routing meshes, telemetry data is exported to third-party APM systems (Datadog, Prometheus, Grafana). Transmitting raw API keys or provider secrets in telemetry would leak credentials into logs.
- **Implementation**: Senders compute `ObfuscatedKeyID` as the first 8 bytes of `SHA-256(SecretKey | Salt)` encoded as a little-endian `u64`. This enables precise usage attribution and auditing without exposing the underlying secret.

---

## 3. Protocol Downgrade Resistance

Adversarial middleboxes may attempt to strip protocol headers or force downgrades:
- On WebSocket connections, clients **MUST** negotiate `Sec-WebSocket-Protocol: lmstream-v1`. If the server fails to accept `lmstream-v1`, the client **MUST** abort the connection immediately.
- Downgrades to legacy unauthenticated plain text streams are strictly forbidden.

---

## 4. Reporting Vulnerabilities

To report a vulnerability in the LMStream specification or reference implementations, please submit a confidential report to `security@lmstream.org` (or open a GitHub Security Advisory).
