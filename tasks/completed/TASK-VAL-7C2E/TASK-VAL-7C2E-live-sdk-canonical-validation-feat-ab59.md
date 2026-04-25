---
id: TASK-VAL-7C2E
title: "Live-SDK canonical validation of FEAT-AB59 orchestrator-side Phase 4/5 wiring"
status: completed
created: 2026-04-25T12:00:00Z
updated: 2026-04-25T12:35:00Z
completed: 2026-04-25T12:35:00Z
completed_location: tasks/completed/TASK-VAL-7C2E/
previous_state: in_progress
state_transition_reason: "Closed for completeness per user direction; live-run AC unsatisfied"
priority: critical
task_type: validation
parent_feature: FEAT-AB59
parent_review: TASK-REV-45750
implementation_mode: task-work
complexity: 3
tags:
  - autobuild
  - validation
  - live-sdk
  - FEAT-AB59
  - critical-path
  - F4A1-followup
related_to:
  - TASK-REV-45750
  - TASK-REV-119C1
  - TASK-DIAG-F4A2
  - TASK-OSI-006
  - TASK-OSI-007
test_results:
  status: not_executed
  coverage: null
  last_run: null
acceptance_criteria_outcomes:
  AC-001: satisfied
  AC-002: satisfied
  AC-003: satisfied (structural; idempotency proven against synthetic artefacts)
  AC-004: not_satisfied (live run attempted, failed before producing artefacts)
  AC-005: not_applicable (no verdict captured)
  AC-006: not_applicable (no signal-level fail to map)
---

# Task: Live-SDK canonical validation of FEAT-AB59 orchestrator-side Phase 4/5 wiring

## Why this task exists

FEAT-AB59 (orchestrator-side specialist invocation) shipped seven OSI subtasks
that all pass their stub-SDK tests (31/31 in 0.16s). The post-implementation
review TASK-REV-45750 confirmed the wiring is structurally sound — every
boundary inside Python, every JSON contract, every dedup rule, every
direct-mode skip, every Phase 4/5 failure path is correct in code.

**What is NOT yet confirmed**: that a live `claude_agent_sdk.query` call,
made by `invoke_test_orchestrator` and `invoke_code_reviewer` against the
real Anthropic API, actually produces:

- an orchestrator-issued `test-orchestrator` SDK session,
- followed by an orchestrator-issued `code-reviewer` SDK session,
- a well-formed `specialist_results.json` with both phase blocks,
- a merged `task_work_results.json["agent_invocations_validation"]` with
  `status: "passed"` and `missing_phases: []`.

Three weeks of failed forge/jarvis runs (forge-run-3, forge-run-5,
jarvis-FEAT-002-run-2) showed zero specialist invocations and stalled on
`coach_agent_invocations_stall`. The user's explicit constraint:

> *"We cannot afford another failed live run without first proving the
> wiring is correct via a tighter validation loop."*

A forge or jarvis live run is hours of wall-clock and significant API
spend. This task is the cheap proxy: a single canonical task, ≤10 minutes,
with full debug preservation, that proves the live SDK accepts the new
runners' inputs and that the orchestrator-side Phase 4/5 sessions appear
in `messages.jsonl`.

## Description

Build a minimal canonical AutoBuild fixture and a small harness that runs
it and checks the three pass signals defined below. If all three pass, the
wiring is confirmed against the live SDK and forge/jarvis can be re-run
with confidence. If any signal fails, the captured `messages.jsonl` plus
the `task_work_results.json` artefacts pinpoint exactly which boundary
broke (per the boundary table in `docs/reviews/feat-ab59-validation/TASK-REV-45750-validation-report.md` §4)
without burning a forge run's worth of budget.

### Scope (in)

1. **Create one canonical AutoBuild task**:
   `tasks/backlog/TASK-AB59-CANON-add-helper.md` (or equivalent path —
   choose any non-clashing ID). Frontmatter:
   ```yaml
   ---
   id: TASK-<canonical-id>
   title: "FEAT-AB59 canonical: add_one helper"
   status: backlog
   priority: low
   task_type: feature
   complexity: 2
   autobuild:
     enabled: true
     max_turns: 2
     base_branch: main
     mode: standard
     sdk_timeout: 600
   ---
   ```
   Body specifies a single function, e.g.:
   ```python
   # src/feat_ab59_canon/helpers.py
   def add_one(n: int) -> int:
       return n + 1
   ```
   plus one acceptance test that exercises happy path + a negative case.
   Deliberately tiny — ≤30 LOC end-to-end — so AutoBuild can complete in
   one or two turns.

