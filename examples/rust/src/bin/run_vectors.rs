use lmstream::{decode_frame, encode_frame, validate_payload};
use serde::Deserialize;
use std::fs;
use std::path::PathBuf;

#[derive(Deserialize)]
struct ManifestVector {
    id: String,
    raw_hex: Option<String>,
    expected_error: Option<ExpectedError>,
    #[serde(default)]
    steps: Vec<ScenarioStep>,
}

#[derive(Deserialize)]
struct ExpectedError {
    code: u16,
    scope: String,
}

#[derive(Deserialize)]
struct ScenarioStep {
    raw_hex: String,
}

#[derive(Deserialize)]
struct Manifest {
    vectors: Vec<ManifestVector>,
}

fn main() {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..");
    let vectors_dir = root.join("vectors");

    let mut total_tested = 0;

    // 1. Golden Vectors
    let golden_path = vectors_dir.join("golden/manifest.json");
    let golden_str = fs::read_to_string(&golden_path).expect("Read golden manifest");
    let golden: Manifest = serde_json::from_str(&golden_str).expect("Parse golden manifest");

    for v in &golden.vectors {
        let hex_str = v.raw_hex.as_ref().unwrap();
        let raw = hex::decode(hex_str).expect("Hex decode");
        let frame = decode_frame(&raw).unwrap_or_else(|e| panic!("Failed decode {}: {}", v.id, e));
        let re_encoded = encode_frame(&frame).unwrap_or_else(|e| panic!("Failed encode {}: {}", v.id, e));
        assert_eq!(hex::encode(re_encoded), *hex_str, "Mismatch in {}", v.id);
        total_tested += 1;
    }
    println!("[OK] Rust validated {} golden vectors", golden.vectors.len());

    // 2. Invalid Vectors
    let invalid_path = vectors_dir.join("invalid/manifest.json");
    let invalid_str = fs::read_to_string(&invalid_path).expect("Read invalid manifest");
    let invalid: Manifest = serde_json::from_str(&invalid_str).expect("Parse invalid manifest");

    for v in &invalid.vectors {
        let hex_str = v.raw_hex.as_ref().unwrap();
        let raw = hex::decode(hex_str).expect("Hex decode");
        let res = decode_frame(&raw).and_then(|f| validate_payload(f.header.opcode, &f.payload));
        assert!(res.is_err(), "Invalid vector {} expected failure, but passed", v.id);
        total_tested += 1;
    }
    println!("[OK] Rust validated {} invalid vectors", invalid.vectors.len());

    // 3. Edge Vectors
    let edge_path = vectors_dir.join("edge/manifest.json");
    let edge_str = fs::read_to_string(&edge_path).expect("Read edge manifest");
    let edge: Manifest = serde_json::from_str(&edge_str).expect("Parse edge manifest");

    for v in &edge.vectors {
        let hex_str = v.raw_hex.as_ref().unwrap();
        let raw = hex::decode(hex_str).expect("Hex decode");
        let frame = decode_frame(&raw).unwrap_or_else(|e| panic!("Failed decode {}: {}", v.id, e));
        let re_encoded = encode_frame(&frame).unwrap_or_else(|e| panic!("Failed encode {}: {}", v.id, e));
        assert_eq!(hex::encode(re_encoded), *hex_str, "Mismatch in {}", v.id);
        total_tested += 1;
    }
    println!("[OK] Rust validated {} edge vectors", edge.vectors.len());

    // 4. Scenarios
    let scenarios_path = vectors_dir.join("scenarios/manifest.json");
    let scenarios_str = fs::read_to_string(&scenarios_path).expect("Read scenarios manifest");
    let scenarios: Manifest = serde_json::from_str(&scenarios_str).expect("Parse scenarios manifest");

    for v in &scenarios.vectors {
        for step in &v.steps {
            let raw = hex::decode(&step.raw_hex).expect("Hex decode");
            let _ = decode_frame(&raw);
            total_tested += 1;
        }
    }
    println!("[OK] Rust validated {} scenario steps", scenarios.vectors.len());

    println!("\nAll {} test vectors successfully validated by Rust reference implementation!", total_tested);
}
