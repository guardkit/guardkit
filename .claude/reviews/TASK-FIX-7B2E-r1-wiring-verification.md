# TASK-FIX-7B2E — R1 (assertable-AC linter) wiring verification

**Task:** TASK-FIX-7B2E (wave 1 of FEAT-R2GP)
**Parent review:** TASK-REV-4D190 §R1
**Predecessor:** TASK-AC-53445 (landed 2026-04-21, 33/33 tests passing)
**Date:** 2026-04-22
**Status:** Static verification complete · Dynamic verification complete ·
**Revised 2026-04-22 after retro-grep**: R1 is **non-deterministically wired**
(fires in some Claude sessions, not others — single positive dynamic test is
insufficient evidence on its own). See §"Verdict (inverted after dynamic run)"
and §"Retro grep of FEAT-JARVIS-001" below. TASK-FIX-3C9D restored to
priority `high`; the structural fix is back on the critical path for
TASK-COH-RUN1.

---

## Verdict (inverted after dynamic run)

> **Note (revision 3, 2026-04-22):** The "wired (behaviourally)" framing
> below stands as a description of the single positive dynamic run, but
> it is superseded as the *overall* verdict. Once §"Retro grep of
> FEAT-JARVIS-001" is read alongside the dynamic run, the honest
> combined verdict is **"non-deterministically wired"** — not "wired".
> A single positive dynamic test is insufficient to conclude the runner
> is active; Claude-as-runtime interprets descriptive prose
> non-deterministically across sessions. This is the methodological
> lesson captured in the sibling Graphiti episode
> *"Verification methodology: single positive dynamic test is insufficient
> for Claude-as-runtime features."* The forward-looking claim in
> §"Status / state transitions after this result" that TASK-FIX-3C9D
> drops to `medium` is **reverted**: TASK-FIX-3C9D is back at `high`
> priority and now explicitly blocks TASK-COH-RUN1. TASK-COH-RUN1's R1
> pre-flight additionally requires an in-situ grep of each cohort
> member's `/feature-plan` stdout for `AC-quality review:` — a
> once-wired, always-wired assumption is not safe under Claude-as-runtime.

**R1 is wired — but via Claude-as-runtime interpretation of the
descriptive Step 10.5 prose, not via an imperative execution instruction.**
The static analysis was correct about the spec's structure (no
`Execute:` line, Step 10.5 absent from execution traces) but wrong
about the behavioural outcome under the Claude-follows-markdown runtime:
the descriptive prose is sufficient instruction for Claude to invoke
`lint_plan_warnings` as a tool call at the right moment.

Dynamic run on 2026-04-22 emitted the exact
`AC-quality review: 25 unverifiable acceptance criteria detected
(warn-mode, non-blocking).` header with **6 / 6 fixture prose ACs
firing** — matching the fixture's own prediction and exceeding
TASK-REV-4D012's ≥3-of-6 threshold.

The spec is therefore **structurally fragile** (no imperative, no trace
reference, no producer script) but **behaviourally functional** under
the current runtime. Two things follow:

- **TASK-FIX-7B2E is closed as *wired*.** The remediation task
  TASK-FIX-3C9D is still worth doing — it hardens the wiring against a
  future runtime that only honours imperatives — but it no longer
  blocks the forge / study-tutor cohort runs.
- **R1 activation is non-deterministic across runs.** The same spec
  text did not produce the AC-quality header on FEAT-JARVIS-001
  (2026-04-21, ~10 hours after TASK-AC-53445 landed). See §"Retro grep
  of FEAT-JARVIS-001" below.

This is a close cousin of the "runner without producer" failure mode
TASK-REV-4D190 identified for R2 — the spec-to-runtime gap is still
there — but with Claude-as-runtime reading the descriptive side, the
gap narrows to "works today, may silently stop working under a stricter
reader." See §"Architectural pattern" below.

---

## Static evidence

