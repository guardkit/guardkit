# Implementation Guide: AutoBuild FEAT-PEBR Failure-Recovery

## Quick Reference

- **Waves**: 2
- **Parallelism**: Wave 1 has 4 disjoint-file subtasks → all run in
  parallel Conductor workspaces. Wave 2 has 2 subtasks that rebase
  on Wave 1 output (shared-file dependencies).
- **Sibling task in forge**: TASK-FRR-PEB-FM-001 runs concurrently
  in the **forge** repo and is independent of the GuardKit waves —
  it can land first as a workaround.
- **Testing depth**: `default-by-complexity`:
  - Complexity 2 → minimal (compile + smoke)
  - Complexity 3-4 → standard (≥80% coverage on changed lines + arch
    review)
  - Complexity 5-6 → standard/strict (add focused regression tests
    against the FEAT-PEBR fixture)

## Wave 1 — Parallel, disjoint files

Each of these can be started in its own Conductor workspace without
rebase:

### W1-1 · TASK-GK-AC-001 — Don't flag bare basenames in AC scanner ★ P0 ★

- Workspace: `autobuild-feat-pebr-failure-recovery-w1-1`
- Command: `/task-work TASK-GK-AC-001`
- Touches:
  - `guardkit/orchestrator/agent_invoker.py` (`_scan_ac_for_missing_paths`,
    lines 6028-6094 + caller at 6150)
  - `tests/orchestrator/test_agent_invoker.py`
  - `tests/fixtures/feat_pebr_worktree/` (new fixture)
- Gate: regression test against the FEAT-PEBR worktree fixture
  asserts `_compute_plan_audit_verdict(...)` returns
  `status != "violation"` for AC text containing
  `pipeline_consumer.py` (basename) when the file exists at
  `src/forge/adapters/nats/pipeline_consumer.py`.

### W1-2 · TASK-GK-CR-001 — Populate requirements on Coach gate-fail ★ P0 ★

- Workspace: `autobuild-feat-pebr-failure-recovery-w1-2`
- Command: `/task-work TASK-GK-CR-001`
- Touches:
  - `guardkit/orchestrator/quality_gates/coach_validator.py`
    (`_feedback_from_gates` and 5 sister return sites at
    lines 1080-1086, 1378, 1406, 1453, 1482, 1540)
  - `tests/quality_gates/test_coach_validator.py`
- **Critical regression guard**: do NOT promote `decision` from
  `feedback` to `approve` based on requirements alone.
  `all_gates_passed` remains the sole gate on `decision`.
- Gate: a fixture replaying the FEAT-PEBR turn-1 task_work_results.json
  through Coach produces `criteria_met=6, decision="feedback"`.

### W1-3 · TASK-GK-PA-001 — Plan-audit modify-vs-create

- Workspace: `autobuild-feat-pebr-failure-recovery-w1-3`
- Command: `/task-work TASK-GK-PA-001`
- Touches:
  - `guardkit/installer/core/commands/lib/plan_audit.py`
    (`_scan_modified_files` line 210+, `_compare_files`
    lines 420-458)
  - `guardkit/orchestrator/agent_invoker.py:_compute_plan_audit_verdict`
    (around line 6096) — surfaces new modify-axis fields
  - `guardkit/orchestrator/quality_gates/coach_validator.py:5320-5380`
    — extends feedback assembly to mention modify-axis discrepancies
  - `tests/installer/test_plan_audit.py`
