# LMStream Frequently Asked Questions (FAQ)

### Why not just use gRPC or WebSockets with Protobuf?
Protobuf requires schema compilation (`.proto`), creates secondary sources of truth, and incurs serialization overhead on tiny streaming deltas. LMStream frames are byte-oriented with an 8-byte header, zero-copy UTF-8 boundaries, and specialized LLM semantics (reasoning, tool streaming, speculative rewinds). When gRPC is used, LMStream frames ride as raw bytes in an envelope, preserving HTTP/2 streams without duplicating the vector surface.

### Why Little-Endian instead of Network Byte Order (Big-Endian)?
Virtually all modern consumer CPUs (x86_64, ARM64/Apple Silicon, RISC-V) and GPU memory architectures are natively Little-Endian. Mandating Little-Endian byte order eliminates byte-swapping overhead on modern servers and client devices.

### How does LMStream handle browser environments?
LMStream is first-class in browsers via WebSocket (`wss://`) and WebTransport. A pure TypeScript zero-dependency client parses binary frames directly from `ArrayBuffer` without polyfills. For legacy environments, an SSE JSON profile is defined in `bindings/sse.md`.

### Can a client pause a stream indefinitely?
No. Servers enforce a negotiated `PauseBufferCap` (default 1 MiB) and an idle retention timeout TTL (default 60 seconds). If either limit is exceeded, the server evicts the session with `ERROR 1006` or `ERROR 1009`, protecting against memory exhaustion attacks while leaving the connection open.
