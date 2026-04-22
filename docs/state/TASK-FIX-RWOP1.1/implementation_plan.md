# Implementation Plan — TASK-FIX-RWOP1.1

**Task:** Wire `/feature-plan` Step 11 (BDD scenario linking / `@task:` tagging) — remove runner-without-producer orphan
**Parent review:** [TASK-REV-RWOP1](../../reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md) Finding #1
**Date:** 2026-04-22
**Phase:** 2 (Implementation Planning)

## Path Decision: Path B (producer-script CLI shim)

The task brief offered two functionally-equivalent remediation paths. **Path B
chosen** for the following reasons:

1. **Robust against Claude-session variance.** TASK-FIX-7B2E §"Retro grep of
   FEAT-JARVIS-001" established that dynamic verification in a single Claude
   session is *not* sufficient evidence that Claude-as-runtime will activate
   prose-only steps reliably. Path A (rewriting Step 11 prose to `INVOKE
   Task(bdd-linker, ...)` and having the agent do the whole job) carries the
   same risk this task is trying to close. Path B's `Execute:` imperatives
   are interpreted by `bash`, not by Claude, so they fire deterministically.
2. **R1 precedent consistency.** TASK-FIX-3C9D applied the producer-script
   shape to the R1 AC linter (`generate_feature_yaml.py` Step 8). Using the
   same shape here means Coach + downstream auditors see one uniform
   "imperative `Execute:` → producer → callable" pattern across R1 and R2,
   making future runner-without-producer audits cheaper.
3. **Preserves the in-process orchestrator as a tested reference.** The
   existing `bdd_linking_phase.run_linking_phase` contract is well covered
   by `test_bdd_linking.py` (interactive / non-interactive / threshold /
   all-tagged idempotency / matcher-errors). Path B keeps it intact and
   reuses its primitives (`discover_feature_file`, `parse_matcher_response`)
   inside the new CLI shim — so the existing test suite continues to
   exercise the same code paths.

## Files

### Created

| Path | LOC | Purpose |
|---|---:|---|
| `installer/core/commands/lib/feature_plan_bdd_link.py` | ~430 | Path B producer script (`prepare`/`apply` subcommands) |
| `tests/integration/feature_plan/test_bdd_linking_end_to_end.py` | ~430 | End-to-end test driving the script via subprocess |
| `docs/state/TASK-FIX-RWOP1.1/implementation_plan.md` | this file | Phase 2 design capture |
| `.claude/reviews/TASK-FIX-RWOP1.1-bdd-linking-verification.md` | ~150 | Dynamic verification capture |

### Modified

| Path | Change |
|---|---|
| `installer/core/commands/feature-plan.md` | Step 11 prose rewritten: drops the `from ... import run_linking_phase` preamble + matcher-callback Python block; replaces with two `Execute:` imperatives bracketing one `INVOKE Task(bdd-linker, ...)` invocation |
| `installer/core/commands/lib/bdd_linking_phase.py` | Module docstring updated with a `.. note::` block flagging the orchestrator as the in-process reference implementation, with production callsite pointer to `feature_plan_bdd_link.py` |
| `installer/core/commands/bin-entries.txt` | New manifest entry for `feature_plan_bdd_link.py` so install.sh symlinks it as `~/.agentecflow/bin/feature-plan-bdd-link` |
| `tasks/in_progress/TASK-FIX-RWOP1.1-...md` (this task) | Frontmatter status: backlog → in_progress |

### Out of scope (explicitly per task brief)

- Refactoring `bdd-linker` matching heuristics — they are tested and stable.
- Changes to `bdd_linker.apply_mapping` internals.
- Changing the `.feature`-file output format or `@task:` tag convention.
- Retroactively tagging cohort features (forge, study-tutor) — that's
  TASK-COH-RUN1's pre-flight step.
