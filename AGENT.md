# AGENT Context: LMStream Open Standard

LMStream is an open standard binary streaming wire protocol designed specifically for LLM responses, providing bidirectional control, multiplexing, unified semantics, and cross-language conformance. Deliverables encompass the normative core specification, transport bindings, semantic models, test vectors, a conformance protocol, and reference implementations across TypeScript, Python, Go, and Rust. This is a STANDARDS project: the documents are the product; all code exists only to validate them.

---

## Document Hierarchy

1. **`SPEC.md`** is the ultimate, normative source of truth.
2. **`DECISIONS.md`** records all architectural and design choices (D1–D15+).
3. **`bindings/`** (`websocket.md`, `webtransport-quic.md`, `sse.md`, `grpc.md`, `lmstream.proto`) and **`semantics/`** provide normative bindings, state machines, and algorithmic rules.
4. **`vectors/`** derive strictly from `SPEC.md`.
5. **`examples/`** derive strictly from `SPEC.md` and `vectors/`.
6. Code NEVER defines the spec. If code reveals an ambiguity or bug in the spec, record a decision in `DECISIONS.md` and pause for human review.

---

## Ground Rules

1. **One task per agent session**: Execute tasks methodically per `PLAN.md`.
2. **Documents are the source of truth**: Never modify the specification simply to make code pass. If a task exposes a spec bug, record it as a numbered decision in `DECISIONS.md`.
3. **Human review gates are non-negotiable**:
   - All decisions in `DECISIONS.md`.
   - Every normative spec section (Phases 1–3).
   - Registry ranges.
   - Vector manifests.
   Agents draft; humans own every MUST/SHOULD.
4. **Never hand-edit generated files**: Never manually edit `.bin` vector files or files marked with generated headers. CI regenerates and diffs them.
5. **Clean working tree**: Keep all progress tracked and verified against test suites and schemas.

---

## Current Status

- **Phase**: Phase 9 Complete — Standard Ratified (`LMStream-1.0-rc1`)
- **Status**: All specifications, transport bindings, semantics, test vectors, conformance protocols, and reference implementations in TypeScript, Python, Go, and Rust are fully implemented, validated, and verified.
- **Next Steps**: Tag v1.0, solicit external implementer review, cut final release.
