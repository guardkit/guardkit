# TASK-REV-AC53 — Re-audit of TASK-AC-53445 for other "runner without producer" orphans

**Task:** TASK-REV-AC53
**Parent task under re-review:** TASK-AC-53445 (landed 2026-04-21)
**Motivating verification:** TASK-FIX-7B2E
  (`.claude/reviews/TASK-FIX-7B2E-r1-wiring-verification.md`)
**Date:** 2026-04-22
**Mode:** code-quality / architectural re-audit · depth: standard
**Verdict:** **Clean** — TASK-AC-53445's delivery surface has no remaining
orphan runners. The one orphan previously identified (R1 / Step 10.5)
was closed by TASK-FIX-3C9D, which landed the imperative callsite in
`installer/core/commands/lib/generate_feature_yaml.py` (the producer
step 8 executes). No further remediation tasks filed from this review.
One *incidentally observed* pre-existing concern is noted in §Incidental
Observations and is explicitly **out of scope** for this re-audit.

---

## Audit frame

The lens applied is the "runner without producer" anti-pattern from
TASK-REV-4D190 Addendum A, restated here:

> A verifier, linter, or callable described in a command spec must have
> either (a) an imperative `Execute:` / `Run:` / `Call:` line in that
> spec's execution trace, or (b) an imperative callsite in an upstream
> script that the spec does invoke. A callable described only in prose
> is, under the Claude-follows-markdown runtime, a documented-only
> callable — fires non-deterministically across sessions (see
> TASK-FIX-7B2E §"Retro grep of FEAT-JARVIS-001").

For each new callable and each new spec step introduced by TASK-AC-53445,
we ask:
1. Is there a runtime caller that is (a) NOT a test and (b) NOT the
   module that defines it?
2. For spec steps: is the step reachable from an `Execute:` / `Run:` /
   `Call:` line (directly or transitively through a script that is
   itself imperatively invoked)?

---

## Delivery surface of TASK-AC-53445

Per TASK-AC-53445 Implementation Summary
(`tasks/completed/2026-04/TASK-AC-53445-assertable-ac-linter-feature-plan.md:107-128`):

| # | File | Kind | TASK-AC-53445 additions |
|---|---|---|---|
| 1 | `guardkit/orchestrator/quality_gates/criteria_classifier.py` | Python module | `UNVERIFIABLE_CONFIDENCE_THRESHOLD` constant (line 233); `UnverifiableACWarning` dataclass (line 237); `classify_with_warnings()` (line 250) |
| 2 | `guardkit/orchestrator/quality_gates/ac_linter.py` | New Python module (83 lines) | `lint_plan_warnings()` (line 33); `format_warning_summary()` (line 56) |
| 3 | `installer/core/commands/feature-plan.md` | Command spec | Step 10.5 "AC-quality review (warn-mode v1)" |
| 4 | `tests/unit/test_criteria_classifier.py` | Unit tests | `TestUnverifiableACWarning` × 4 + `TestLinterHasNoIndependentPatterns` × 2 |
| 5 | `tests/integration/feature_plan/test_ac_linter_warning_flow.py` | Integration tests | `TestProseAcsSurfaceWarnings` × 6 + `TestLinterReasonFidelity` × 1 |

Tests (rows 4 & 5) are out of frame for the anti-pattern — their
"producer" is the pytest runner, which is how tests are meant to be
reached. The audit therefore focuses on rows 1–3.

---

## Per-item findings

### Row 1 — `criteria_classifier.py` additions

