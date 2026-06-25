# SUPERSEDED — duplicate TASK-ABFIX-010 filing

> Historical note (not a task — intentionally carries no `id:`/`status:`
> frontmatter so it is not scanned as a second TASK-ABFIX-010 and does not
> collide with the canonical task file in this folder).

## What this was

A second TASK-ABFIX-010 was filed independently as a flat file
`tasks/backlog/TASK-ABFIX-010-coach-per-test-timeout-false-green.md`
(commit `deb81ca7`, 2026-06-24, "test timeout task") — the original guardkit
task the forge handoff pointed at
(`forge/docs/handoffs/FMDR-NATS-SESSION-DISCOVERIES-2026-06-24.md` line 111:
"guardkit TASK-ABFIX-010 — harness-side false-green fixes").

It collided on `id: TASK-ABFIX-010` with the canonical, implemented task in this
folder ([`TASK-ABFIX-010.md`](TASK-ABFIX-010.md)). It was retired on 2026-06-25
(reviewed and found fully superseded; re-implementing it would have re-introduced
known regressions — see below).

**Original provenance preserved:** `feature_id: FEAT-CD4C`, `sub_feature: ABFIX`,
`wave: 1`, `dependencies: [TASK-ABFIX-005]`, complexity 5, est 3h.

## Why it was superseded (its scope is 100% covered)

| Its acceptance criterion | Resolved by |
|---|---|
| AC3 — pollution guard doesn't count infra timeouts (`tests_run=0`) → no false `unrecoverable_stall` | **DONE** — TASK-ABFIX-010 W1+W2 (commit `069086a0`); reproducer T1a |
| AC5 — genuine false-green still overridden to NOT passed | **DONE** — landed; T1b + T3 (backstop not disarmed) |
| AC4 — regression test (the *no-stall* half) | **DONE** — T1a |
| AC1 — inject per-test `--timeout` so a hung test → named FAILED | **TASK-ABFIX-011** (W3, backlog) |
| AC2 — distinguish infra-timeout from hung-test (per-test attribution) | **TASK-ABFIX-011** (W3, backlog) |
| AC4 — regression test (the *named-node* half) | **TASK-ABFIX-011** (W3, backlog) |
| "Related finding" — required test gate for `task_type: testing` + deterministic substrate-vs-code | **TASK-ABFIX-012** (W4, backlog) |

## Why re-implementing it as-worded would have regressed (the checks we ran)

1. **Harness-wide `--timeout` regression.** Its AC1 injects
   `--timeout=<N> --timeout-method=thread`. It acknowledged graceful degradation,
   but was less safe than TASK-ABFIX-011 in three load-bearing ways the ABFIX-010
   design review made explicit: no **stack-agnostic gate** (pytest-only → breaks /
   silently no-ops on TS/.NET/Go, violating `stack-plugin-architecture`); did not
   enumerate the **four injection sites** (esp. the ABFIX-005 isolated/parallel
   path); no **returncode-4 → `signal_absent`** classifier. These are exactly why
   W3 was split out and gated.
2. **Collision with landed work.** Its AC3 + the "narrative false-green override"
   it described touching are already fixed (absent → `None`, carried through the
   gate chain). Re-implementing would churn or undo the keep-`None` fix.

The complexity-5/3h estimate itself under-scoped what the design review found to be
a gate-chain + false-green-guard + deliberate-prior-decision (COACHRUNPARITY01 L3)
tangle.

## Canonical records

- Implemented: [`TASK-ABFIX-010.md`](TASK-ABFIX-010.md) (this folder) — W1+W2+L2 landed.
- Follow-ons: `tasks/backlog/TASK-ABFIX-011/` (W3), `tasks/backlog/TASK-ABFIX-012/` (W4).
- Rule seeded: `.claude/rules/absence-must-survive-every-reconciliation-layer.md`.
