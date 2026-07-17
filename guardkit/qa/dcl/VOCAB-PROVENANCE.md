# PROVENANCE — vendored DCL v1.0 compiler-verified vocabulary reference

Vendored 2026-07-17 for the W1-S1 DCL machine-authoring lane (`guardkit dcl author`).

## What this is

`vocab-reference.md` is the compiler-verified **closed vocabulary** for DCL v1.0 — the
standing reference the §10 authoring protocol appends to every authoring prompt so the seat
generates only literals the compiler accepts. It contains only compiler-verified facts.

## Source (sha-pinned, byte-identical copy)

- **Source file:** `fleet-evals/harness/dcl/vocab-reference.md` (the §10 protocol's working home).
- **sha256:** `25121afe7415b15cba161fa2f3e728dad7095675f214a298317b51bb0e8fee2b`
  (asserted byte-identical here by `VOCAB-SHA256SUMS` and by
  `tests/qa/dcl/test_author.py::test_vocab_reference_sha256_pinned`).
- **Upstream pin:** `github.com/russelleast/Capability-Language@4f9fbe56414eecbd100c337da770e1e24c2fcc85`
  (v1.0.6, Apache-2.0). Same pin as the vendored WASM checker in `bin/` (see `bin/PROVENANCE.md`).

## Verification receipt

Every literal in the reference was verified against the running compiler: **227 accept/reject
probes** (161 accept + 66 reject) through the vendored WASM checker, 2026-07-17, all consistent
with the extracted closed sets — including the skeleton, which compiles verbatim with zero
diagnostics. Receipt: `fleet-evals/harness/dcl/vocab-probes-receipt.md`.

## Re-freeze discipline

The reference travels by sha-pinned byte-identical copy. Any upstream change reopens the §10
protocol doc (`fleet-evals/docs/research/ideas/dcl-heldout-suite-scope.md` §10, re-frozen
`8a3b9d1`) BEFORE the copy is refreshed — never a piecemeal edit. If this file changes, update
`VOCAB-SHA256SUMS` and the pinned sha in `guardkit/qa/dcl/author.py` (`VOCAB_REF_SHA256`) and
the test in the same diff.