- Wiring Step 11 into `--quiet` / `--no-interactive` flag semantics beyond
  what the existing prose specifies (i.e. interactive review via the rich
  table is dropped from the production path; it remains in the in-process
  orchestrator's contract for tests).

## External dependencies

None. Reuses existing libraries:

- `installer.core.commands.lib.bdd_linker` (parsing + atomic rewrite)
- `installer.core.commands.lib.bdd_linking_phase` (`discover_feature_file`,
  `parse_matcher_response`, `MatcherResponseError`)
- `pyyaml` (already a project dependency; used by `generate_feature_yaml.py`)

## Estimated effort

- Duration: ~2 hours (script ~30 min, prose rewrite ~30 min, tests ~45 min,
  verification + Graphiti note ~15 min).
- LOC: ~860 (~430 script + ~430 test).

## Implementation phases

1. Create the producer script with `prepare`/`apply` subcommands; reuse
   existing primitives.
2. Add the manifest entry so `install.sh` symlinks the script.
3. Rewrite Step 11 prose to the `Execute:` + `INVOKE Task(...)` shape.
4. Update `bdd_linking_phase.py` docstring to redirect future readers to
   the production entry-point.
5. Write the end-to-end test driving the script via subprocess; cover
   ready / silent-skip paths / matcher-error exit codes / round-trip
   idempotency.
6. Run all named regression suites; fix any breakage.
7. Capture dynamic verification against a prose-AC fixture; record at
   `.claude/reviews/`.
8. Add Graphiti note to `guardkit__project_decisions`.

## Risk mitigations

| Risk | Mitigation |
|---|---|
| New script silently masks `bdd-linker` agent failures | `apply` exits with code **2** on `MatcherResponseError` (distinct from generic input errors at code 1), so feature-plan.md prose can branch on "matcher returned garbage; offer a retry" specifically. |
| Acceptance criteria not surfaced to matcher | `prepare` reads each task's markdown file (resolved via the feature YAML's `file_path`) and extracts the `## Acceptance Criteria` bullet block. Verified end-to-end in `TestPrepareReady::test_request_includes_acceptance_criteria_from_task_md`. |
| Regression in existing in-process orchestrator behaviour | All 33 `test_bdd_linking.py` tests + 14 `test_bdd_linker.py` tests + adjacent suites kept passing (no signature changes; only docstring update). |
| Step 11 prose still allows the old "Python import" pattern | Rewrote the entire Step 11 block to remove the import-and-callback prose; added an explicit "Do NOT do this" non-goal calling out the original failure mode by name. |

## Acceptance-criteria mapping

| AC | Evidence |
|---|---|
| Path chosen + rationale captured in implementation_plan.md Phase 2 | This file's "Path Decision" section. |
| `run_linking_phase` or replacement has at least one non-test caller | `grep -rn "run_linking_phase\|feature_plan_bdd_link" --include="*.py" | grep -v "test_\|/tests/\|bdd_linking_phase.py:"` returns 6 matches in `installer/core/commands/lib/feature_plan_bdd_link.py`. |
| Step 11 reachable from the main execution trace | `feature-plan.md` Step 11 now uses `Execute: python3 ~/.agentecflow/bin/feature-plan-bdd-link prepare ...` + `INVOKE Task(bdd-linker, ...)` + `Execute: ... apply ...`; no Python import-and-callback prose remains. |
| End-to-end test at `tests/integration/feature_plan/test_bdd_linking_end_to_end.py` | 11 tests, 11 passing; covers ready/skip/error/round-trip; asserts `@task:` tags appear in rewritten file. |
| Dynamic verification captured | `.claude/reviews/TASK-FIX-RWOP1.1-bdd-linking-verification.md`. |
| Pre-existing 33/33 green test baseline maintained | `test_bdd_linking.py` (27/27), `test_criteria_classifier.py` (27/27), `test_ac_linter_warning_flow.py` (7/7), `test_bdd_linker.py` (34/34), `test_bdd_oracle_nudge.py` (9/9), `test_smoke_gates_nudge.py` (14/14), `test_generate_feature_yaml_linter.py` (4/4) all passing. |
| Graphiti note added to `guardkit__project_decisions` | Added via `mcp__graphiti__add_memory` (UUID recorded in verification report). |