2. **Add a runner script**: `validation/feat-ab59/run_canonical.sh` (or
   `.py` — author's choice). Responsibilities:
   - Set `GUARDKIT_AUTOBUILD_PRESERVE_DEBUG=1` so TASK-DIAG-F4A2's
     instrumentation captures `messages.jsonl`, the rendered prompts, and
     the SDK message stream for each session.
   - Invoke `guardkit autobuild task TASK-<canonical-id>`.
   - On completion, parse three artefacts and emit a clear pass/fail
     verdict.

3. **Pass signals** (all three required):
   - **Signal A — orchestrator emitted both specialist sessions**:
     `messages.jsonl` contains at least one record where the agent role
     is `"test-orchestrator"` and at least one where it is
     `"code-reviewer"`, distinct from the Player session, and the
     test-orchestrator record precedes the code-reviewer record in time.
   - **Signal B — gate credited the phases**:
     `.guardkit/autobuild/TASK-<canonical-id>/task_work_results.json`
     contains
     `agent_invocations_validation.status == "passed"` and
     `missing_phases == []`.
   - **Signal C — specialist results well-formed**:
     `.guardkit/autobuild/TASK-<canonical-id>/specialist_results.json`
     exists and contains both `phase_4` and `phase_5` blocks with
     `status: "passed"`.

4. **Fail signals** (any one is a fail):
   - Zero `test-orchestrator` or `code-reviewer` records in
     `messages.jsonl`.
   - `agent_invocations_validation.status` is `"violation"` or
     `"validator_error"`, OR `missing_phases` is non-empty.
   - `specialist_results.json` absent, or any phase block has
     `status` other than `"passed"`.
   - Turn history shows `coach_agent_invocations_stall`.

5. **Re-runnable, idempotent**:
   - Cleanup script must remove any prior worktree at
     `.guardkit/worktrees/TASK-<canonical-id>/` and any prior autobuild
     artefacts at `.guardkit/autobuild/TASK-<canonical-id>/` before the
     run.
   - Multiple runs must produce identical pass/fail verdicts (no
     accumulating state).

### Scope (out)

- **Re-running forge-FEAT-FORGE-002 or jarvis-FEAT-J002.** Those happen
  AFTER this task confirms the wiring. This task is the gate before
  burning forge/jarvis budget.
- **Modifying any FEAT-AB59 code.** This is a validation harness, not a
  fix. If a fail signal fires, the follow-up is a separate fix task — not
  scope creep into this one.
- **Adding integration tests for the test-helper-drift concern** (§7-C1
  of the review report). That is a separate hardening task.
- **Re-running the OSI-007 stub-SDK suite.** Already passing; not the
  question this task answers.

### Acceptance criteria

- [ ] AC-001: A canonical AutoBuild task fixture exists at a backlog path
      with `autobuild.enabled: true`, `max_turns: 2`, and a deliverable
      ≤30 LOC.
- [ ] AC-002: A runner script exists at `validation/feat-ab59/` that
      sets `GUARDKIT_AUTOBUILD_PRESERVE_DEBUG=1`, invokes
      `guardkit autobuild task <id>`, and emits a clear PASS/FAIL
      verdict against the three signals.
- [ ] AC-003: The runner script implements the full cleanup-and-rerun
      cycle (removes prior worktree + autobuild dir before each run);
      two consecutive runs produce identical verdicts.
- [ ] AC-004: First run executes successfully end-to-end. Total
      wall-clock ≤10 minutes. Verdict is captured (PASS or FAIL) along
      with the path to the `messages.jsonl` for forensic inspection.
- [ ] AC-005: If verdict is **PASS**, this task's completion notes
      include the three artefact excerpts proving each signal:
      (a) two grep'd lines from `messages.jsonl` showing each
      orchestrator-issued session, (b) the
      `agent_invocations_validation` block JSON, (c) the
      `specialist_results.json` content.
- [ ] AC-006: If verdict is **FAIL**, this task's completion notes
      include: which signal fired, the root-cause boundary (mapped
      against TASK-REV-45750 §4 boundary table), and a
      separately-filed follow-up task ID for the actual fix. This
      task is then closed as **failed-validation**, not as completed.

## Implementation Notes

- **Reuse TASK-DIAG-F4A2 infrastructure**: the `GUARDKIT_AUTOBUILD_PRESERVE_DEBUG=1`
  environment variable triggers the existing preservation pipeline at
  `guardkit/orchestrator/sdk_debug.py`. Don't reinvent the
  message-capture mechanism — exercise it.
- **The canonical task should be deliberately boring**. It exists only
  to drive a complete Player → Phase 4 → Phase 5 → merge → Coach turn
  loop. The semantic content of the implementation is irrelevant. Pick
  the simplest possible single-file deliverable.
- **Don't accept "tests passed" as evidence on its own** — the Coach
  needs to **see** the orchestrator-issued specialist sessions in the
  message stream. The whole point of this validation is to confirm the
  message stream contains them, not just that the gate passed (which
  could pass for the wrong reason if the synthesised skipped records
  silently substitute).
- **Worktree under `.guardkit/worktrees/TASK-<canonical-id>/`** — same
  pattern AutoBuild already uses. Cleanup with
  `guardkit worktree cleanup TASK-<canonical-id>` between runs.
- **If the live run reveals a regression**: per the parent review,
  `messages.jsonl` plus the rendered prompts at
  `.guardkit/autobuild/<task>/sdk_debug/` are sufficient to triage. The
  follow-up fix task should be filed with the captured artefacts as
  primary evidence; it is NOT in scope for this task.

## Pass-signal verification recipes

For copy-paste evidence collection in AC-005:

```bash
# Signal A (test-orchestrator session)
grep -F '"role": "test-orchestrator"' .guardkit/autobuild/<id>/messages.jsonl | head -1

# Signal A (code-reviewer session)
grep -F '"role": "code-reviewer"' .guardkit/autobuild/<id>/messages.jsonl | head -1

# Signal B (gate credit)
jq '.agent_invocations_validation' .guardkit/autobuild/<id>/task_work_results.json

# Signal C (specialist results)
cat .guardkit/autobuild/<id>/specialist_results.json
```

The exact JSON path / field name in `messages.jsonl` should be confirmed
against the format `sdk_debug.py` actually emits — adjust the grep
accordingly during implementation.

## References

- Parent review (this task's reason to exist):
  `docs/reviews/feat-ab59-validation/TASK-REV-45750-validation-report.md` §10
- FEAT-AB59 architecture:
  `docs/reviews/orchestrator-side-specialist-invocation/TASK-REV-119C1-review-report.md`
- FEAT-AB59 implementation guide:
  `tasks/backlog/orchestrator-side-specialist-invocation/IMPLEMENTATION-GUIDE.md`
- Diagnostic preservation infrastructure:
  `guardkit/orchestrator/sdk_debug.py` (enabled by
  `GUARDKIT_AUTOBUILD_PRESERVE_DEBUG=1`, seeded by TASK-DIAG-F4A2)
- Wiring under test:
  `guardkit/orchestrator/autobuild.py:2625-2748` (TASK-OSI-006)
- Stub-SDK gate (passing — sibling, not this task):
  `tests/integration/test_autobuild_phase_4_5_orchestration.py`
- Refuted prompt-class fix lifecycle (proves this gate is needed):
  commits `7f8f14ba`, `86688fc6`, `a8789317` (TASK-FIX-7A08 reverted)

## Success criteria (one-line)

A live `claude_agent_sdk.query` call, made by `invoke_test_orchestrator`
on a canonical AutoBuild task, results in `messages.jsonl` recording an
orchestrator-issued `test-orchestrator` session followed by an
orchestrator-issued `code-reviewer` session, and the merged
`task_work_results.json` shows
`agent_invocations_validation.status == "passed"`. This is necessary AND
sufficient evidence that the FEAT-AB59 wiring works against the real SDK.

## Notes

- Priority `critical`: this task is the gate before re-running forge or
  jarvis. AutoBuild has been broken for weeks on those features.
- After this task completes (PASS), the next workstream is the
  forge-FEAT-FORGE-002 + jarvis-FEAT-J002 acceptance suite — a separate
  workstream not gated by this task's file but by its verdict.
- After this task completes (FAIL), the next workstream is the specific
  fix identified by the failure mode — separately filed.
- This task is the canonical exemplar of the "tighter validation loop"
  the user requested. If it pays off (cheaply confirms or refutes the
  fix), the pattern is reusable for future post-implementation reviews
  of large autobuild changes.

## Completion Notes (2026-04-25)

**Closed for completeness per user direction.** The live-run half of the
task did not succeed — the harness was built and structurally verified,
but the live `guardkit autobuild task TASK-AB59-CANON` invocation
attempted prior to completion failed before producing any autobuild
artefacts (worktree was created at `.guardkit/worktrees/TASK-AB59-CANON/`
at 12:15, `autobuild_state.turns: []`, no `task_work_results.json`,
no `specialist_results.json`, no `sdk_debug/` tree). This means the
four signals defined in `validation/feat-ab59/README.md` could not be
evaluated against any real run.

### What shipped

- `tasks/backlog/TASK-AB59-CANON-add-helper.md` — canonical AutoBuild
  fixture (`add_one(n)` deliverable, ≤30 LOC AC, `autobuild.enabled:
  true`, `max_turns: 2`, `mode: standard`, `sdk_timeout: 600`).
  AC-001 satisfied.
- `validation/feat-ab59/run_canonical.sh` — cleanup + run + verify
  driver. Exports `GUARDKIT_AUTOBUILD_PRESERVE_DEBUG=1` per
  TASK-DIAG-F4A2 contract. Removes prior worktree, repo-root
  autobuild dir, and stale `autobuild/TASK-AB59-CANON` branch before
  each run. Supports `--verify-only` and `--skip-cleanup`. AC-002
  and AC-003 satisfied at the structural level — the failure-path
  was exercised live (`--verify-only` against missing artefacts
  exits 1 with the expected FATAL message), and the verifier was
  exercised against a synthetic PASS scenario (exits 0) and a
  synthetic FAIL scenario with phase_5 skipped + missing
  test-orchestrator marker (exits 1, A1 + C correctly red, A2 + B
  correctly green). Idempotency in the AC-003 sense (two consecutive
  live runs producing identical verdicts) was not exercised live.
- `validation/feat-ab59/verify_signals.py` — four-signal verifier.
  Splits the original Signal A into A1 (test-orchestrator-prompt
  evidence) and A2 (live-SDK message-stream evidence) because
  `guardkit/orchestrator/sdk_debug.py` records SDK message
  dataclasses where `role` is the SDK chat role, not the agent
  identity, and because both Player and test-orchestrator run as
  `agent_type="player"` (same applies to code-reviewer and the
  Coach validator on the coach side) so per-role `prompt.txt` +
  `messages.jsonl` get clobbered by the later writer in the same
  turn. The deviation is documented in the README.
- `validation/feat-ab59/README.md` — harness docs, signal table,
  failure-mode → boundary mapping (per TASK-REV-45750 §4),
  re-runnability invariants, and explicit "what this is not" scope.

### What did NOT ship

- AC-004: A successful end-to-end live run with verdict captured. The
  attempted run produced an empty worktree and zero turns. Root cause
  not investigated — closed without forensic artefacts to map against
  the boundary table.
- AC-005: Three artefact excerpts proving each PASS signal.
  Inapplicable — no PASS verdict.
- AC-006: Boundary-mapped FAIL evidence with a separately-filed
  follow-up fix-task ID. Inapplicable — there was no signal-level FAIL
  (signals couldn't be evaluated). Pre-signal failure is a different
  failure class than the spec contemplated.

### Implication for downstream workstreams

The original premise of this task — *"prove the FEAT-AB59 wiring
against the live SDK before burning forge/jarvis budget"* — remains
**unproven**. forge-FEAT-FORGE-002 and jarvis-FEAT-J002 are NOT
unblocked by this task's closure.

### Post-closure deletion (2026-04-25)

The harness was deleted post-closure on user direction (deemed useless
given the live run failed pre-artefact). What was deleted:

- `validation/feat-ab59/` (run_canonical.sh, verify_signals.py, README.md)
- `tasks/backlog/TASK-AB59-CANON-add-helper.md` (canonical fixture)
- `.guardkit/worktrees/TASK-AB59-CANON/` (dead worktree)
- branch `autobuild/TASK-AB59-CANON`

If FEAT-AB59 live-SDK validation is re-attempted later, the harness
must be rebuilt from scratch. The signal-deviation rationale (why
`grep '"role": "test-orchestrator"'` against `messages.jsonl` does
not work) is preserved in this task's Graphiti task-completion
episode (group `guardkit__task_outcomes`) and need not be
rediscovered. Whatever caused the live `guardkit autobuild task`
invocation to fail before producing any artefacts also remains
unidentified — likely upstream of the orchestrator-side specialist
invocations (AutoBuild initialisation or pre-loop), and a separate
diagnostic pass would be warranted before re-attempting FEAT-AB59
validation.
