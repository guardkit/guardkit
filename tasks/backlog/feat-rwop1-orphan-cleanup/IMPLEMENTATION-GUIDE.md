# Implementation guide — FEAT-RWOP1 orphan cleanup (non-cohort-blocking)

**Scope**: the three non-cohort-blocking tasks in this folder. For
the cohort-blocking pair (RWOP1.1 + RWOP1.2), see
[../FEAT-RWOP1-IMPLEMENTATION-GUIDE.md](../FEAT-RWOP1-IMPLEMENTATION-GUIDE.md).

## Execution order at a glance

```
Anytime (do in parallel; none blocks another; none blocks TASK-COH-RUN1)
  ├── Track A: RWOP1.3   (task-work rollup — largest, ~2–3 days with triage)
  ├── Track B: RWOP1.4   (feature-spec decisions — ~4–6 hours)
  └── Track C: RWOP1.5   (--from-spec disposition — ~1–2 hours)
```

Total: ~3 days of focused work across three tracks, runnable in
parallel Conductor workspaces if desired. Each track is independently
mergeable.

---

## Track A — TASK-FIX-RWOP1.3 (task-work orphan rollup)

**Mission**: decide wire-vs-delete for 22 orphaned imperatives in
`installer/core/commands/task-work.md`, then execute the decisions.
This is the largest and most decision-heavy of the three tracks.

**Files** (expected touch-surface):

- [installer/core/commands/task-work.md](../../../installer/core/commands/task-work.md) — spec prose rewrites (probably Phase 2/2.5B/3/4/5 phase-gate block softening OR deletion; Phase 2.7/2.8/4.5 pseudo-code rewrites; Phase 5.5 plan_audit structural wiring; Step 6.5 validate_agent_invocations wiring; Step 8 commit_state_files wiring or removal)
- [guardkit/orchestrator/agent_invoker.py](../../../guardkit/orchestrator/agent_invoker.py) — probable WIRE target (most orphans land here as post-Player-stream validators)
- [guardkit/orchestrator/quality_gates/coach_validator.py](../../../guardkit/orchestrator/quality_gates/coach_validator.py) — probable consumer for new validator outputs
- [installer/core/commands/lib/__init__.py](../../../installer/core/commands/lib/__init__.py) — remove stale re-exports per DELETE-MODULE verdicts; clear the `QuickReviewHandler` TEMPORARY FIX comment one way or another
- Various `installer/core/commands/lib/*.py` — delete modules per DELETE-MODULE verdicts
- New triage doc: `docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md`

**Decisions to make** (record in the triage doc):