| # | Indicator | Location | Result |
|---|---|---|---|
| 1 | `ac_linter.py` module exists | `guardkit/orchestrator/quality_gates/ac_linter.py` | ✅ 83 lines, defines `lint_plan_warnings` and `format_warning_summary` |
| 2 | `classify_with_warnings()` exists | `guardkit/orchestrator/quality_gates/criteria_classifier.py:250` | ✅ Returns `(ClassificationResult, List[UnverifiableACWarning])` |
| 3 | `UNVERIFIABLE_CONFIDENCE_THRESHOLD` constant | `criteria_classifier.py` | ✅ Value `0.6` |
| 4 | Step 10.5 documented in command spec | `installer/core/commands/feature-plan.md:2241-2315` | ✅ Descriptive prose only |
| 5 | **Step 10.5 included in execution trace** | `installer/core/commands/feature-plan.md:2370-2395` (Flag-Only), `:2397-2461` (Structured) | ❌ **Absent.** Trace: 1→2→3→4→5→6→7→8→8.5→9. No step 10 or 10.5. |
| 6 | **Imperative `Execute:` or `Run:` line for linter** | Step 10.5 body, lines 2255-2268 | ❌ Only descriptive prose: *"the post-step collects…"*, *"Calls `lint_plan_warnings(tasks)`"* |
| 7 | **"REMEMBER: Your job is to…" duty list** | `feature-plan.md:2332-2340` | ❌ Lists 6 duties; AC linter not among them |
| 8 | **Runtime Python caller of `lint_plan_warnings`** outside tests/linter | `grep -rn "lint_plan_warnings\|ac_linter" --include="*.py" | grep -v "test_\|/tests/\|ac_linter.py:"` | ❌ **Zero matches.** |
| 9 | Installed script invoking linter | `~/.agentecflow/bin/` | ❌ No match for `generate-feature` or `ac_linter` |
| 10 | Integration test calls linter via `/feature-plan` | `tests/integration/feature_plan/test_ac_linter_warning_flow.py:16-105` | ❌ Test imports and calls `lint_plan_warnings(mock_feature_plan_output)` **directly** against a constructed list of task dicts. It does not drive `/feature-plan` end-to-end. The 33/33 green suite is therefore consistent with "not wired". |

### Direct comparison — Step 8 (wired) vs Step 10.5 (not wired)

**Step 8** (`feature-plan.md:2429-2440`):
```
8. Generate structured feature file (default behavior):
   - Execute: python3 ~/.agentecflow/bin/generate-feature-yaml \
       --name "implement OAuth2" \
       ...
```
This is imperative — a literal shell command Claude is instructed to run.

**Step 10.5** (`feature-plan.md:2255-2268`):
```
How it works:
1. After Step 10 writes task markdown and the structured YAML, the
   post-step collects each generated task's `id` + `acceptance_criteria`.
2. Calls
   `guardkit.orchestrator.quality_gates.ac_linter.lint_plan_warnings(tasks)`,
   which delegates per task to
   `criteria_classifier.classify_with_warnings()`.
3. Any criterion classified at confidence <
   `UNVERIFIABLE_CONFIDENCE_THRESHOLD` (currently 0.6) produces a
   single `UnverifiableACWarning` ...
```
This is descriptive — narrates what the post-step *does*, but never
tells the executor (Claude, or a shell script) to invoke it.

### Additional signal — "Step 10" itself is missing

Step 10.5 self-references a "Step 10" and "Step 11" (completion summary).
Neither exists in the spec. The entire Step 10/10.5/11 block appears to
have been appended to the spec without being integrated into the main
execution flow. This further supports "unintentional omission" over
"deferred-by-design".

---

## Architectural pattern — "runner without producer"

This is the same failure mode TASK-REV-4D190 Addendum A captured for R2:
a verifier whose runtime-side is described but not plumbed. R1 and R2
back-to-back exhibit the pattern, in slightly different shapes:

- **R2 (TASK-REV-4D190):** `/feature-spec` → `/feature-plan` → `/task-work`
  describe a cross-command verifier, no command actually invokes it.
- **R1 (this task):** `/feature-plan` alone describes the linter post-step
  in Step 10.5, no imperative instruction in the same file invokes it.

The candidate design rule is: *every verifier documented in a command spec
must have either (a) an imperative `Execute: …` line in that spec's execution
trace, or (b) a producer in an upstream script that the spec does invoke.*
A verifier described only in prose is, under the Claude-follows-markdown
runtime, a documented-only verifier.

This observation is relevant both to the R1 remediation (TASK-FIX-3C9D,
filed alongside this report) and to a follow-up re-review of TASK-AC-53445:
at delivery time the same pattern could have been caught had there been
an explicit "Step 10.5 is reachable from the execution trace" acceptance
criterion.

See also Graphiti episode *"Design rule candidate: runner without
producer anti-pattern"* (seeded from TASK-REV-4D190).

---

## Against the task ACs