| New symbol | Location | Runtime consumer outside the defining module | Verdict |
|---|---|---|---|
| `UNVERIFIABLE_CONFIDENCE_THRESHOLD` (constant `0.6`) | [`criteria_classifier.py:233`](../../guardkit/orchestrator/quality_gates/criteria_classifier.py#L233) | **Self-consumed** at [`criteria_classifier.py:283`](../../guardkit/orchestrator/quality_gates/criteria_classifier.py#L283) inside `classify_with_warnings`. Referenced in prose by [`ac_linter.py` docstring (line 17)](../../guardkit/orchestrator/quality_gates/ac_linter.py#L17) and by `feature-plan.md:2265` as the "v1→v2 threshold knob." No non-prose external reader, but this is the correct shape for a module-internal knob: v2 block-mode is a literal one-line edit to this constant. | **Not an orphan.** |
| `UnverifiableACWarning` dataclass | [`criteria_classifier.py:237`](../../guardkit/orchestrator/quality_gates/criteria_classifier.py#L237) | Instantiated at [`criteria_classifier.py:285`](../../guardkit/orchestrator/quality_gates/criteria_classifier.py#L285) (inside `classify_with_warnings`); imported as a return-type at [`ac_linter.py:28`](../../guardkit/orchestrator/quality_gates/ac_linter.py#L28); instances returned to runtime caller [`generate_feature_yaml.py:711`](../../installer/core/commands/lib/generate_feature_yaml.py#L711). | **Not an orphan.** |
| `classify_with_warnings()` | [`criteria_classifier.py:250`](../../guardkit/orchestrator/quality_gates/criteria_classifier.py#L250) | Called at [`ac_linter.py:51`](../../guardkit/orchestrator/quality_gates/ac_linter.py#L51). | **Not an orphan.** |

### Row 2 — `ac_linter.py` (new module)

| New symbol | Location | Runtime consumer outside tests and the defining module | Verdict |
|---|---|---|---|
| `lint_plan_warnings(tasks)` | [`ac_linter.py:33`](../../guardkit/orchestrator/quality_gates/ac_linter.py#L33) | **Called at [`generate_feature_yaml.py:711`](../../installer/core/commands/lib/generate_feature_yaml.py#L711)** in `main()`, guarded by `AC_LINTER_AVAILABLE and not args.quiet`. `generate_feature_yaml.py` is imperatively invoked by Step 8 of `/feature-plan` (see §"Spec-trace reachability" below). | **Not an orphan (post TASK-FIX-3C9D).** At TASK-AC-53445 delivery this was R1 — the orphan TASK-FIX-7B2E identified. Closed 2026-04-22 by TASK-FIX-3C9D. |
| `format_warning_summary(warnings)` | [`ac_linter.py:56`](../../guardkit/orchestrator/quality_gates/ac_linter.py#L56) | **Called at [`generate_feature_yaml.py:713`](../../installer/core/commands/lib/generate_feature_yaml.py#L713)** in `main()`. | **Not an orphan (post TASK-FIX-3C9D).** |

### Row 3 — `feature-plan.md` Step 10.5

**Reachability check.** Step 10.5 reads (after TASK-FIX-3C9D rewrite):

> *"**No separate step here.** The AC linter's imperative callsite
> lives in `installer/core/commands/lib/generate_feature_yaml.py` (the
> producer step 8 executes)."* — [`feature-plan.md:2241-2250`](../../installer/core/commands/feature-plan.md#L2241-L2250)

Step 8 is imperative. Both example execution traces now name Step 10.5
inside Step 8's block:

- Flag-Only trace, [`feature-plan.md:2424`](../../installer/core/commands/feature-plan.md#L2424):
  *"Script transitively runs the AC-quality linter (Step 10.5): prints
  `AC-quality review: N unverifiable acceptance criteria detected` to
  stdout in non-quiet mode (warn-only, non-blocking)"*
- Structured trace, [`feature-plan.md:2478-2481`](../../installer/core/commands/feature-plan.md#L2478-L2481):
  *"Script ALSO runs the AC-quality linter (Step 10.5) and appends
  `AC-quality review: …` to stdout (warn-only, non-blocking). This is
  the deterministic R1 callsite; see TASK-FIX-3C9D."*

**Verdict: not an orphan (post TASK-FIX-3C9D).** The *spec-to-runtime*
loop is now closed on both sides: the runtime has a caller
(generate_feature_yaml.py), the spec names it in Step 8's execution
trace, and Step 10.5 itself documents "runs transitively via step 8"
rather than narrating its own imperatives. This is the textbook
remediation shape the TASK-REV-4D190 design-rule candidate calls for.

At TASK-AC-53445 delivery time Step 10.5 was a pure prose description —
no `Execute:` line, not named in the execution trace, no in-repo caller
— and relied on Claude-as-runtime interpretation of descriptive text to
fire. The 2026-04-22 verification (TASK-FIX-7B2E) caught this.

### Rows 4–5 — Test files

Out of frame. Tests are invoked by the pytest runner; their
"producer" relationship is the test harness, not a runtime caller. The
only anti-pattern risk in tests is stale imports / dead tests, which
the grep above would surface — none found.

One secondary observation, not a finding in the anti-pattern sense:
`tests/integration/feature_plan/test_ac_linter_warning_flow.py` calls
`lint_plan_warnings(mock_feature_plan_output)` **directly** against
constructed task dicts. It does not drive `/feature-plan` end-to-end,
which is why TASK-AC-53445's 33/33 green suite was consistent with R1
being unwired — the test exercised the linter library in isolation.
TASK-FIX-3C9D filed
`tests/integration/feature_plan/test_generate_feature_yaml_linter.py`
(present in this repo's git status as untracked at audit time) which
closes that gap by driving the producer script via subprocess. This is
a test-coverage observation, not a runner-without-producer finding.

---

## Spec-trace reachability (Step 10.5 specifically)

Walking the Structured execution trace in
[`feature-plan.md:2435-2482`](../../installer/core/commands/feature-plan.md#L2435-L2482):

| Trace step | Imperative? | Reaches Step 10.5? |
|---|---|---|
| 1. Parse feature description | implicit | no |
| 2. `INVOKE Task(clarification-questioner, ...)` | `INVOKE` | no |
| 3. `/task-create ...` | slash command | no |
| 4. `/task-review ...` | slash command | no |
| 5. User choice | interactive | no |
| 6. `INVOKE Task(clarification-questioner, context=impl_prefs)` | `INVOKE` | no |
| 7. "Creates structure" — feature folder, subtasks, diagrams | inferred from §Step 6 | no |
| **8.** **`Execute: python3 ~/.agentecflow/bin/generate-feature-yaml …`** | **Execute:** | **YES** — the script's `main()` calls `lint_plan_warnings` + `format_warning_summary` at `generate_feature_yaml.py:711-713` |
| 8.5. `Execute: guardkit feature validate FEAT-XXXX` | `Execute:` | no (post-linter validation) |
| 9. Show completion summary | implicit | no |

Step 10.5's numbering persists in the spec as a narrative header
(`10.5. ✅ AC-quality review (warn-mode v1) — runs transitively via
step 8`) but its runtime is now attached to step 8, not an independent
execution step. This collapse is what TASK-FIX-3C9D delivered. The
header is documentation; the wiring is imperative.

---

## Incidental observations (out of scope — do not file remediation from here)

These were noticed while walking the files and are recorded for
completeness. Each is explicitly **not** a TASK-AC-53445 delivery
orphan.

1. **`~/.agentecflow/bin/generate-feature-yaml` is absent on the
   current install.** `ls ~/.agentecflow/bin/` shows symlinks for
   `agent-enhance`, `agent-format`, `agent-validate`, `gk`, `gki`,
   `graphiti-check`, `graphiti-diagnose`, `guardkit`, `guardkit-init`
   — but no `generate-feature-yaml`. `installer/scripts/` contains no
   reference to installing it. Step 8 of `/feature-plan` nonetheless
   says `Execute: python3 ~/.agentecflow/bin/generate-feature-yaml …`
   at `feature-plan.md:2176`, `:2200`, `:2468`. This could weaken the
   R1 wiring chain under a stricter Claude-as-runtime that refuses to
   substitute the missing binary path — the linter callsite would be
   unreachable because its container is. The 2026-04-22 dynamic run in
   TASK-FIX-7B2E nonetheless produced the AC-quality header, which
   implies Claude-as-runtime (a) resolved the path to
   `installer/core/commands/lib/generate_feature_yaml.py` directly, or
   (b) ran the Python inline from the import, without going through
   `~/.agentecflow/bin/`.

   **Explicitly out of scope for this review.** The missing binary
   predates TASK-AC-53445 (see `.claude/reviews/TASK-REV-1BE3-review-report.md`
   which referenced the same path) and belongs to whatever owns the
   installer's binary deployment. Not a TASK-AC-53445 delivery orphan.

   **Update 2026-04-22 (post-checkpoint):** User chose [I]mplement at
   the decision checkpoint specifically to file this observation.
   Filed as **TASK-FIX-B1E4** (priority: low, complexity: 2) at
   `tasks/backlog/TASK-FIX-B1E4-install-generate-feature-yaml-bin-symlink.md`.
   Root cause identified: `generate_feature_yaml.py` is missing from
   [`installer/core/commands/bin-entries.txt`](../../installer/core/commands/bin-entries.txt)
   — the manifest that `bin-entries.txt`'s own preamble declares is the
   SOLE source of truth for which Python scripts under `commands/` get
   exposed as `~/.agentecflow/bin/` symlinks. Fix is a one-line
   manifest addition + reinstall.

2. **Step 10.6 (BDD oracle nudge) was added by TASK-FP-NDG1 into the
   same file.** It is *not* a TASK-AC-53445 addition (it references
   Step 10.5 as a predecessor but is itself TASK-FP-NDG1's delivery —
   see `tasks/completed/TASK-FP-NDG1/TASK-FP-NDG1.md`). **Not audited
   here.** If any re-audit of TASK-FP-NDG1 is wanted under the same
   lens, file separately.

---

## Against the task acceptance criteria

| AC | Status |
|---|---|
| All files touched by TASK-AC-53445 walked; findings enumerated per file | ✅ §"Per-item findings" rows 1–5 |
| For each newly introduced callable: a runtime caller confirmed or the absence recorded | ✅ Five callables enumerated (`UNVERIFIABLE_CONFIDENCE_THRESHOLD`, `UnverifiableACWarning`, `classify_with_warnings`, `lint_plan_warnings`, `format_warning_summary`); each has a confirmed runtime caller outside tests and its defining module |
| For each newly introduced spec step: imperative reachability confirmed or the absence recorded | ✅ Step 10.5 is reachable via Step 8's imperative `Execute: python3 ~/.agentecflow/bin/generate-feature-yaml` call chain; confirmed at `feature-plan.md:2424` and `:2478-2481` |
| Review report filed at `docs/reviews/TASK-REV-AC53-reaudit-task-ac-53445.md` with verdict block | ✅ this file; verdict: **Clean** |
| If orphans found: remediation tasks filed and cross-linked | ✅ N/A — **no orphans found in TASK-AC-53445's delivery surface**. The one known orphan (R1 / Step 10.5) was already remediated by TASK-FIX-3C9D before this re-audit ran. No new remediation tasks filed. |

---

## Verdict

**Clean.** 0 additional orphan runners in TASK-AC-53445's delivery
surface beyond the one R1 orphan already closed by TASK-FIX-3C9D.

This matches the task's stated expectation ("expected finding is 'R1
was the only orphan' — but confirm, don't assume").

The cohort (jarvis / forge / study-tutor under TASK-COH-RUN1) is clear
to proceed on the TASK-AC-53445 surface specifically. TASK-COH-RUN1's
R1 pre-flight remains the correct gate — this re-audit does not
substitute for dynamic verification of the linter header against
each cohort repo's planner stdout.

---

## Cross-links

- Task under re-review: `tasks/completed/2026-04/TASK-AC-53445-assertable-ac-linter-feature-plan.md`
- Verification that motivated this re-audit: `.claude/reviews/TASK-FIX-7B2E-r1-wiring-verification.md`
- Remediation that closed the one known orphan: `tasks/completed/TASK-FIX-3C9D/TASK-FIX-3C9D-wire-ac-linter-into-feature-plan.md`
- Design-rule candidate (Graphiti): *"Design rule candidate: runner without producer anti-pattern"* (seeded from TASK-REV-4D190)
- Parent review: `docs/reviews/TASK-REV-4D190-jarvis-first-autobuild-review.md` §R1 / Addendum A
