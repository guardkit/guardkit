---
id: TASK-AB-HERMETICTEST01
title: Hermetic-environment test guidance — env-reading config tests must monkeypatch the full env surface
status: backlog
created: 2026-07-05T08:35:00Z
priority: low
tags: [autobuild, player-prompt, testing, env-isolation]
complexity: 3
source: docs/retro/abl001-run3-honest-fail-and-credential-leak-2026-07-04.md
---

# Task: Tests that read ambient env are flaky AND a leak channel — make hermeticity explicit guidance

> Filed 2026-07-05 from ABL-001 run-3 lesson 4. Prompt/doc-level guidance
> (the INVARIANTTEST01 shape); no verdict-logic change.

## Description

ABL-001 run 3, turn 1: the Player's test asserted a monkeypatched
`postgres_dsn`, but the config loader read the ambient `FLEET_MEMORY_PG_DSN`
from the loop's environment. Two failures in one: (a) the test was
non-hermetic — its outcome depended on the host environment (it failed on the
GB10 loop and would pass on a clean CI box); (b) the failing diff printed the
ambient value — which was a **live credential** (see the sibling
TASK-AB-SECRETSCRUB01 for the leak-channel half).

Retro lesson 4: "Env isolation belongs in the task spec… make env-reading
config tests hermetic (`monkeypatch.delenv`/`setenv` around the full
`FLEET_MEMORY_*` surface)."

## Acceptance Criteria

- [ ] AC-001: Player-prompt guidance (following the
      player-prompt-reinforce-coach-constraint-in-three-locations pattern used
      by TASK-AB-INVARIANTTEST01, and landing adjacent to its text): tests
      exercising env-read configuration MUST pin the FULL relevant env-var
      surface with `monkeypatch.setenv`/`delenv` — a test whose outcome can
      change with the host environment is not a test of the code.
- [ ] AC-002: Coach-side advisory (prompt guard, `should_fix`, never
      turn-rejecting alone): flag a NEW test that asserts config values whose
      loader reads env vars the test does not pin.
- [ ] AC-003: `/feature-plan` spec guidance: tasks whose deliverable reads
      configuration from env must name the env surface in the task spec so the
      Player knows what to pin (mirrors the negative-boundary guidance added
      by INVARIANTTEST01).
- [ ] AC-004: Operational note in the instrumentation guide: never run agent
      loops with live credentials in the ambient environment — fixture DSNs
      only (the P4 contract; live creds had no business in the ABL loop env).
- [ ] AC-005: Tests pinning the prompt text in all locations (the
      transient-assertion test file is the template).

## Regression constraints

- `.claude/rules/player-prompt-reinforce-coach-constraint-in-three-locations.md`
  — all three Player-prompt locations, detection phrase shared verbatim with
  the Coach guard.
- `.claude/rules/structural-defence-beats-prompt-instruction.md` — this is
  prompt-only by necessity (LLM-chosen test style); the structural halves are
  TASK-AB-SECRETSCRUB01 (leak channel) and the existing basetemp/venv
  isolation work. Pair the prompt with the monitor: SECRETSCRUB01's lint.
- Advisory only — must not join any turn-rejecting set
  (per-task-green-is-not-feature-green discipline for syntactic heuristics).
