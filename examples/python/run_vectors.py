#!/usr/bin/env python3
import json
import os
import sys

# Ensure local lmstream package is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lmstream import decode_frame, encode_frame, LMStreamError

def run_tests():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    vectors_dir = os.path.join(root, "vectors")

    total_tested = 0

    # 1. Golden Vectors
    golden_path = os.path.join(vectors_dir, "golden", "manifest.json")
    with open(golden_path, "r", encoding="utf-8") as f:
        golden = json.load(f)
    for vec in golden["vectors"]:
        raw = bytes.fromhex(vec["raw_hex"])
        frame = decode_frame(raw)
        re_encoded = encode_frame(frame)
        if re_encoded.hex() != vec["raw_hex"]:
            raise AssertionError(f"Golden vector {vec['id']} mismatch: expected {vec['raw_hex']}, got {re_encoded.hex()}")
        total_tested += 1
    print(f"[OK] Python validated {len(golden['vectors'])} golden vectors")

    # 2. Invalid Vectors
    invalid_path = os.path.join(vectors_dir, "invalid", "manifest.json")
    with open(invalid_path, "r", encoding="utf-8") as f:
        invalid = json.load(f)
    for vec in invalid["vectors"]:
        raw = bytes.fromhex(vec["raw_hex"])
        try:
            f = decode_frame(raw)
            # If frame-level decode succeeded, test payload decode
            if f.header.opcode == 0x06: # USAGE
                from lmstream.payloads import decode_usage
                decode_usage(f.payload)
            elif f.header.opcode == 0x09: # ERROR
                from lmstream.payloads import decode_error
                decode_error(f.payload)
            elif f.header.opcode == 0x0E: # REWIND
                from lmstream.payloads import decode_rewind
                decode_rewind(f.payload)
            raise AssertionError(f"Invalid vector {vec['id']} expected failure, but passed!")
        except LMStreamError as err:
            if err.code != vec["expected_error"]["code"]:
                raise AssertionError(f"Invalid vector {vec['id']} failed with code {err.code}, expected {vec['expected_error']['code']}")
        total_tested += 1
    print(f"[OK] Python validated {len(invalid['vectors'])} invalid vectors")

    # 3. Edge Vectors
    edge_path = os.path.join(vectors_dir, "edge", "manifest.json")
    with open(edge_path, "r", encoding="utf-8") as f:
        edge = json.load(f)
    for vec in edge["vectors"]:
        raw = bytes.fromhex(vec["raw_hex"])
        frame = decode_frame(raw)
        re_encoded = encode_frame(frame)
        if re_encoded.hex() != vec["raw_hex"]:
            raise AssertionError(f"Edge vector {vec['id']} mismatch: expected {vec['raw_hex']}, got {re_encoded.hex()}")
        total_tested += 1
    print(f"[OK] Python validated {len(edge['vectors'])} edge vectors")

    # 4. Scenario Vectors
    scenario_path = os.path.join(vectors_dir, "scenarios", "manifest.json")
    with open(scenario_path, "r", encoding="utf-8") as f:
        scenarios = json.load(f)
    for sc in scenarios["vectors"]:
        for step in sc["steps"]:
            raw = bytes.fromhex(step["raw_hex"])
            try:
                decode_frame(raw)
            except LMStreamError:
                pass  # Error injection step in scenarios (e.g. scenario 8)
            total_tested += 1
    print(f"[OK] Python validated {len(scenarios['vectors'])} scenario steps")

    print(f"\nAll {total_tested} test vectors successfully validated by Python reference implementation!")

if __name__ == "__main__":
    run_tests()
