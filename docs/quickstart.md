# LMStream Quickstart Guide

Get up and running with the LMStream reference server and clients in under 5 minutes.

---

## 1. Prerequisites

- **Node.js**: `v22.0.0` or later
- **Python**: `3.10` or later
- **Go**: `1.22` or later
- **Rust / Cargo**: Stable

---

## 2. Running Test Vectors

LMStream comes with 145 canonical test vectors (golden, invalid, edge, scenario). Validate them across any language:

### TypeScript
```bash
cd examples/typescript
npm install
npm test
npm run generate-vectors
```

### Python
```bash
python examples/python/run_vectors.py
```

### Go
```bash
cd examples/go
go run run_vectors.go
```

### Rust
```bash
cd examples/rust
cargo run --bin run_vectors
```

---

## 3. Running the Mock Server & Interactive Demos

### Start the Reference Mock Server
The mock server provides both a native WebSocket interface (`:9123`) and a gRPC interface (`:9124`).

```bash
cd examples/typescript
npm run mock-server
```

### Run Client Demos

In another terminal:

#### TypeScript WebSocket Demo
```bash
cd examples/typescript
npm run demo
```

#### TypeScript gRPC Demo
```bash
cd examples/typescript
npm run grpc-demo
```

#### Python WebSocket Demo
```bash
python examples/python/demo.py
```
