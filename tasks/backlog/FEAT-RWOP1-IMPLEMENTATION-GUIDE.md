# FEAT-RWOP1 — Runner-without-producer orphan cleanup (implementation guide)

**Parent review:** [docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md](../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md)
**Cohort run gated on Phase 1:** [tasks/backlog/r2-pipeline-closure-and-forge-cohort/TASK-COH-RUN1-forge-and-study-tutor-cohort-run.md](r2-pipeline-closure-and-forge-cohort/TASK-COH-RUN1-forge-and-study-tutor-cohort-run.md)
**Design-rule candidate (Graphiti):** *"runner without producer anti-pattern"* — uuid `184731b0-3cb6-4eb2-a310-883421767dbf`

## Execution order at a glance

```
Phase 1 (cohort-blocking, parallelizable; MUST land before TASK-COH-RUN1 fires)
  ├── Track 1: RWOP1.1   (wire Step 11 BDD linking — ~1 day, complexity 6)
  └── Track 2: RWOP1.2   (fold Steps 10.6 + 10.7 nudges — ~3 hours, complexity 3)

Phase 2 (non-cohort-blocking, parallelizable; anytime after Phase 1)
  ├── Track A: RWOP1.3   (task-work orphan rollup, 22 decisions — ~2–3 days, complexity 6)
  ├── Track B: RWOP1.4   (feature-spec Coach gating + dead surface — ~4–6h, complexity 4)
  └── Track C: RWOP1.5   (/feature-plan --from-spec disposition — ~1–2h, complexity 3)

Phase 3 (cohort run, gated on Phase 1; same-folder pre-existing task)
  └── TASK-COH-RUN1      (forge + study-tutor cohort run + report, ~half day attended)

Phase 4 (follow-up; file when Phase 2 completes)
  └── TASK-REV-RWOP2     (closure review — confirm wiring rate ≥ 75%; decide on pre-commit hook)
```

**Total effort:** ~3 days focused work for Phase 1 + ~3 days for
Phase 2 (runnable in three parallel Conductor workspaces) + half-day
attended cohort run. Phase 4 is a half-day review.

---

## Phase 1 — Cohort-blocking fixes (MUST land first)

Both tasks live in
[tasks/backlog/r2-pipeline-closure-and-forge-cohort/](r2-pipeline-closure-and-forge-cohort/)
alongside `TASK-COH-RUN1`. They use the TASK-FIX-3C9D producer-script
pattern: imperative call folded into the script that `/feature-plan`
already executes.

### Phase 1, Track 1 — TASK-FIX-RWOP1.1 (wire Step 11 BDD linking)

**Mission:** close the R2 load-bearing orphan. Step 11 of
`/feature-plan` claims to invoke the `bdd-linker` subagent to
auto-`@task:`-tag BDD scenarios, but the Python orchestrator
(`run_linking_phase`) has zero production callers and the subagent
is unreachable through any path. Without this fix, cohort features
ship un-tagged → R2 BDD oracle collects zero scenarios → silent green
across the entire cohort report.

**Task file:** [r2-pipeline-closure-and-forge-cohort/TASK-FIX-RWOP1.1-wire-feature-plan-step-11-bdd-linking.md](r2-pipeline-closure-and-forge-cohort/TASK-FIX-RWOP1.1-wire-feature-plan-step-11-bdd-linking.md)

**Files:**

- [installer/core/commands/feature-plan.md](../../installer/core/commands/feature-plan.md) — Step 11 prose rewrite (lines 2407-2533)
- [installer/core/agents/bdd-linker.md](../../installer/core/agents/bdd-linker.md) — possible agent-scope expansion (if Path A)
- New: `installer/core/commands/lib/feature_plan_bdd_link.py` (if Path B)
- New: `tests/integration/feature_plan/test_bdd_linking_end_to_end.py`
- [installer/core/commands/lib/bdd_linking_phase.py](../../installer/core/commands/lib/bdd_linking_phase.py) — add docstring noting production-caller status (module itself unchanged)

**Decisions to make:**

- **Path A (Claude-runtime)** — rewrite Step 11 prose to use
  `INVOKE Task(bdd-linker, ...)` directly (same pattern as
  `clarification-questioner` at Step 2); agent owns end-to-end
  work including file edits. Cleaner but relies on Claude-runtime
  interpretation (see TASK-FIX-7B2E §"Retro grep of FEAT-JARVIS-001"
  for why this can be non-deterministic).
- **Path B (producer script)** — new `feature_plan_bdd_link.py` CLI
  with `--prepare` and `--apply` modes; Step 11 uses
  `Execute: python3 ~/.agentecflow/bin/feature-plan-bdd-link --prepare`
  then `INVOKE Task(bdd-linker, ...)` with piped JSON then
  `--apply`. Matches TASK-FIX-3C9D R1 shape exactly.

Suggested default: **Path B**. Deterministic across Claude sessions;
consistent with the R1 fix shape; robust against the non-determinism
TASK-FIX-7B2E documented.

**Traps:**

- Don't rewrite `bdd_linking_phase.run_linking_phase` internals — the
  existing contract (interactive / non-interactive / threshold /
  idempotency / matcher-errors) is well-tested and stable.