| AC | Status |
|---|---|
| A reproducible prose-AC fixture exists | ✅ `tests/fixtures/r1-verification/prose-ac-spec.md` — six ACs covering PEX-014..020 bug classes |
| `/feature-plan` invoked against the fixture; output captured | ✅ **Run captured** at `docs/reviews/improve-coach-verification/test-feature-plan.md`. Invocation: `/feature-plan "Build a small internal ingestion tool..." --context tests/fixtures/r1-verification/prose-ac-spec.md` |
| Evidence documented for each of the PEX-014..020 bug classes | ✅ 6 / 6 fixture ACs fired. See §"Dynamic verification result" table. |
| Finding recorded in `.claude/reviews/TASK-FIX-7B2E-r1-wiring-verification.md`: wired / not wired / partially wired | ✅ **This file.** Final verdict: **wired (behaviourally)** — see §"Verdict (inverted after dynamic run)" at the top. |
| If not wired, remediation task filed and linked to TASK-AC-53445 | ✅ **TASK-FIX-3C9D** filed at `tasks/backlog/r2-pipeline-closure-and-forge-cohort/TASK-FIX-3C9D-wire-ac-linter-into-feature-plan.md`. **Priority: `high`** (restored 2026-04-22 after retro-grep showed R1 did not fire on FEAT-JARVIS-001 — activation is session-dependent, structural fix is back on the critical path for COH-RUN1). See `priority_history` in TASK-FIX-3C9D for the full flip sequence. |

---

## Dynamic verification repro

**Fixture:** `tests/fixtures/r1-verification/prose-ac-spec.md`
(6 deliberately prose ACs covering the PEX-014..020 bug classes;
each one is predicted in the fixture's own table to trip the
`UNVERIFIABLE_CONFIDENCE_THRESHOLD = 0.6` gate.)

**Invocation (run from repo root):**

```
/feature-plan "Build a small internal ingestion tool that accepts uploaded CSV files, writes them to a staging area, emits schema metadata, and exposes a read endpoint. The tool should be robust to malformed inputs and should not regress behaviour for existing callers." --context tests/fixtures/r1-verification/prose-ac-spec.md
```

**What to look for in the output:**

Grep the transcript for:
```
AC-quality review:
```
(The exact header emitted by `format_warning_summary()` per
`feature-plan.md:2299`.)

**Outcome interpretation:**

| Observation | Interpretation |
|---|---|
| Header appears; warnings listed for ≥3 of the 6 fixture ACs | R1 is wired. Static analysis is wrong — investigate the reconciling code path. |
| Header does not appear | R1 is not wired. Static analysis confirmed end-to-end. Proceed with TASK-FIX-3C9D. |
| Header appears but flags < 3 of 6 | R1 is wired but classifier under-firing — separate remediation needed against `criteria_classifier.py` patterns, *not* the wiring. |

Paste the captured output as a new §"Dynamic verification result" below,
and move TASK-FIX-7B2E to `in_review` once the run is captured.

---

## Path-deviation note

Task AC specifies `.claude/reviews/TASK-FIX-7B2E-r1-wiring-verification.md`.
That is the path written. Earlier draft proposed relocating to
`docs/reviews/` on the (incorrect) basis that TASK-REV-4D190 lives there;
that convention is for `/task-review` outputs, not verification-task
outputs. Correction accepted; AC-specified path honoured.

---

## Dynamic verification result

**Date:** 2026-04-22
**Transcript:** `docs/reviews/improve-coach-verification/test-feature-plan.md`
**Runtime:** Claude Opus 4.7 (1M context), session-driven `/feature-plan`

**Observed outcome: R1 IS wired (via Claude-as-runtime interpretation).**

The invocation in §"Dynamic verification repro" produced the exact
header predicted by the fixture:

```
AC-quality review: 25 unverifiable acceptance criteria detected
(warn-mode, non-blocking).
```

All six fixture prose ACs triggered warnings under their owning subtasks:

| Fixture AC (from `tests/fixtures/r1-verification/prose-ac-spec.md`) | Warned? | Owning task in generated plan |
|---|:-:|---|
| (PEX-014) schema metadata is correct …reflects …faithfully | ✅ | TASK-CSV-003 |
| (PEX-015) staging-area writer behaves semantically the same… | ✅ | TASK-CSV-002, TASK-CSV-006 |
| (PEX-016) file paths handled safely and sanitised appropriately | ✅ | TASK-CSV-004 |
| (PEX-017) handle malformed CSV inputs gracefully | ✅ | TASK-CSV-006 |
| (PEX-018) backward-compatible defaults ensure no breakage | ✅ | TASK-CSV-005 |
| (PEX-019/020) performance is reasonable …observable …appropriately | ✅ | TASK-CSV-006 |

**6 / 6 fixture ACs fired** — matches the fixture's own static
prediction (it predicted "all 6 warn"), and comfortably clears
TASK-REV-4D012's R1 acceptance criterion of ≥3 of 6.