For each of the 22 orphans in [TASK-REV-RWOP1 Appendix A](../../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md#appendix-a--task-workmd-raw-findings),
pick:

- **WIRE** — the gate is worth enforcing deterministically; add a
  real caller + propagate violation into `task_work_results.json` for
  Coach.
- **DELETE-MODULE** — Python module is unit-tested but never called;
  contract is Claude-runtime; delete the module + re-export + tests.
- **DELETE-PROSE** — spec references pseudo-code that doesn't merit a
  module; soften to LLM-intent language.

**Priority-ranked WIRE candidates** (start here even before full
triage if you want an early win):

1. `validate_agent_invocations` (Step 6.5) — spec-declared sole
   safeguard against false reporting; wiring is high-leverage.
2. `execute_phase_5_5_plan_audit` (Phase 5.5) — Coach consumes the
   field; producer is LLM-prose. TASK-FIX-3C9D shape applies exactly.
3. `PhaseGateValidator.validate_phase_completion` — six prose
   callsites; deterministic post-phase check replaces LLM self-report.

**Traps**:

- Don't blanket-WIRE. Most of `feature_detection.supports_*`,
  `library_detector.detect_library_mentions`,
  `library_context.gather_library_context`, `flag_validator` are
  genuine Claude-runtime intent signals — wiring them adds ceremony
  without catching anything a Player would actually fake. DELETE-MODULE
  those; keep the spec prose as intent guidance.
- Don't touch the autobuild inline protocols
  (`autobuild_design_protocol.md`, `autobuild_execution_protocol.md`).
  Those are separate artifacts with their own (future) triage.
- Do NOT block TASK-COH-RUN1 on this track.

**Validation**:

- Triage doc exists with per-orphan verdict + rationale.
- At minimum RWOP1.3 Phase 2 items 1 and 2 wired with end-to-end
  tests demonstrating Coach catches a Player that skips them.
- `QuickReviewHandler` TEMPORARY FIX comment in `lib/__init__.py` is
  resolved (either the import is live or the comment is gone).
- Post-execution wiring rate for `task-work.md` ≥ 75 % (up from 34.9 %).

**Effort**: 2–3 days. Phase 1 triage alone is ~half a day.

---

## Track B — TASK-FIX-RWOP1.4 (feature-spec Coach gating + dead surface)

**Mission**: resolve two independent concerns in `/feature-spec`:
(a) Phase 5 Coach low-confidence assumption gating (unwired gating
claim); (b) `FeatureSpecCommand` Python orchestrator (dead code with
a live twin).

**Files**:

- [installer/core/commands/feature-spec.md](../../../installer/core/commands/feature-spec.md) — Phase 5 prose line 337 (WIRE → keep; SOFTEN → rewrite)
- [guardkit/orchestrator/quality_gates/coach_validator.py](../../../guardkit/orchestrator/quality_gates/coach_validator.py) — add `_assumptions.yaml` hook if Part A = WIRE
- [guardkit/commands/feature_spec.py](../../../guardkit/commands/feature_spec.py) — delete (if Part B = DELETE) or wire into CLI (if PROMOTE)
- [guardkit/cli/feature.py](../../../guardkit/cli/feature.py) — add `guardkit feature spec` subcommand (if PROMOTE)
- [installer/core/commands/bin-entries.txt](../../../installer/core/commands/bin-entries.txt) — add manifest entry (if PROMOTE)
- Decision doc: `.claude/reviews/TASK-FIX-RWOP1.4-decisions.md`

**Decisions to make**:

Two independent choices (capture rationale per part in the
decision doc):

- Part A: WIRE vs SOFTEN vs ESCALATE
- Part B: PROMOTE vs DELETE

Suggested defaults: Part A = WIRE (low-confidence assumptions
cascading into BDD scenarios silently is the same failure class as
R1); Part B = DELETE (there's a live twin at
`graphiti/parsers/feature_spec.py`; promoting adds a CLI nobody is
asking for).

**Traps**:

- Part A WIRE — don't emit a hard block; Coach gating should be a
  warning/flag, not a failure, unless there's strong signal the
  low-confidence cascades are breaking things. Start with warn-mode.
- Part B DELETE — don't delete `seed_to_graphiti` until you've
  confirmed `guardkit/integrations/graphiti/parsers/feature_spec.py`
  covers the same scenarios-seeding behaviour. Check the `.guardkit/quality-gates/FEAT-1253.yaml:22` smoke-import too.
- Do NOT block TASK-COH-RUN1 on this track.

**Validation**:

- Decision doc exists with rationale per part.
- If Part A = WIRE: at least one E2E test asserts Coach's behaviour
  on a `_assumptions.yaml` with `confidence: low` rows.
- If Part B = DELETE: `grep -r "FeatureSpecCommand" --include="*.py"
  | grep -v "test_\|/tests/"` returns zero matches.
- Post-execution wiring rate for `feature-spec.md` hard-module
  imperatives ≥ 50 % (up from 10 %).

**Effort**: 4–6 hours.

---

## Track C — TASK-FIX-RWOP1.5 (--from-spec orphan chain)

**Mission**: resolve 8-helper orphan chain under `--from-spec` flag
in `/feature-plan`. Pre-existing pattern unrelated to R1/R2/R3; pure
hygiene.

**Files**:

- [installer/core/commands/feature-plan.md](../../../installer/core/commands/feature-plan.md) lines 247-278 — rewrite OR delete
- `guardkit/planning/*.py` — delete, relocate, or promote depending on path
- [installer/core/commands/bin-entries.txt](../../../installer/core/commands/bin-entries.txt) — add manifest entry (if WIRE)

**Decisions to make**:

- WIRE (add a `feature-plan-from-spec` bin entry)
- DELETE (remove the flag + helpers, or move helpers to `_scratch/`)
- EXTRACT (move helpers into a separate `guardkit plan spec` CLI
  subcommand)

Suggested default: **DELETE**. The `--from-spec` block predates
current design; check git history for any real usage before deciding.

**Traps**:

- If DELETE + you want a safety window, move helpers to
  `guardkit/_scratch/planning/` with a README noting reason + date,
  rather than outright deletion. 90-day window before true removal.
- Do NOT run this track until after RWOP1.1 + RWOP1.2 land — those
  are the priority.

**Validation**:

- Decision doc at `.claude/reviews/TASK-FIX-RWOP1.5-from-spec-decision.md`
  (~200 words).
- Post-execution grep for the 8 helpers returns either all-wired or
  all-absent, consistent with the chosen path.
- `/feature-plan` unit + integration suite remains green.

**Effort**: 1–2 hours.

---

## After all three land

Update the TASK-REV-RWOP1 review's wiring-rate numbers with the
post-execution measurements. Consider filing a thin follow-up review
(`TASK-REV-RWOP2` or similar) to confirm the pattern was closed — or,
if the wiring rate is still < ~75 % overall, to triage remaining items.

Graphiti update: add a closure episode to `guardkit__project_decisions`
noting the final wiring rate after RWOP1.3–1.5 land, and whether the
"runner without producer" pattern should now graduate from
candidate-design-rule to enforced-design-rule (possibly via a
pre-commit hook that greps for imperatives in command-spec `.md`
files against caller evidence in runtime code).