- ⚠️ **File overlap with W1-1 and W1-2**: this task touches
  `agent_invoker.py:_compute_plan_audit_verdict` (line 6096) and
  `coach_validator.py:_feedback_from_gates` plan_audit branch
  (lines 5320-5380). These are **disjoint regions** from W1-1
  (line 6028) and W1-2 (line 1080), but Conductor will detect file
  overlap. Either:
  - Land W1-1 and W1-2 first, then W1-3 rebases (treat as Wave 2 in
    Conductor's eyes), OR
  - Coordinate manually via small targeted edits per region.
- Gate: a task with `## Files to Modify: pipeline_consumer.py` and
  a Player that modifies that file passes; same task with a Player
  that doesn't modify it produces a medium-severity discrepancy.

### W1-4 · TASK-GK-PROF-001 — Template-aware phase-3 specialist resolution

- Workspace: `autobuild-feat-pebr-failure-recovery-w1-4`
- Command: `/task-work TASK-GK-PROF-001`
- Touches:
  - Quality-gate profile config (search for the literal
    `python-api-specialist`)
  - `guardkit/orchestrator/quality_gates/` (specialist-resolution
    helper, location TBD by author)
  - `tests/quality_gates/test_profile_resolution.py` (likely new file)
- Gate: replaying FEAT-PEBR turn-1 against the langchain-deepagents
  template produces no advisory or names a langchain specialist.

## Wave 2 — Parallel, rebase Wave 1

### W2-1 · TASK-GK-FB-001 — Operator-feedback severity ordering

- Workspace: `autobuild-feat-pebr-failure-recovery-w2-1`
- Command: `/task-work TASK-GK-FB-001`
- Depends on: TASK-GK-CR-001 (Wave 1)
- Touches:
  - `guardkit/orchestrator/autobuild.py:3127-3129` (preferred —
    smaller diff)
  - OR `guardkit/orchestrator/quality_gates/coach_validator.py:1058-1069`
    (alternative — reverses prepend)
  - `tests/orchestrator/test_autobuild.py` (or wherever the summary
    builder is tested)
- Gate: replaying FEAT-PEBR turn-1 Coach output produces an operator
  summary containing `"Plan audit detected high-severity"` (not the
  advisory).

### W2-2 · TASK-GK-DOC-001 — Doc-level counter exclusion

- Workspace: `autobuild-feat-pebr-failure-recovery-w2-2`
- Command: `/task-work TASK-GK-DOC-001`
- Depends on: TASK-GK-AC-001 (Wave 1)
- Implementation mode: `direct` (no full task-work loop — change is
  mechanical)
- Touches:
  - `guardkit/orchestrator/agent_invoker.py:6598-6649`
    (`_validate_file_count_constraint`) and the caller around
    line 6358 / 6422
  - `tests/orchestrator/test_agent_invoker.py`
- Gate: FEAT-PEBR turn-1 fixture (4 files in `files_created`) does
  not emit the doc-level warning.

## Wave dependency graph

```
Wave 1 (parallel):                    Wave 2 (rebase):
                                      ┌──────────────────────────┐
  ┌──W1-1 (GK-AC) ───────────────┐    │  ★ Conductor parallel ★  │
  │  agent_invoker.py:6028        ├──→│ W2-2 (GK-DOC)            │
  └───────────────────────────────┘    │  agent_invoker.py:6598   │
                                       └──────────────────────────┘
  ┌──W1-2 (GK-CR) ───────────────┐    ┌──────────────────────────┐
  │  coach_validator.py:1080      ├──→│ W2-1 (GK-FB)             │
  └───────────────────────────────┘    │  coach_validator.py +    │
                                       │  autobuild.py            │
                                       └──────────────────────────┘
  ┌──W1-3 (GK-PA) ───────────────┐
  │  plan_audit.py + agent_invoker├──  (independent of Wave 2)
  │  + coach_validator (regions) │
  └───────────────────────────────┘

  ┌──W1-4 (GK-PROF) ─────────────┐
  │  profile config              ├──  (independent of Wave 2)
  └───────────────────────────────┘
```

## Sibling-repo sequencing

The forge-repo workaround
[TASK-FRR-PEB-FM-001](../../../../forge/tasks/backlog/forge-autobuild-runner-pipeline-emitter-bridge/TASK-FRR-PEB-FM-001-add-explicit-files-sections-and-reclassify.md)
runs **concurrently** with these waves. It is independent of all
GuardKit changes and works against the current GuardKit code. If
landed alone:

- TASK-FRR-PEB-FM-001 unblocks FEAT-PEBR's `--resume` immediately
  (PlanAuditor consumes the explicit plan, no AC-fallback fires).
- The GuardKit fixes still ship, but as planned-not-emergency work.

If landed alongside W1-1 / W1-2:

- Belt-and-braces. The FRR-PEB tasks have correct frontmatter for
  future runs, and any *other* template that hits the same
  basename-scanner bug also benefits from the GuardKit fix.

Recommended: land both. The forge-side change is small (~30 min) and
prevents the failure mode from recurring on FRR-PEB-002 through 014.

## Rollback / Risk Management

- **TASK-GK-AC-001** is low-risk if implemented as Option (a) (opt-in
  parameter): the audit path opts out of basename flagging, the
  synthetic-report path keeps current behaviour. Reviewers should
  verify the synthetic-report path is exercised by an existing test
  that didn't change.
- **TASK-GK-CR-001** is the riskiest change. Critical guard: the new
  requirements-on-fail population must NOT change Coach `decision`
  or `all_gates_passed`. Add an explicit assertion:

  ```python
  assert (
      gates_status.all_gates_passed
      or coach_result.decision == "feedback"
  )
  ```

  in the new code path. If the assertion ever fires in CI, revert the
  change.
- **TASK-GK-PA-001** changes a soft warning (today's empty-stub) to
  a real comparison. Severity tiers are deliberately calibrated:
  missing-modify is `medium` (not `high`) so it does not gate the
  loop the way missing-create does. If post-deploy data shows too
  many false positives, downgrade further to `low` or gate behind a
  config flag `plan_audit.modify_axis_enabled: false (default)`
  with explicit opt-in for hardening runs.
- **TASK-GK-FB-001** is operator-experience only — does not change
  delivered Player feedback. Risk: low.
- **TASK-GK-DOC-001** is a path-prefix filter. Risk: low —
  exclusions are conservative and can be tightened later.
- **TASK-GK-PROF-001** could break templates that rely on the literal
  `python-api-specialist`. Provide fallback chain:
  template-discovered → profile-default → `python-api-specialist`.
  If unsure of the existing-template inventory, run a grep across
  `guardkit/installer/core/templates/*/` for this literal before
  landing.

## Completion

When all six subtasks are in `completed/`:

```bash
# In the forge repo:
cd /home/richardwoollcott/Projects/appmilla_github/forge
guardkit autobuild feature FEAT-PEBR --resume
# Expect: Wave 1 / TASK-FRR-PEB-001 turns to APPROVED in 1 turn.

/task-complete TASK-REV-PEBR-001
```

…and update `TASK-REV-PEBR-001` from `review_complete` → `completed`,
then capture feature-level outcome to Graphiti under
`guardkit__task_outcomes` (referencing TASK-REV-PEBR-001 as the
parent review). The completion episode should cite the
post-fix `--resume` run as evidence the chain is broken.
