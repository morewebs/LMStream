import * as fs from "node:fs";
import * as path from "node:path";
import { fileURLToPath } from "node:url";
import { decodeFrame, encodeFrame } from "../src/index.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, "../../../..");
const specPath = path.join(rootDir, "SPEC.md");

function cleanHex(raw: string): string {
  return raw.replace(/[^0-9a-fA-F]/g, "").toLowerCase();
}

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

function main() {
  console.log("Verifying SPEC.md Appendix A worked examples against codec...");
  let content = fs.readFileSync(specPath, "utf-8");

  const regex = /<!-- (?:TODO-verify|VERIFIED):\s*([a-zA-Z0-9_-]+)\s*-->\s*```(?:text|hex)?\s*([0-9a-fA-F\s]+)```/g;
  let match;
  let verifiedCount = 0;

  while ((match = regex.exec(content)) !== null) {
    const id = match[1];
    const rawHex = cleanHex(match[2]);
    const bytes = hexToBytes(rawHex);

    try {
      const decoded = decodeFrame(bytes);
      const reEncoded = encodeFrame(decoded);
      const reEncodedHex = bytesToHex(reEncoded);

      if (reEncodedHex !== rawHex) {
        throw new Error(`Example ${id} failed roundtrip: expected ${rawHex}, got ${reEncodedHex}`);
      }
      console.log(`✓ Spec example '${id}' verified: Opcode 0x${decoded.header.opcode.toString(16)}, Length ${decoded.header.length}`);
      verifiedCount++;
    } catch (err) {
      console.error(`✗ Spec example '${id}' failed:`, err);
      process.exit(1);
    }
  }

  console.log(`Successfully verified all ${verifiedCount} spec examples!`);
}

main();
