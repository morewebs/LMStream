# LMStream Rust Reference Implementation

Pure Rust reference codec and test vector validator.

## Run Test Vectors

```bash
cargo run --bin run_vectors
```

## Structure

- `src/lib.rs`: LMStream frame header encoding/decoding, error catalog, fixed-length validation.
- `src/bin/run_vectors.rs`: Manifest test runner verifying all golden, invalid, edge, and scenario test vectors.
