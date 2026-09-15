# LMStream Governance & Specification Lifecycle (GOVERNANCE.md)

This document establishes the official governance process, release lifecycle, errata management, and registry change control for the LMStream open standard.

---

## 1. Specification Lifecycle

The LMStream standard follows a four-stage maturation lifecycle modeled on IETF and W3C processes:

```text
+----------------+      +----------------+      +----------------+      +----------------+
| Working Draft  | ---> | Candidate Rec  | ---> |  Standard v1.0 | ---> | Errata/Maint   |
| (Draft-01..N)  |      | (Feature Freeze)|     | (Ratified v1.0)|      | (v1.1 / Minor) |
+----------------+      +----------------+      +----------------+      +----------------+
```

1. **Working Draft (`LMStream-1.0-draft`)**: Active authoring and exploratory proposals. All breaking changes must be documented in `DECISIONS.md`.
2. **Candidate Recommendation (Feature Freeze)**: Test vectors frozen; reference implementations in TypeScript, Python, Go, and Rust validate against conformance test suite.
3. **Ratified Standard (`LMStream-1.0`)**: Formally tagged and immutable. No breaking changes permitted.
4. **Maintenance & Errata (`LMStream-1.x`)**: Clarifications, non-breaking extension opcode additions, and typo corrections.

---

## 2. Errata Policy

- **Editorial Errata**: Typographical errors, non-normative code corrections, or formatting updates that do not alter protocol wire bytes may be applied via pull request with approval from two maintainers.
- **Technical Errata**: Ambiguities or conflicting MUST/SHOULD requirements identified post-ratification require an Errata Advisory recorded in `DECISIONS.md` before publishing an update.

---

## 3. Registry Change Control

- **Core Opcodes (`0x01–0x2F`) & Core Errors (`1001–1999`)**: Reserved strictly for the core specification. Adding or modifying entries requires a major or minor specification release.
- **Extension Opcodes (`0x30–0xEF`) & Errors (`2000–2999`)**: May be allocated to standard extensions. Requests must submit:
  1. Detailed payload specification and endianness definition.
  2. Concrete motivation and provider context.
  3. Golden and invalid test vectors verifying codec serialization.

---

## 4. Deprecation Policy

- Features marked deprecated in `LMStream-1.x` **MUST** continue to be supported for at least one minor release cycle prior to removal in a major version (`LMStream-2.0`).
- Deprecated opcodes remain permanently reserved in `registry.md` and **MUST NOT** be reallocated to different semantics.

---

## 5. Contribution Process

All contributions are governed by the following rules:
1. **Spec Before Code**: Code exists only to validate normative documents. Pull requests proposing code changes that contradict the specification will be rejected.
2. **Deterministic Test Vectors**: Any normative wire change must include matching test vector additions in `vectors/`.
3. **Dual Licensing**: Contributors agree to license specifications under **CC-BY-4.0** and implementation code under the **MIT License**.
