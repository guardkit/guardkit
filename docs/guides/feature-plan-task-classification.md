# `/feature-plan` task classification

Reference for the three classes of defect that `/feature-plan` is
hardened against, the strong/weak signal taxonomy used by the
Class C detector, and the `operator_handoff` escape hatch that
runs through `/feature-complete`.

This guide is the operator-facing companion to the implementation
work in [`tasks/backlog/feature-plan-defects/`](../../tasks/backlog/feature-plan-defects/).
For full reproducer history and defence-layer breakdowns, follow
the per-class subfolder links below.

## Philosophy: plan-time prevention beats runtime detection

The cheapest place to reject a bad feature plan is the prompt
round-trip with the operator — one yes/no question, ~5 seconds,
zero SDK turns burned. The most expensive place is the turn-budget
burn that wastes minutes producing artefacts the gate will never
accept (~50–75 minutes per missed task in the FEAT-FD32 baseline).

Every defence in this folder is anchored at plan time, with a
runtime safety net for cases the planner misses. **Both layers must
miss for a defect to ship.** We bias toward false positives at the
plan-time layer — they cost one operator confirmation; false
negatives cost a full turn-budget burn.

## The three classes

| Class | Defect | Predicate type | Layer where prevention is anchored |
|---|---|---|---|
| **A** | Invented paths in `smoke_gates.command` | `present_on_disk(path)` | Plan-time path verification (L3a) + generator validator (L3b) |
| **B** | Temporal mis-sequencing of `after_wave` | `present_at_wave_W(path)` | Same validators as Class A, with wave-aware temporal check |
| **C** | Task-design mismatch — runtime-observation ACs | `observed_at_runtime(real_world)` | Plan-time detector + `operator_handoff` enforcement |

The three classes are **independent**: a single feature run can hit
one, two, or all three. Each has its own subfolder, parent review,
and prevention strategy. The unifying principle is the predicate
shape: A and B are about **paths the validator can check
deterministically**; C is about **claims that no validator can
check at all** because the verification predicate names the real
world rather than the codebase.

## Class A — invented paths

**Defect**: Plan agent emits a `smoke_gates.command` shell snippet
whose positional pytest paths do not exist in the target repo's
`tests/` tree. A single bad token (e.g. `tests/cli/` when only
`tests/unit/` exists) produces pytest exit 4 — pytest's "file or
directory not found" code — which `run_smoke_gate` treats as a
hard failure.

**Reproducer**: forge FEAT-DEA8 Run 2 (2026-05-02) — `tests/cli/`
in the smoke gate, no such directory in the forge repo,
17 minutes of SDK budget burned, 10 of 11 tasks blocked.

**Defence layers** (defence in depth — same defect rejected at ≥2 layers):

| Layer | Surface | Subtask | What it does |
|---|---|---|---|
| L3a | `feature-plan.md` prompt | TASK-FPSG-001 | "Path verification — REQUIRED" rule above the smoke-gate-author block |
| L3b | `generate-feature-yaml --validate-smoke-gates` | TASK-FPSG-002 | Parses positional argv, resolves each path against target repo, errors on miss |
| L3c | `smoke_gates_nudge` example block | TASK-FPSG-003 | Discovers and lists the target repo's actual `tests/` subdirs in the nudge banner |
| L3d | `guardkit feature validate FEAT-XXXX` | TASK-FPSG-004 | Same checks as L3b at the CLI validator + fixes the `~/.agentecflow/bin/guardkit` wrapper that previously silently no-op'd |
| L4 | `FeatureLoader._parse_feature` pre-flight | TASK-FPSG-005 | Final pre-flight at feature-load time, before any wave fires |

See [`tasks/backlog/feature-plan-defects/class-a-invented-paths/README.md`](../../tasks/backlog/feature-plan-defects/class-a-invented-paths/README.md)
and its [`IMPLEMENTATION-GUIDE.md`](../../tasks/backlog/feature-plan-defects/class-a-invented-paths/IMPLEMENTATION-GUIDE.md)
for the full layer breakdown and the shared `parse_positional_paths`
helper that L3b, L3d, and L4 all import.

## Class B — temporal mis-sequencing

