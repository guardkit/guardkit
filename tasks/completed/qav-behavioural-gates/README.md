# QA Verifier Behavioural-Evidence Gates

The three genuinely-NEW QA-Verifier gates (Phase 0, no fine-tune):

| Layer | Gate | Task |
|---|---|---|
| L2 | Anti-stub body scan (tree-sitter dialect DATA) | TASK-QAV-001 (factory) + TASK-QAV-002 (seam) |
| L3 | Runtime coverage — zero-execution authored public surface | TASK-QAV-003 |
| L4 | Behavioural round-trip oracle — the one hard gate | TASK-QAV-004 |
| — | Dogfood validation (fs-01 + correctly-wired stub) | TASK-QAV-005 |

**Out of scope:** L1 wiring probes (built — FEAT-C332), Coach fine-tune
(Phase 1), BDD glue policy. A1–A6 stand.

**Read first:** `docs/retro/qa-verifier-state-consolidation-2026-07-04.md`,
then `IMPLEMENTATION-GUIDE.md` here, then the spec at
`features/qav-behavioural-gates/`.

Waves: 001 → 002 → 003 → 004 → 005, sequential (`--max-parallel 1`).