Aggregate: **25 UnverifiableACWarning instances** across the six
generated subtasks, including the fixture ACs plus other prose-style
criteria (e.g., "All modified files pass project-configured lint/format
checks with zero errors") that also fall through the classifier's
low-confidence fallback branch.

### What "wired via Claude-as-runtime interpretation" means here

Step 10.5 of `installer/core/commands/feature-plan.md` contains:
- no `Execute: …` line (static evidence #6)
- no mention in the execution traces (static evidence #5)
- no imperative callsite in `~/.agentecflow/bin/` or
  `generate_feature_yaml.py` (static evidence #8, #9)

The linter nonetheless ran because the spec's descriptive prose ("the
post-step collects each generated task's `id` + `acceptance_criteria`…
Calls `lint_plan_warnings(tasks)`…") was sufficient instruction for
Claude to execute the equivalent Python inline at the correct point in
the flow (between feature-YAML generation and the completion summary).
The linter module was imported, the tasks' frontmatter + AC sections
were loaded, `lint_plan_warnings(tasks)` was called, and
`format_warning_summary(warnings)` was printed to planner output.

This behaviour is **not guaranteed across runs**. See next section.

### Retro grep of FEAT-JARVIS-001

At TASK-REV-4D190 review time the activation check was "no warnings
present in task frontmatter or plan YAML." The actual activation
signal — the `AC-quality review:` header — lives in `/feature-plan`
*planner output*, not in persisted artefacts. Re-grepping jarvis:

| File | `AC-quality review:` matches |
|------|:-:|
| `jarvis/docs/history/feature-plan-FEAT-JARVIS-001-history.md` (the captured plan transcript, 515 lines) | **0** |
| `jarvis/docs/reviews/phase-1/autobuild-FEAT-JARVIS-001.md` (downstream autobuild log, 2,081 lines) | 0 (expected — downstream of planning) |
| `jarvis/.guardkit/autobuild/FEAT-JARVIS-001/` tree | 0 |

Timing: TASK-AC-53445 landed 2026-04-21 ~12:19; jarvis `/feature-plan`
history was captured at 2026-04-21 ~22:33 — **~10 hours after the spec
was updated**. So R1 existed in the spec at jarvis plan time and still
did not activate.

**Conclusion:** R1 activation is non-deterministic across Claude-as-
runtime invocations. Today's run fired; the jarvis run did not. This
upgrades TASK-FIX-3C9D from "harden the wiring" (a pure hygiene
improvement) to "make activation deterministic" (a correctness
improvement) — but with the priority demotion noted below, because the
linter does at least fire some of the time under the current spec.

### Status / state transitions after this result

- **TASK-FIX-7B2E** → `in_review`. Verdict captured, dynamic evidence
  recorded, fixture preserved for future re-runs.
- **TASK-FIX-3C9D** → remains `backlog`, priority **`high` → `medium` →
  `high` (restored 2026-04-22)**. The medium flip was based on the
  single positive dynamic test; the retro-grep of FEAT-JARVIS-001 shows
  R1 did not fire there — activation is session-dependent under Claude-
  as-runtime. The structural fix is therefore back on the critical path
  for COH-RUN1 to have reliable R1 coverage, not a hygiene-only
  improvement. TASK-COH-RUN1's `depends_on` now includes TASK-FIX-3C9D
  explicitly. See TASK-FIX-3C9D `priority_history` for the full flip
  sequence (high → medium → high, each with a reason).
- **Spec-hardening follow-up** (out of scope for this task): whether
  `feature-plan.md` Step 10.5 should be promoted to an imperative
  `Execute:` block, and whether the linter should be moved into
  `generate-feature-yaml` (Option B in TASK-FIX-3C9D). Either change
  would convert "behaviourally functional but structurally fragile"
  into "behaviourally and structurally functional."

### Caveats on this conclusion

- Sample size is one positive run and one negative historical run. A
  handful of additional runs (different feature descriptions, different
  Claude sessions) would tighten the non-determinism claim.
- The negative historical run (jarvis) may have had all-assertable ACs,
  in which case "no header" is the correct *quiet* outcome, not a
  non-activation. The fixture used today is specifically engineered to
  force non-quietness; the jarvis feature was not. This doesn't change
  the conclusion that the activation signal was absent, but it weakens
  the "non-deterministic" framing into "at-least-fires-sometimes,
  cannot-guarantee-fires-always."
- The captured transcript at
  `docs/reviews/improve-coach-verification/test-feature-plan.md` is a
  session-log dump, not a structured report — further re-runs should
  capture planner stdout only (no agent UI chrome) to make retroactive
  grepping easier.
