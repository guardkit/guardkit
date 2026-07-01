# Guard asymmetry between paired specialists is a latency-blocker class

> **Source**: Seeded by TASK-PERF-SPECLAT01 (2026-06, commit `dacbed553`
> "fix(SPECLAT01): bound autobuild specialist phase so it can't exhaust the task
> budget") from the FEAT-9DDE run-6 blocker. Promoted from Graphiti to git by
> FEAT-MEM-09 WS-2b. Sibling of
> [`watchdog-activity-signal-must-be-substrate-aware.md`](watchdog-activity-signal-must-be-substrate-aware.md)
> — both bound a specialist that can otherwise run unbounded.

## The rule

When an autobuild specialist's latency threatens to exhaust the per-task budget,
**bound the specialist phase** before reaching for a faster specialist model. Two
bounds are load-bearing and must be applied to **every** orchestrator-invoked
specialist symmetrically:

1. A **per-specialist SDK-timeout cap** (`_cap_specialist_timeout`,
   [`autobuild.py:2765`](../../guardkit/orchestrator/autobuild.py#L2765)), and
2. A **no-activity watchdog** (see the sibling rule).

**Guard asymmetry between paired specialists is a defect class.** If the Phase-4
test-orchestrator has both bounds and the Phase-5 code-reviewer does not, the
code-reviewer can run unbounded and burn the whole task budget purely because it
inherited neither guard. Any *new* orchestrator specialist MUST inherit **both**
bounds, or it is a latency blocker waiting to fire.

A compounding sub-rule: a specialist timeout cap must be computed from
`post_player_remaining` — the budget left **after** the Player phase — not the
stale start-of-turn `remaining_budget`
([`autobuild.py:3308`](../../guardkit/orchestrator/autobuild.py#L3308)). A cap
derived from a stale, larger figure does not actually bound the phase.

## Why this rule exists

**2026-06 — FEAT-9DDE run-6.** A Phase-5 `code-reviewer` invocation ran for
**2138s** (~35 min) and hit an SDK timeout, consuming more than half of the
80-minute task budget and blocking the task. Root cause: the code-reviewer
lacked the per-specialist SDK-timeout cap and the no-activity watchdog that the
Phase-4 `test-orchestrator` already had. It was not a model-speed problem — it
was a *missing-guard* problem, and the missing guard existed for one specialist
but not its pair.

The fix bounds the phase model-agnostically and offline-testably:

- `SPECIALIST_BUDGET_FRACTION`
  ([`autobuild.py:226`](../../guardkit/orchestrator/autobuild.py#L226),
  env `GUARDKIT_SPECIALIST_BUDGET_FRACTION`, default `0.5`) — a ceiling on the
  fraction of `post_player_remaining` the specialist phase may consume.
- `_cap_specialist_timeout`
  ([`autobuild.py:2765`](../../guardkit/orchestrator/autobuild.py#L2765)) — caps
  the per-specialist `sdk_timeout` for **both** the Phase-4 test-orchestrator and
  the Phase-5 code-reviewer through one shared helper
  (escape hatch: `GUARDKIT_SPECIALIST_TIMEOUT_CAP=disable`,
  [`autobuild.py:2801`](../../guardkit/orchestrator/autobuild.py#L2801)).

The rejected alternative was a `--specialist-model` override pointing at a faster
model. That addresses throughput root-cause but (a) adds cross-repo
guardkitfactory harness model-threading surface, (b) depends on a faster model
actually being served on GB10, and (c) therefore **cannot be validated offline** —
so it was deferred in favour of the model-agnostic bounds, which directly satisfy
the ACs and test offline.

## Symptom

- A single autobuild task fails with a specialist SDK timeout after the specialist
  ran for a large fraction of the task budget (minutes, not the expected phase
  duration).
- The over-running specialist is the *pair* of one that has SDK-timeout + watchdog
  guards — i.e. one of `{test-orchestrator, code-reviewer}` ran unbounded while the
  other would have been capped.
- The over-run consumes `> SPECIALIST_BUDGET_FRACTION` of `post_player_remaining`.

## Detection recipe

```bash
# 1. Every orchestrator specialist invocation — confirm each routes its sdk_timeout
#    through _cap_specialist_timeout (not a raw/uncapped timeout).
rg -n "invoke_(test_orchestrator|code_reviewer|.*specialist)" guardkit/orchestrator/autobuild.py
rg -n "_cap_specialist_timeout" guardkit/orchestrator/autobuild.py

# 2. Confirm the cap derives from post_player_remaining, not remaining_budget.
rg -n "post_player_remaining|SPECIALIST_BUDGET_FRACTION" guardkit/orchestrator/autobuild.py

# 3. A new specialist with a raw sdk_timeout= and no _cap_specialist_timeout wrap
#    is the hazard — grep for specialist invokes that bypass the cap.
```

## Remediation

1. **Route every specialist's `sdk_timeout` through `_cap_specialist_timeout`.** A
   new specialist that passes a raw timeout re-introduces the asymmetry.
2. **Give every specialist the no-activity watchdog** (see the sibling rule) — the
   SDK-timeout cap bounds total wall-clock; the watchdog bounds *idle* time.
3. **Compute the cap from `post_player_remaining`**, not the start-of-turn budget.
4. **Prefer bounding over a faster model** when the fix must be offline-testable and
   model-agnostic. A model override is a throughput optimisation, not a bound; ship
   the bound first.

## Grep-able signature (for next agent)

```bash
# Bound-present fingerprints (MUST MATCH):
rg -n "def _cap_specialist_timeout" guardkit/orchestrator/autobuild.py         # -> 2765
rg -n "SPECIALIST_BUDGET_FRACTION" guardkit/orchestrator/autobuild.py          # -> 226
rg -n "post_player_remaining" guardkit/orchestrator/autobuild.py               # -> 3308

# Sibling-rule lookup:
rg "specialist-guard-asymmetry|watchdog-activity-signal-must-be-substrate-aware" .claude/rules/
```

## When this rule triggers

- Before adding a NEW orchestrator-invoked specialist (a new Phase-N agent) — it
  MUST inherit `_cap_specialist_timeout` and the no-activity watchdog.
- Before proposing a faster-model override as the fix for a specialist-latency
  blocker — bound the phase first; the model override is a deferred throughput
  optimisation.
- During Phase 2.5 architectural review for anything touching
  `autobuild.py` specialist invocation, `_cap_specialist_timeout`,
  `SPECIALIST_BUDGET_FRACTION`, or `post_player_remaining`.

## What this rule does NOT cover

- The numeric budget fraction (`GUARDKIT_SPECIALIST_BUDGET_FRACTION`, default 0.5)
  and the cap-disable escape hatch — those are operator policy, not the rule.
- Player-phase budgeting — this rule governs the *specialist* phases downstream of
  the Player.
- The faster-specialist-model path itself — it remains a legitimate future
  throughput optimisation, just not a substitute for the bounds.

## Prior art

- **Sibling bound**:
  [`watchdog-activity-signal-must-be-substrate-aware.md`](watchdog-activity-signal-must-be-substrate-aware.md)
  — the *idle-time* half of specialist bounding (the SDK-timeout cap is the
  *total-wall-clock* half). A specialist needs both.
- **Originating fix**: TASK-PERF-SPECLAT01 (commit `dacbed553`), task at
  `tasks/completed/TASK-PERF-SPECLAT01/`; validated live in the FEAT-9DDE runs-7-9
  retro (commit `188f84974`).