**Defect**: Plan agent designs `after_wave: [2, 3]` for a smoke gate
whose target test file is created by a *Wave 3* task. The gate
fires after Wave 2, the file does not yet exist, pytest exits 4 —
the same exit code as Class A but with a different root cause
(a chicken-and-egg sequencing bug rather than a typo).

**Reproducer**: study-tutor FEAT-FD32 Run 2 (2026-05-02) —
`after_wave: [2, 3]` for a gate referencing
`tests/smoke/test_graphiti_live_smoke.py`, which TASK-GR-SMOK
(Wave 3, AC-SMOK-01) creates. Manual fix changed
`after_wave: [2, 3]` to `[3]`. 4 of 5 tasks blocked before the fix.

**Defence layers**: The Class A validators (L3b, L3d, L4) gain a
temporal check on top of the path-existence check. The check logic
lives with the Class A validators because they share the parser
(`parse_positional_paths`) and the same `smoke_gates` enforcement
points. For each `after_wave` value W and each positional path P:

- **Class A check**: Does P exist on disk **right now**?
- **Class B check**: If P does not exist now, does some task whose
  `wave < W` declare P in its acceptance criteria? If yes → fine.
  If no → **reject as Class B mis-sequencing** with a message
  naming the wave that creates the file.

A pragmatic shortcut: if any path P doesn't exist now AND there's
any task with `wave >= W` that mentions P in its acceptance
criteria → flag as a likely Class B mis-sequencing with a warning
recommending the user move `after_wave` to ≥ that task's wave.

The Class B subfolder is a stub that cross-links into the Class A
implementation —
[`tasks/backlog/feature-plan-defects/class-b-temporal-sequencing/README.md`](../../tasks/backlog/feature-plan-defects/class-b-temporal-sequencing/README.md)
explains the rationale.

## Class C — task-design mismatch

**Defect**: Plan agent emits acceptance criteria whose verification
predicate names the real world rather than the codebase —
`observed_at_runtime(real_world)` rather than
`present_in_codebase(artifact)`. Coach is a deterministic
file-existence and test-passing checker; it cannot satisfy these by
construction. The Player can scaffold for the observation but not
perform it. The Player↔Coach loop runs out of turns and the task is
blocked indefinitely.

**Reproducers** (study-tutor FEAT-FD32):
- **TASK-GR-SEED** — 7 of 8 ACs require live FalkorDB at
  `whitestocks:6379`. Outcome: 5 turns, 0/8 verified,
  `max_turns_exceeded`.
- **TASK-GR-DEMO** — 6 of 7 ACs require human-in-the-loop Claude
  Desktop session. Outcome: 5 turns, 0/7 verified,
  `max_turns_exceeded`.

Cumulative cost: ~110 minutes of SDK budget burned, 4 separate
`--resume` cycles + 2 manual completions, ~3 hours of debugging
across two days.

### Class C signal taxonomy

