# PROVENANCE — vendored DCL validity checker (S1, DCL SPIKE)

Spike-class artifact. NOT a frozen suite. No thresholds implied. Vendored 2026-07-13.

## What this is

A Go-free, offline DCL validity checker invocable from a script, staged for the DCL SPIKE
(V-02). The checker is the DCL compiler itself, shipped as a WebAssembly playground build and
driven by a ~90-line Node harness (`dcl-check.mjs`). It is deterministic, offline, contains no
LLM, and emits machine-checkable JSON with typed exit codes.

## Upstream source

- **Repo:** github.com/russelleast/Capability-Language
- **Pinned commit:** `4f9fbe56414eecbd100c337da770e1e24c2fcc85` (HEAD as of 2026-07-13; last
  upstream commit 2026-07-10)
- **License:** Apache License 2.0 (see vendored `LICENSE`, 11357 bytes). `NOTICE` names Russell
  East as creator; contributors retain copyright; project history/authorship preserved here per
  the NOTICE's ask. This vendoring is a derivative use permitted under Apache-2.0.

## Path chosen: WASM playground build (PRIMARY — proven on this box)

The upstream compiler is Go (`go 1.22`). This box (a GB10 Spark, **aarch64/ARM64**) has
`node` v24.15.0 but **no Go toolchain**, and venue law forbids system installs — so the CLI
`dcl` could not be built from source. The repo ships a prebuilt **`dcl.wasm` + `wasm_exec.js`**
(the website playground compiler); that path is architecture-independent and runs under Node.

Vendored files (copied verbatim from the pinned clone; shas in `SHA256SUMS`):

| file | source path in repo | sha256 |
|---|---|---|
| `dcl.wasm` | `website/public/compiler/dcl.wasm` | `1e6c81886a74ea59b49301df09a2f332bb8fdd2f8870b7d3017c1a1d9d042ff7` |
| `wasm_exec.js` | `website/public/compiler/wasm_exec.js` | `0c949f4996f9a89698e4b5c586de32249c3b69b7baadb64d220073cc04acba14` |
| `LICENSE` | `LICENSE` | `58d1e17ffe5109a7ae296caafcadfdbe6a7d176f0bc4ab01e12a689b0499d8bd` |
| `NOTICE` | `NOTICE` | `fd376ed05a81140af69962e3f9ead575dac63b04af6e79674e7aa5662d9cc06f` |

`dcl-check.mjs` (the harness) is authored here, not vendored.

### The WASM entry contract (and how the harness enriches it)

The WASM build exports one global function `dclCompile(source: string) -> string`, where the
string is JSON `{ ok, diagnostics[], ir? }` (source: `compiler/cmd/dclwasm/main.go` in the
pinned repo). The harness derives `diagnosticCount / errorCount / warningCount / infoCount /
sourceCount` from the diagnostics array so the printed envelope mirrors the real
`dcl validate --json` CLI contract documented in the eval doc §2, and exits 0 on `ok:true` /
1 on `ok:false` / 2 on harness/usage error.

### CRITICAL gotcha (recorded so a re-driver reproduces it)

Do **not** override `globalThis.fs`. Overriding it deadlocks Go's scheduler on a `version.json`
file-walk during WASM startup. Letting `wasm_exec.js` install its own default `fs` shim (which
returns `ENOSYS` for the walk) is exactly what makes this run. The harness therefore imports
`wasm_exec.js` and touches nothing on `globalThis` except reading `Go` / `dclCompile`.

### Known limits of the WASM path (honest)

Single-file only; does not embed `version.json`; not the multi-file `validate <dir>` / `summary`
CLI surface. It proves the compiler runs here and its output is clean machine-checkable JSON — a
production oracle would use the real `dcl` CLI (Go build) or the `dcl-mcp` binary. Sufficient for
this spike (one capability, one file).

## Path attempted: prebuilt dcl-mcp binary (SECONDARY — UNAVAILABLE on this arch)

Best-effort, timeboxed. Downloaded `dcl-mcp-linux-amd64.tar.gz` from release tag **`mcp-v0.1.0`**
("DCL MCP Server v0.1.0", 2026-06-30). Recorded for the record, kept in scratch (NOT vendored):

- tarball sha256: `1271def7b43e81f5dc71697c6cadf28192bf9339cc354dce36eaf311a6cffffe`
- extracted `dcl-mcp` binary sha256: `92ad4a4f641e442b015a9e982c4ef8710360be6aefa85b7aebb8b1fa4ba84427`
- `file`: ELF 64-bit LSB executable, x86-64, statically linked (Go)

**It cannot execute on this host.** The box is **aarch64/ARM64**; the release ships only
`darwin-amd64`, `darwin-arm64`, `linux-amd64`, `windows-amd64` — there is **no `linux-arm64`
build**. Attempting to run the amd64 ELF yields the kernel-refusal/shell-fallback error
`Syntax error: Unterminated quoted string`. So the prebuilt-binary path is a dead end on this
ARM64 fleet host; this reinforces the arch-independent WASM path as the correct primary. (On an
amd64 host, or once upstream ships a linux-arm64 mcp build, this binary is the available
alternative.)

## Reproduce

```sh
node dcl-check.mjs <path-to-file.dcl>   # prints JSON envelope; exit 0 ok / 1 errors / 2 usage
sha256sum -c SHA256SUMS                  # integrity of vendored blobs
```

See `PROOF.md` for the two verbatim proof runs (valid README example → ok:true; broken file →
ok:false with coded errors).
