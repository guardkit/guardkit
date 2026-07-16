#!/usr/bin/env node
// dcl_check.mjs — Go-free DCL validity checker harness (WASM playground build).
//
// Vendored from github.com/russelleast/Capability-Language @ 4f9fbe56 (Apache-2.0).
// See PROVENANCE.md for provenance + shas; SHA256SUMS for integrity.
//
// This is guardkit's harness, extended from the fleet-evals spike's dcl-check.mjs
// (spike/dcl-authoring/bin/dcl-check.mjs) with ONE addition: an `--ir` flag that
// includes the compiler's native IR object in the JSON envelope, so the Python
// deriver (checker.py -> deriver.py) can consume intents/actors/shapes/outcomes/
// typed event fields/policies/observations/lifecycle straight from the compiler.
// Envelope fields and exit codes are otherwise identical to the spike harness.
//
// Usage:   node dcl_check.mjs [--ir] <path-to-file.dcl>
// Prints:  a JSON envelope on stdout, shaped to mirror the real `dcl validate --json` CLI:
//            { ok, diagnostics[], diagnosticCount, errorCount, warningCount, infoCount, sourceCount }
//          With --ir the envelope also carries `ir` (the compiler's native IR object).
//          The vendored WASM entrypoint (`dclCompile`) natively returns {ok, diagnostics[], ir?};
//          this harness derives the *Count fields from the diagnostics array so the wire contract
//          matches the CLI's documented envelope (see dcl-factory-evaluation-2026-07.md §2).
// Exit:    0 when ok:true (no error diagnostics), 1 when ok:false, 2 on usage/harness error.
//
// CRITICAL gotcha (from the eval probe, §2): do NOT override globalThis.fs. Overriding it
// deadlocks Go's scheduler on a version.json file-walk. We let wasm_exec.js install its own
// default shim (which returns ENOSYS for the walk), which is exactly what makes this work.

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));

function fail(code, msg) {
  process.stdout.write(JSON.stringify({
    ok: false,
    diagnostics: [{ severity: "error", code: "DCL_HARNESS_ERROR", message: msg }],
    diagnosticCount: 1, errorCount: 1, warningCount: 0, infoCount: 0, sourceCount: 0,
  }, null, 2) + "\n");
  process.exit(code);
}

const args = process.argv.slice(2);
const includeIr = args.includes("--ir");
const target = args.find((a) => !a.startsWith("--"));
if (!target) fail(2, "usage: node dcl_check.mjs [--ir] <path-to-file.dcl>");

let source;
try {
  source = readFileSync(resolve(target), "utf8");
} catch (e) {
  fail(2, `cannot read ${target}: ${e.message}`);
}

// Load the Go WASM runtime shim. It installs globalThis.Go and, importantly, its own
// default globalThis.fs shim. We deliberately do NOT touch globalThis.fs.
await import(resolve(__dirname, "wasm_exec.js"));

if (typeof globalThis.Go !== "function") fail(2, "wasm_exec.js did not install globalThis.Go");

const go = new globalThis.Go();
const wasmBytes = readFileSync(resolve(__dirname, "dcl.wasm"));
const { instance } = await WebAssembly.instantiate(wasmBytes, go.importObject);

// go.run() blocks (the Go main is `select {}`). Fire it and don't await — dclCompile is
// exported synchronously during startup; we poll for it, mirroring the playground loader.
go.run(instance);

async function waitForExport(name, tries = 200, delayMs = 5) {
  for (let i = 0; i < tries; i++) {
    if (typeof globalThis[name] === "function") return globalThis[name];
    await new Promise((r) => setTimeout(r, delayMs));
  }
  return undefined;
}

const dclCompile = await waitForExport("dclCompile");
if (!dclCompile) fail(2, "dclCompile was not exported by dcl.wasm");

let raw;
try {
  raw = dclCompile(source);
} catch (e) {
  fail(2, `dclCompile threw: ${e.message}`);
}

let parsed;
try {
  parsed = JSON.parse(raw);
} catch (e) {
  fail(2, `dclCompile returned non-JSON: ${e.message}`);
}

const diagnostics = Array.isArray(parsed.diagnostics) ? parsed.diagnostics : [];
const errorCount = diagnostics.filter((d) => d.severity === "error").length;
const warningCount = diagnostics.filter((d) => d.severity === "warning").length;
const infoCount = diagnostics.filter((d) => d.severity === "info").length;

const envelope = {
  ok: Boolean(parsed.ok),
  diagnostics,
  diagnosticCount: diagnostics.length,
  errorCount,
  warningCount,
  infoCount,
  sourceCount: 1,
};

// --ir: attach the compiler's native IR object verbatim (may be null/undefined if the
// compile failed hard). The deriver treats a missing ir as a loud, non-derivable state.
if (includeIr) {
  envelope.ir = parsed.ir ?? null;
}

process.stdout.write(JSON.stringify(envelope, null, 2) + "\n");
process.exit(envelope.ok ? 0 : 1);