The detector at TASK-FPTC-001 (in `feature-plan.md`'s "Detection
Rules — when to mark a task `operator_handoff`" section) classifies
acceptance criteria by signal strength. **Strong signals fire on
their own; weak signals require pairing with a strong signal.**

**Strong signals** (any one triggers the operator prompt):

| Category | Verbatim phrases / patterns |
|---|---|
| **Live infrastructure** | `FalkorDB at <host>`, `Redis at <host>`, hostnames like `whitestocks`, `promaxgb10-*`, `localhost:<port>` paired with "live"/"production"; URLs to non-local services; "real LLM"; "real OpenAI"; "MCP query against running" |
| **Human verbs** | "conduct", "drive [N] turns", "observe", "human-in-the-loop", "operator", "Claude Desktop session", "open ChatGPT", "review the dashboard", "watch for", "monitor", "tutoring session" |
| **Wall-clock language** | "p50", "p95", "wall-clock", "latency over a N-minute run", "30 minutes of operation", "soak", "burn-in", "Expected ~30 min" |
| **Author self-disclosure** | Test Requirements section contains "There is no automated test harness for ...", "manual verification required", "operator runs the script and pastes the result", "cannot be satisfied by autobuild" |

**Weak signals** (require a strong signal to trigger):

- "verify", "ensure", "check" — often autobuild-suitable on their own
- "running" something — could be unit test or live run
- specific user names ("Lilymay", "test-user-123")
- specific dataset names that may or may not exist on disk

**False-positive guard.** A weak signal alone does NOT trigger.
Strong signals always trigger. Mixed (1 strong + N weak) trigger.
The detector flags; the human is the final arbiter via the
interactive prompt. We bias toward false positives — they cost one
operator confirmation; false negatives cost a full turn-budget burn.

### Examples

**Triggers** (`operator_handoff`):

- *"`python scripts/seed_student_model.py` runs successfully against
  live FalkorDB at whitestocks:6379 ..."* — live infrastructure +
  wall-clock.
- *"A live MCP tutor session is conducted from Claude Desktop with
  the user as the human-in-the-loop ..."* — live infrastructure +
  human verbs + author self-disclosure.

**Does NOT trigger**:

- *"All unit tests pass with `pytest tests/ -v`."* — verb `pass` is
  weak; no strong signals.
- *"`SettingsClass.from_env()` reads `FALKORDB_HOST` from environment
  ..."* — mentions FalkorDB but as a config string, not a live
  target.

The full rule text (with the interactive prompt verbatim) lives in
[`installer/core/commands/feature-plan.md`](../../installer/core/commands/feature-plan.md)
under "Detection Rules — when to mark a task `operator_handoff`".

## The `operator_handoff` escape hatch

When the detector fires (or the operator chooses it via the
interactive prompt), the task is emitted with `task_type:
operator_handoff` rather than the default. The full machinery:

1. **Plan time** (TASK-FPTC-001): detector flags the AC, prompt
   verbatim asks the operator to confirm. On `Y` (default), the task
   is emitted with `task_type: operator_handoff` and a
   `## Required operator follow-up` block listing the runtime ACs.
2. **Taxonomy** (TASK-FPTC-002): `OPERATOR_HANDOFF` registered as a
   `TaskType` enum value with its own quality-gate profile — no
   tests, no architectural review, no Player↔Coach loop.
3. **Orchestrator skip** (TASK-FPTC-003): `AutoBuildOrchestrator`
   short-circuits `operator_handoff` tasks before invoking the
   Player. The task moves to a deferred state, not BLOCKED.
4. **Validator awareness** (TASK-FPTC-004): `CoachValidator` and
   `FeatureLoader` treat `operator_handoff` as deferred-without-
   validation. No "0/N ACs verified" failure surfaces.
5. **Surface in `/feature-complete`** (TASK-FPTC-005): the operator
   follow-up checklist appears in the merge summary so the operator
   knows which tasks still need manual verification before sign-off.
6. **Detector tests** (TASK-FPTC-006): contract tests against the
   reproducers (TASK-GR-SEED, TASK-GR-DEMO) ensure the detector
   continues to flag them, plus three benign-looking ACs that must
   NOT trigger (false-positive guard).

**Net effect**: a Class C AC consumes one operator confirmation at
plan time, then `/feature-complete` reminds the operator post-merge
that the runtime checks still need to be performed by hand.
AutoBuild never burns a turn on a task it cannot satisfy.

## Backwards compatibility

Per parent-review AC-AUTM-04: **no retroactive labelling of
historical features.** The manual completion of TASK-GR-SEED and
TASK-GR-DEMO, plus the YAML provenance comments in
`appmilla_github/study-tutor/.guardkit/features/FEAT-FD32.yaml`, are
sufficient historical record. forge FEAT-DEA8 already shipped 11/11
post-Class-A fix; not affected.

## Related references

- [`tasks/backlog/feature-plan-defects/README.md`](../../tasks/backlog/feature-plan-defects/README.md)
  — three-class umbrella with cross-links.
- [`tasks/backlog/feature-plan-defects/class-c-task-design-mismatch/README.md`](../../tasks/backlog/feature-plan-defects/class-c-task-design-mismatch/README.md)
  — Class C subtask plan (FPTC-001..007) and wave breakdown.
- [`installer/core/commands/feature-plan.md`](../../installer/core/commands/feature-plan.md)
  — `/feature-plan` command spec, including the "Detection Rules"
  and "Interactive prompt step" subsections that implement the
  Class C detector.
- [`.claude/reviews/TASK-REV-AUTM-review-report.md`](../../.claude/reviews/TASK-REV-AUTM-review-report.md)
  — full rationale for Shape D (detector + enforcer) and the
  alternatives considered.