- Single positive dynamic test is NOT sufficient evidence under
  Claude-as-runtime. If Path A, verify across ≥ 2 fresh Claude
  sessions before declaring done.
- Don't forget TASK-COH-RUN1's `depends_on` update (already noted in
  the task file) — closeout only.

**Validation:**

- Non-test caller exists — `grep -rn "run_linking_phase\|feature_plan_bdd_link" --include="*.py" | grep -v "test_\|/tests/\|bdd_linking_phase.py:"` returns ≥ 1 match in `installer/` or `guardkit/`.
- End-to-end test asserts `@task:` tag appears on at least one scenario in the output `.feature` file.
- Dynamic verification: `/feature-plan` against `tests/fixtures/r1-verification/prose-ac-spec.md` + a companion `.feature` skeleton produces a tagged output file. Transcript at `.claude/reviews/TASK-FIX-RWOP1.1-bdd-linking-verification.md`.
- Pre-existing 33/33 green test baseline maintained.

**Effort:** 1 day focused. Complexity-6.

### Phase 1, Track 2 — TASK-FIX-RWOP1.2 (fold Step 10.6 + 10.7 nudges)

**Mission:** close the R2 and R3 fallback signals. Step 10.6 (BDD
oracle activation nudge) and Step 10.7 (R3 smoke-gates activation
nudge) are exact twins of the R1 orphan: unit-tested in isolation
(24 green tests combined), zero non-test callers. Fix is mechanically
~10 lines of code following the TASK-FIX-3C9D pattern.

**Task file:** [r2-pipeline-closure-and-forge-cohort/TASK-FIX-RWOP1.2-fold-bdd-oracle-and-smoke-gates-nudges.md](r2-pipeline-closure-and-forge-cohort/TASK-FIX-RWOP1.2-fold-bdd-oracle-and-smoke-gates-nudges.md)

**Files:**

- [installer/core/commands/lib/generate_feature_yaml.py](../../installer/core/commands/lib/generate_feature_yaml.py) — add two nudge calls after the existing AC-linter block (~lines 710-713)
- [installer/core/commands/feature-plan.md](../../installer/core/commands/feature-plan.md) — Step 10.6 + 10.7 prose rewrite (lines 2313-2405); execution-trace updates around lines 2424 and 2478-2481
- New: `tests/integration/feature_plan/test_generate_feature_yaml_nudges.py`

**Decisions to make:**

Already decided by the review — fold into producer script, exactly
matching TASK-FIX-3C9D R1 shape. No path choice.

**Traps:**

- Ensure `output_path` (the feature YAML path, defined at
  `generate_feature_yaml.py:700` for the AC-linter block) is in
  scope where the smoke-gates nudge call lands. Pass it explicitly.
- Match `generate_feature_yaml.py`'s existing import-style convention
  — it uses top-of-file `try: ... except ImportError:` with
  `_AC_LINTER_AVAILABLE` pattern. Copy that shape for the nudges.
- Don't add any new `bin-entries.txt` entries. `generate-feature-yaml`
  is already exposed by TASK-FIX-B1E4.
- Don't re-tune `UNVERIFIABLE_CONFIDENCE_THRESHOLD` or any nudge
  internals. Only add callers.

**Validation:**

- Both helpers have non-test callers — `grep -rn "check_bdd_oracle_activation\|check_smoke_gates_activation" --include="*.py" | grep -v "test_\|/tests/\|bdd_oracle_nudge.py:\|smoke_gates_nudge.py:"` returns 2 matches inside `generate_feature_yaml.py`.
- Step 10.6 + 10.7 prose rewritten to "runs transitively via Step 8" shape (match Step 10.5 post-TASK-FIX-3C9D).
- Both execution traces (Flag-Only + Structured) name Steps 10.6 and 10.7 inside Step 8's block.
- E2E test drives `generate_feature_yaml.py` with a fixture workspace missing `@task:` tags AND `smoke_gates:`; both banners appear in stdout; both suppressed in `--quiet` mode. Transcript at `.claude/reviews/TASK-FIX-RWOP1.2-nudges-verification.md`.
- Existing 24 unit tests still green.

**Effort:** 2.5–3.5 hours. Complexity-3. Lowest-risk task in the
feature; essentially copy-paste of the TASK-FIX-3C9D mechanics.

### Phase 1 gate criterion (before Phase 3 / TASK-COH-RUN1 fires)

Both Track 1 and Track 2 complete. TASK-COH-RUN1's `depends_on`
contains `TASK-FIX-RWOP1.1` + `TASK-FIX-RWOP1.2` (already added by
the review). Pre-flight greps land:

```bash
# R1 (pre-existing)
grep -q 'AC-quality review:' /path/to/cohort-member/feature-plan-stdout.log

# R2 (new, from this review)
grep -l '@task:' /path/to/cohort-member/features/*.feature  # → at least one match
# OR
grep -q 'BDD oracle activation' /path/to/cohort-member/feature-plan-stdout.log

# R3 (new, from this review)
grep -E '^smoke_gates:' /path/to/cohort-member/.guardkit/features/FEAT-*.yaml
# OR
grep -q 'smoke gates activation' /path/to/cohort-member/feature-plan-stdout.log
```

