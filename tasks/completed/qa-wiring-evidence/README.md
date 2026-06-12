# FEAT-QAWE — Stack-agnostic wiring evidence (QA-Verifier piece #2)

**Design:** `docs/features/qa-verifier-wiring-probes-scope.md`
**Rule:** `.claude/rules/stack-plugin-architecture.md`

One tree-sitter `WiringAnalyzer` + declarative dialects (py/js/ts/csharp) producing
UNWIRED_PATH / MOCKED_SEAM / SPEC_GAP evidence into the Coach bundle. Stack-agnostic by
default; plugins only for BDD *execution* (consumed, not duplicated).

## Tasks

| Wave | Task | Complexity | Depends on |
|---|---|---:|---|
| 1 | QAWE-001 — tree-sitter analyzer core + dialects | 6 | — |
| 2 | QAWE-002 — UNWIRED_PATH bundle integration | 5 | QAWE-001 |
| 3 | QAWE-003 — MOCKED_SEAM evidence (∥ Wave 2) | 4 | QAWE-001 |
| 4 | QAWE-004 — SPEC_GAP + hard-guard | 5 | QAWE-002 + **FEAT-E2CB (BDDWIRE) merged** |

## Sequencing

**FEAT-E2CB (BDDWIRE) lands first** — Wave 4 (SPEC_GAP) consumes its multi-stack
`BDDRunResult`. Waves 1–3 are independent of BDDWIRE and can build first.

## Run

```bash
guardkit autobuild feature FEAT-QAWE --verbose      # after BDDWIRE for Wave 4
```
