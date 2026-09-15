import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { decodeFrame, encodeFrame, LMStreamError } from "../src/index.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// In dist/scripts/generate-vectors.js: __dirname = <root>/examples/typescript/dist/scripts
// Go up 3 levels from src/scripts or 4 levels from dist/scripts:
const rootDir = path.resolve(__dirname, "../../../..");
const vectorsDir = path.join(rootDir, "vectors");

function hexToBytes(hex: string): Uint8Array {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.substring(i, i + 2), 16);
  }
  return bytes;
}

function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

async function processCategory(category: string, isInvalid = false) {
  const manifestPath = path.join(vectorsDir, category, "manifest.json");
  if (!fs.existsSync(manifestPath)) {
    console.warn(`Manifest not found: ${manifestPath}`);
    return;
  }
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
  let passed = 0;

  for (const vec of manifest.vectors) {
    if (category === "scenarios") {
      // Scenarios contain multiple steps
      for (let i = 0; i < vec.steps.length; i++) {
        const step = vec.steps[i];
        const raw = hexToBytes(step.raw_hex);
        const binFile = path.join(vectorsDir, category, `${vec.id}-step-${i + 1}.bin`);
        fs.writeFileSync(binFile, raw);
      }
      passed++;
      continue;
    }

    const raw = hexToBytes(vec.raw_hex);
    const binFile = path.join(vectorsDir, category, `${vec.id}.bin`);
    fs.writeFileSync(binFile, raw);

    if (isInvalid) {
      // Invalid vectors MUST fail to decode
      try {
        decodeFrame(raw);
        throw new Error(`Vector ${vec.id} expected failure with code ${vec.expected_error.code}, but decoded successfully`);
      } catch (err: any) {
        if (err instanceof LMStreamError) {
          if (err.code !== vec.expected_error.code) {
            throw new Error(`Vector ${vec.id} failed with code ${err.code}, expected ${vec.expected_error.code}`);
          }
        }
      }
    } else {
      // Golden / Edge vectors MUST round-trip perfectly: decode(raw) -> encode() === raw
      const decoded = decodeFrame(raw);
      const reEncoded = encodeFrame(decoded);
      const reEncodedHex = bytesToHex(reEncoded);
      if (reEncodedHex !== vec.raw_hex) {
        throw new Error(`Vector ${vec.id} round-trip mismatch:\nExpected: ${vec.raw_hex}\nGot:      ${reEncodedHex}`);
      }
    }
    passed++;
  }
  console.log(`Validated and generated .bin files for ${passed} vectors in '${category}'`);
}

async function main() {
  console.log("Generating LMStream canonical binary vectors...");
  await processCategory("golden", false);
  await processCategory("invalid", true);
  await processCategory("edge", false);
  await processCategory("scenarios", false);
  console.log("Vector generation and round-trip verification complete!");
}

main().catch((err) => {
  console.error("Vector generation failed:", err);
  process.exit(1);
});
