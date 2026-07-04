---
complexity: 7
consumer_context:
- consumes: behavioural_oracle
  driver: guardkit.orchestrator.quality_gates.coach_evidence
  format_note: Optional[Dict]; None = no oracle discovered; ran+failed is the ONLY
    state that overrides a verdict
  framework: CoachEvidenceBundle sibling field
  task: TASK-QAV-002
dependencies:
- TASK-QAV-002
feature_id: FEAT-10AC
id: TASK-QAV-004
implementation_mode: task-work
parent_review: TASK-REV-QAVG
priority: high
status: design_approved
task_type: feature
title: L4 behavioural round-trip oracle — independent oracle discovery, execution,
  hard-RED override
wave: 4
---

# Task: L4 behavioural round-trip oracle

## Description

Populate the `behavioural_oracle` bundle field and add the ONE deterministic
hard gate of this feature: an oracle **the Player did not author** (A2), run
against the live dependency, whose **ran-and-failed** outcome overrides an
approving Coach verdict to feedback — the direct fix for the fs-01 class
(FEAT-MEM-04 false green).

**Discovery is by artefact presence**
(`.claude/rules/activate-by-artefact-not-opt-in-flag.md`): an oracle file at
the convention path `tests/acceptance/*_roundtrip.py` in the worktree, or —
for non-file oracles only — a `behavioural_oracle.command` declared in the
feature YAML (genuine operator policy with no artefact proxy). No frontmatter
opt-in flag.

**Independence check** (ASSUM-004): the oracle file must NOT be in the turn's
authored set (`files_authored` when present, else `files_created ∪
files_modified`). A Player-authored oracle degrades to absent + a warning —
it is never trusted as independent evidence.

**Outcome policy** (consolidation §2 + ASSUM-005/006): ran-and-failed → hard
RED; started-then-timed-out → ran-and-failed (a deliverable that hangs is a
real defect, COACHRUNPARITY01 semantics); failed-to-start / runner error /
no oracle discovered → ABSENT (WARN in v0), never a pass, never a block.

## Acceptance Criteria

- [ ] **AC-1 (hard gate, red→green reproducer):** with a discovered
  independent oracle that ran and failed, an `approve` Coach verdict is
  overridden to `feedback` with a `must_fix` issue naming the oracle and its
  failure output; without the guard the approve stands (red test proves it).
- [ ] **AC-2 (disk persistence):** the override re-persists `coach_turn_N.json`
  so Layer-4 late-approval reconciliation cannot resurrect the stale approve
  (`.claude/rules/deterministic-verdict-override-must-persist-to-disk.md`);
  persistence failure is logged-not-blocking (verdict already overridden in
  memory).
- [ ] **AC-3 (None-safety):** the guard is a no-op when the bundle is `None`,
  `behavioural_oracle` is `None`, or the outcome is anything but
  ran-and-failed — mirroring the existing guard archetype's None-safety.
- [ ] **AC-4 (pass path):** a passing oracle records
  `{status:"ran", passed:true, oracle_path, provenance}` in the bundle; no
  override fires.
- [ ] **AC-5 (independence):** a Player-authored oracle (in the authored set)
  is recorded as `{status:"not_independent"}` + a `should_fix` warning; it
  neither passes nor blocks.
- [ ] **AC-6 (timeout asymmetry):** started-then-timed-out → ran-and-failed
  (fires the override); failed-to-start → absent WARN (no override). Both
  branches pinned by tests.
- [ ] **AC-7 (absence discipline):** no declared oracle → `behavioural_oracle`
  stays `None`; declared-but-unresolvable → absent WARN; both survive
  serialization unchanged and never coerce to pass/fail downstream.
- [ ] **AC-8 (behavioural check, dogfood):** an end-to-end test drives a
  fixture worktree with a real (not mocked) failing round-trip oracle through
  the Coach path and asserts the final persisted verdict is `feedback`.
- [ ] **AC-9:** existing suites green; all modified files pass
  project-configured lint/format checks with zero errors.

## Test Requirements

Unit tests per outcome branch (pass / fail / timeout / not-started /
not-independent / absent); the AC-1 red→green regression pair; the AC-8
end-to-end. Model the guard verbatim on the
`_reconcile_absent_independent_test_signal` archetype (wired at the same
post-verdict seam, beside the COACHFG01 and spec-gap guards).

## Implementation Notes

- Oracle execution runs in the worktree venv with a bounded timeout
  (default 300s, env-overridable) — a specialist-style bound, applied
  structurally, never prompt-requested.
- Record provenance in the bundle dict: oracle path, discovery method
  (convention path vs feature-YAML command), authored-set check result,
  exit code, duration, tail of output (truncated).
- `feature-spec`'s fleet-memory instance: FEAT-MEM-05's parity harness is the
  reference oracle shape; do NOT hardcode it — the hook is generic.