---

## Phase 2 — Non-cohort-blocking cleanup

All three tracks live in
[tasks/backlog/feat-rwop1-orphan-cleanup/](feat-rwop1-orphan-cleanup/).
See that folder's
[IMPLEMENTATION-GUIDE.md](feat-rwop1-orphan-cleanup/IMPLEMENTATION-GUIDE.md)
for per-track detail (files, decisions, traps, validation, effort).

Summary:

- **Track A — RWOP1.3 (task-work orphan rollup)**: 22 wire-vs-delete decisions + execution. Largest of the three. Produces `docs/reviews/TASK-FIX-RWOP1.3-task-work-triage.md` + wires at minimum `validate_agent_invocations` and `execute_phase_5_5_plan_audit`. Target post-execution wiring rate for `task-work.md`: ≥ 75 % (up from 34.9 %).
- **Track B — RWOP1.4 (feature-spec decisions)**: two independent
  choices — Phase 5 Coach gating (WIRE / SOFTEN / ESCALATE) +
  `FeatureSpecCommand` disposition (PROMOTE / DELETE). Target
  post-execution hard-module wiring rate for `feature-spec.md`:
  ≥ 50 % (up from 10 %).
- **Track C — RWOP1.5 (--from-spec disposition)**: single choice —
  WIRE / DELETE / EXTRACT the 8-helper pre-existing orphan chain.
  Default: DELETE.

All three are independent of each other and run in parallel.

---

## Phase 3 — Cohort run (TASK-COH-RUN1)

Already filed at [r2-pipeline-closure-and-forge-cohort/TASK-COH-RUN1-forge-and-study-tutor-cohort-run.md](r2-pipeline-closure-and-forge-cohort/TASK-COH-RUN1-forge-and-study-tutor-cohort-run.md).
Gated on Phase 1 completion.

The TASK-REV-RWOP1 review updated COH-RUN1's `depends_on` + added the
R2/R3 pre-flight greps noted in Phase 1.

---

## Phase 4 — Follow-up review (TASK-REV-RWOP2, to be filed)

After Phase 2 completes, file a closure review task that:

1. Recomputes the runner-without-producer wiring rate across all three
   spec files (target: ≥ 75 % overall, up from 33.8 %).
2. Updates the Graphiti `"runner without producer anti-pattern"` node
   with the final evidence: sample size (should now be ≤ ~15 remaining
   orphans, if DELETE verdicts were executed), wiring rate, final
   canonical fix shape.
3. Decides whether the pattern should graduate from
   candidate-design-rule to enforced-design-rule via a pre-commit hook
   that greps `installer/core/commands/*.md` imperatives against
   runtime-caller evidence. Rejected once already by TASK-REV-RWOP1 as
   out-of-scope; the evidence base after Phase 2 may support it.

Do not file TASK-REV-RWOP2 until Phase 2 is complete — filing early
forces premature closure.

---

## Dependency graph

```
FEAT-RWOP1
├── Phase 1 (cohort-blocking)
│   ├── RWOP1.1  (no blockers; requires TASK-FIX-3C9D shape understanding)
│   └── RWOP1.2  (no blockers; simplest of the five)
├── Phase 2 (non-cohort-blocking)
│   ├── RWOP1.3  (no blockers)
│   ├── RWOP1.4  (no blockers)
│   └── RWOP1.5  (no blockers; prefer after RWOP1.1 + RWOP1.2 for priority reasons)
├── Phase 3
│   └── TASK-COH-RUN1  → blocked on: RWOP1.1 + RWOP1.2
└── Phase 4
    └── TASK-REV-RWOP2 (not yet filed) → blocked on: RWOP1.3 + RWOP1.4 + RWOP1.5
```

---

## Related

- Parent review: [docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md](../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md)
- Grandparent review: [docs/reviews/TASK-REV-4D190-jarvis-first-autobuild-review.md](../../docs/reviews/TASK-REV-4D190-jarvis-first-autobuild-review.md) §R1 / Addendum A
- Canonical fix shape (R1 precedent): [tasks/completed/TASK-FIX-3C9D/TASK-FIX-3C9D-wire-ac-linter-into-feature-plan.md](../completed/TASK-FIX-3C9D/TASK-FIX-3C9D-wire-ac-linter-into-feature-plan.md)
- Precursor verification: [.claude/reviews/TASK-FIX-7B2E-r1-wiring-verification.md](../../.claude/reviews/TASK-FIX-7B2E-r1-wiring-verification.md)
- Sibling narrow re-audit: [docs/reviews/TASK-REV-AC53-reaudit-task-ac-53445.md](../../docs/reviews/TASK-REV-AC53-reaudit-task-ac-53445.md)
- Cohort workstream: [tasks/backlog/r2-pipeline-closure-and-forge-cohort/](r2-pipeline-closure-and-forge-cohort/)
- Hygiene workstream: [tasks/backlog/feat-rwop1-orphan-cleanup/](feat-rwop1-orphan-cleanup/)
