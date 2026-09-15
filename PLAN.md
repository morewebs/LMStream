# LMStream Build Plan

This document tracks the execution of all phases for the LMStream open standard.

---

## Ground Rules

1. **One task per agent session.** Never "do Phase 3." The agent reads `AGENT.md` + `PLAN.md`, executes one task, checks it off, stops for human review.
2. **Documents are the source of truth.** Vectors derive from `SPEC.md`; examples derive from `SPEC.md` + vectors. Never let the agent "fix" the spec to make code pass — if a task exposes a spec bug, file a new decision in `DECISIONS.md` and stop.
3. **Human review gates are non-negotiable** at: all decisions (Phase 0), every normative spec section (Phases 1–3), registry ranges, and the vector manifests. Agents draft; humans own every MUST.
4. **Never hand-edit generated files** (`.bin` vectors, anything with a "generated" header). CI regenerates and diffs them.
5. **One commit per task**, message = task ID.

---

## Phase 0 — Foundations

- [x] **Task 0.1 — Repository scaffold**
- [x] **Task 0.2 — `DECISIONS.md`: resolve D1–D15**
- [x] **Task 0.3 — `CONVENTIONS.md` + `AGENT.md`**

---

## Phase 1 — Core specification (`SPEC.md`)

- [x] **Task 1.1 — Skeleton + §1 Introduction**
- [x] **Task 1.2 — §2 Framing**
- [x] **Task 1.3 — §3 Opcode registry**
- [x] **Task 1.4 — §4.1 Data payloads**
- [x] **Task 1.5 — §4.2 Accounting payloads**
- [x] **Task 1.6 — §4.3 Control payloads + §5–§8**
- [x] **Task 1.7 — Appendix A placeholder**

---

## Phase 2 — Semantics

- [x] **Task 2.1 — `semantics/state-machines.md`**
- [x] **Task 2.2 — `semantics/flow-control.md`**
- [x] **Task 2.3 — `semantics/client-algorithms.md`**
- [x] **Task 2.4 — `semantics/provider-mapping.md`** *(informative)*

---

## Phase 3 — Transport bindings

- [x] **Task 3.1 — `bindings/websocket.md`**
- [x] **Task 3.2 — `bindings/webtransport-quic.md`**
- [x] **Task 3.3 — `bindings/sse.md`**
- [x] **Task 3.4 — `bindings/grpc.md` + `bindings/lmstream.proto`**

---

## Phase 4 — Registries, security, governance

- [x] **Task 4.1 — `registry.md`**
- [x] **Task 4.2 — `SECURITY.md`**
- [x] **Task 4.3 — `GOVERNANCE.md`**

---

## Phase 5 — Test vectors (authored from the frozen spec, no code yet)

- [x] **Task 5.1 — `vectors/schema/manifest-schema.json`**
- [x] **Task 5.2 — Golden vectors (target ≥ 60)**
- [x] **Task 5.3 — Invalid vectors (≥ 15)**
- [x] **Task 5.4 — Edge vectors (≥ 20)**
- [x] **Task 5.5 — Scenario vectors (≥ 8)**
- [x] **Task 5.6 — `TRACEABILITY.md`**

---

## Phase 6 — Reference implementation (TypeScript) + generation

- [x] **Task 6.1 — `examples/typescript` scaffold**
- [x] **Task 6.2 — Codec**
- [x] **Task 6.3 — `scripts/generate-vectors.ts`**
- [x] **Task 6.4 — Spec-example verification**

---

## Phase 7 — Mock server + language examples

- [x] **Task 7.1 — Mock reference server** (WS + gRPC scripted transcripts)
- [x] **Task 7.2 — TypeScript reference client** (WS demo + gRPC demo asserting golden transcript)
- [x] **Task 7.3 — Python reference client & validator**
- [x] **Task 7.4 — Go reference client & validator**
- [x] **Task 7.5 — Rust reference client & validator**

---

## Phase 8 — Conformance + CI

- [x] **Task 8.1 — `conformance/runner-protocol.md`** (L1 codec, L2 WS + gRPC)
- [x] **Task 8.2 — `.github/workflows/ci.yml`** (proto lint + TS gRPC interop job)

---

## Phase 9 — Documentation + publication

- [x] **Task 9.1 — `docs/`**
- [x] **Task 9.2 — `README.md` final**
- [x] **Task 9.3 — Review round + v1.0**

---

## Milestones & Effort

| Milestone | Ends at | State |
|---|---|---|
| M0 | Phase 0 | D1–D15 signed, scaffold committed | Complete |
| M1 | Phase 3 | Spec + semantics + bindings frozen at draft | Complete |
| M2 | Phase 6 | Vectors frozen, reference impl green, spec examples verified | Complete |
| M3 | Phase 8 | Four languages green in CI, conformance protocol published | Complete |
| M4 | Phase 9 | External review done, `LMStream-1.0` tagged | Complete |
