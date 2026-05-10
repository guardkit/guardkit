---
id: TASK-AB-FIX-CHECKPOINT-CLAIM-AUDIT
title: "Per-turn checkpoint must verify Player-claimed files are staged before commit (catch silent gitignore eaters)"
status: completed
created: 2026-05-10T00:00:00Z
updated: 2026-05-10T18:30:00Z
completed: 2026-05-10T18:30:00Z
completed_location: tasks/completed/2026-05/TASK-AB-FIX-CHECKPOINT-CLAIM-AUDIT/
priority: high
tags: [autobuild, orchestrator, checkpoint, quality-gate, false-positive-approval, gitignore, defense-in-depth]
task_type: feature
complexity: 4
estimated_minutes: 180
parent_review: TASK-INV-AB1
related_tasks:
  - TASK-AB-FIX-INVAB1
  - TASK-INV-AB1
related_rules:
  - .claude/rules/absence-of-failure-is-not-success.md
---

# Task: Per-turn checkpoint must verify Player-claimed files are staged before commit

## Provenance

This is a sibling / defense-in-depth follow-up to **TASK-AB-FIX-INVAB1**
(2026-05-06, completed) and the rule it seeded,
[`.claude/rules/absence-of-failure-is-not-success.md`](../../.claude/rules/absence-of-failure-is-not-success.md).

The original investigation (**TASK-INV-AB1**) identified that the
deterministic Coach path bypassed `CoachVerifier`. The fix wired
`CoachVerifier` into `CoachValidator` so file-existence claims are
checked on disk via `Path(worktree_path / file).exists()`.

That fix worked exactly as designed. **It does not, however, defend
against the case where the Player creates a file in the worktree that
git silently refuses to stage** — typically due to an unanchored
`.gitignore` rule. The Coach passes (file *does* exist on disk), the
checkpoint commits successfully (no error from `git add` for an ignored
path), the per-turn artifact diff appears clean… and the Player-created
source file never reaches the merged branch. Worktree gets cleaned up
later, file is lost.

This was the failure mode that bit `study-tutor` `FEAT-39E1` on
2026-05-08 (4 production source modules silently dropped). Forensic
trail in the §Evidence section below.

## Problem statement

The autobuild orchestrator's per-turn checkpoint step (`[guardkit-checkpoint]
Turn N complete (tests: pass)` commits) currently does not cross-check
the set of files the Player claims to have created/modified against the
set of files actually staged for the commit. As a result, files
silently filtered by `.gitignore` (or any other git-add filter:
pathspecs, sparse-checkout, attribute filters, etc.) are committed-by-
omission with no error surfaced to either the Player feedback channel
or the Coach gate evaluation.

The structural shape matches the defect class documented in
[`.claude/rules/absence-of-failure-is-not-success.md`](../../.claude/rules/absence-of-failure-is-not-success.md):
**absence of evidence (no `git add` error for a silently-ignored path)
is being interpreted as evidence of absence of failure**. The rule's
remediation #1 — *"Pair every count_failed == 0 rule with
count_attempted > 0; refuse to approve when the attempted-count is zero
or absent. Surface 'no oracle ran' as a feedback issue, not silent
approval."* — applies here verbatim. The "attempted count" in this case
is the count of Player-claimed files that actually got staged.

## Evidence (FEAT-39E1, 2026-05-08)

Reconstructed from the `study-tutor` repo at commit `54d8cbb` (the
FEAT-39E1 merge commit). All file paths below are inside the
`study-tutor` checkout.

### Player wrote the files

`task_work_results.json` for `TASK-NATS-PH1-002`:

```json
{
  "files_created": [
    "src/study_tutor/adapters/manifest.py",
    "tests/unit/adapters/test_manifest.py"
  ],
  "completion_promises": [
    {
      "criterion_id": "AC-001",
      "implementation_files": ["src/study_tutor/adapters/manifest.py"],
      ...
    },
    ... (5 more ACs, all citing the same file)
  ],
  "tests_run": true,
  "tests_passed": true
}
```

### Coach verified them on disk and approved

`coach_turn_1.json` for the same task:

```json
{
  "decision": "approve",
  "validation_results": { "all_gates_passed": true },
  "honesty_verification": {
    "verified": true,
    "honesty_score": 1.0,
    "discrepancy_count": 0,
    "resolved_paths": []
  }
}
```

Note: `resolved_paths: []` here is *correct* per `_verify_files_exist`
semantics — it only populates when files were missing-but-rescued via
`state_bridge.canonical_path_for()`. An empty list with `verified: true`
means "every claimed file was found directly at `worktree_path /
file`". The Coach was honest. The files really were there.

### Per-turn checkpoint silently dropped them

The autobuild branch tip `031b437` (just before the merge) contains
**zero** files under `src/study_tutor/adapters/` or `tests/unit/
adapters/`:

```
$ git ls-tree -r 031b437 -- src/study_tutor/adapters/
(empty)
$ git ls-tree -r 031b437 -- tests/unit/adapters/
(empty)
```

`git show --stat 031b437` shows the checkpoint commit added 9 files,
all under `.guardkit/autobuild/TASK-NATS-PH2-001/` (autobuild metadata)
plus `coverage_phase4.json` — but **no** source files for the task it
was checkpointing.

### Why git dropped them

`study-tutor/.gitignore:284` carries an unanchored rule
`adapters/` (intended for ML model artefacts: LoRA weights etc.).
Lines 295-298 re-include `src/study_tutor/tutoring/adapters/`
specifically (added by TASK-INV-AB1's fix for FEAT-6CC5). The new
NATS-fleet adapters package at `src/study_tutor/adapters/` and its test
mirror `tests/unit/adapters/` were not listed in the re-include block,
so `git add` silently skipped them. (Patched separately in study-tutor
post-mortem.)

### Downstream blast radius

- 4 production modules and ~3 test modules permanently lost (only
  reconstructable from autobuild artifact JSONs).
- 6 tasks (PH1-001/002/004/005/008/009) marked `status: completed` in
  `tasks/completed/` despite shipping zero deliverables.
- Container deployment crash-loops for 2 days before the gap was
  caught during the operator-run deployment runbook.
- Operator-side recovery cost: feature-yaml restore from git, 6 task
  files moved back to backlog, 7 stale duplicate stubs cleaned up,
  3 commits (study-tutor) of audit metadata and reopen documentation.

## Proposed remediation

After every successful per-turn checkpoint git commit (and before the
Coach gate accepts the turn as `approve`), cross-check Player-claimed
file paths against the actual staged set:

```python
# Pseudocode — slot into the orchestrator's checkpoint step,
# right after the `git add` and `git commit` for the turn.

claimed = set()
for key in ("files_created", "files_modified", "tests_written"):
    claimed.update(task_work_results.get(key, []))
for promise in task_work_results.get("completion_promises", []):
    claimed.update(promise.get("implementation_files", []))
    if t := promise.get("test_file"):
        claimed.add(t)

# What did git actually pick up in the checkpoint commit?
staged = set(
    subprocess.check_output(
        ["git", "show", "--name-only", "--format=", "HEAD"],
        cwd=worktree_path,
    ).decode().splitlines()
)

dropped = claimed - staged
if dropped:
    raise CheckpointClaimAuditFailed(
        category="claim_audit",
        message=(
            f"Player claimed {len(claimed)} files but git only staged "
            f"{len(claimed) - len(dropped)}. Dropped: {sorted(dropped)}. "
            "Most common cause: unanchored .gitignore rule. Investigate "
            "before approving the turn."
        ),
        dropped=sorted(dropped),
    )
```

Surface the failure as a Coach `must_fix` issue with `category:
"claim_audit"` (sibling of TASK-AB-FIX-INVAB1's `category: "honesty"`).
This makes it dashboard-visible and stall-classifier-aware.

The check is cheap (one `git show --name-only` per turn) and adds the
"attempted count > 0" precondition that the rule's §Remediation #1
requires for the implicit `git add error count == 0` gate.

## Acceptance criteria

- [x] **AC-001**: After the per-turn checkpoint commit, the orchestrator
  computes the `claimed` set from `task_work_results.files_created +
  files_modified + tests_written + completion_promises[*].implementation_files
  + completion_promises[*].test_file` (any keys present).
- [x] **AC-002**: The orchestrator computes the `staged` set from
  `git show --name-only --format= HEAD` in the worktree.
  *Implementation note*: in the current `autobuild.py` flow Coach
  validates **before** the checkpoint commit lands
  (`autobuild.py:2257-2266` for approve path, `:2306-2316` for feedback
  path), so at honesty-verification time HEAD is still the previous
  turn's checkpoint. Using `git show HEAD` would therefore audit the
  wrong commit. The implementation uses
  `git status --porcelain=v1 --untracked-files=all` which returns the
  same staged-set semantics ("paths git would pick up on the next
  `git add -A`") at the right moment in the flow. The intent of AC-002
  is preserved — the literal command is documented as a deviation in
  `coach_verification.py::_verify_claims_were_staged` so a future
  reviewer can re-evaluate if the checkpoint timing changes.
- [x] **AC-003**: If `claimed - staged` is non-empty, the turn is
  REJECTED with a Coach `must_fix` issue with `category: "claim_audit"`.
  The error description names each dropped path and the
  unanchored-`.gitignore` root cause. Implemented in
  `coach_validator.py::_honesty_issues_from`.
- [x] **AC-004**: Zero-cardinality input → empty discrepancy list →
  other gates decide. Pair-with-attempted-count semantics from
  `absence-of-failure-is-not-success.md`. Tested in
  `tests/unit/test_coach_verification_claim_audit.py` (`test_ac006_*`)
  and `tests/integration/orchestrator/test_coach_claim_audit.py`
  (`test_ac006_zero_claimed_files_does_not_trigger_claim_audit`).
- [x] **AC-005**: Regression test:
  `tests/integration/orchestrator/test_coach_claim_audit.py
  ::test_ac005_gitignored_file_triggers_claim_audit_feedback` — uses
  a real git worktree with the same unanchored `adapters/` rule that
  bit study-tutor on 2026-05-08. Asserts `decision == "feedback"` and
  exactly one issue with `category: "claim_audit"` and
  `severity: "must_fix"`.
- [x] **AC-006**: Regression test:
  `tests/integration/orchestrator/test_coach_claim_audit.py
  ::test_ac006_zero_claimed_files_does_not_trigger_claim_audit` —
  zero file claims emit no claim_audit issue.
- [x] **AC-007**: Regression test:
  `tests/integration/orchestrator/test_coach_claim_audit.py
  ::test_ac007_all_files_stageable_does_not_trigger_claim_audit` —
  Player creates real source + test files in a real git worktree,
  no claim_audit issue surfaces.
- [x] **AC-008**: All existing tests pass. Verified by running:
  - `tests/unit/test_coach_validator.py` (281 passed)
  - `tests/unit/test_coach_verification.py` (all passed)
  - `tests/unit/test_coach_verification_promises.py` (all passed)
  - `tests/unit/test_coach_verification_state_bridge.py` (all passed)
  - `tests/integration/orchestrator/test_coach_honesty_restoration.py`
    (all passed)
  - `tests/integration/orchestrator/test_coach_record_honesty_roundtrip.py`
    (all passed)

  Pre-existing failures observed but unrelated to this change:
  `tests/orchestrator/test_visual_comparator.py` (missing
  `scikit-image`/`pillow` deps in env);
  `tests/rules/test_no_dead_task_id_references.py` (4 dead TASK-IDs in
  unrelated orchestrator files — verified failing on `main` before this
  change via `git stash`).

## Test cases (zero-cardinality coverage per the rule's §Detection recipe)

Beyond AC-005/006/007 above, exercise:

- Player claims a file that exists on disk (in worktree) but is
  pathspec-filtered by `git config core.sparseCheckout`. Same shape
  as gitignore-filter: file present on FS, missing from `git show
  --name-only`. Should reject.
- Player claims a file that exists in the worktree but the git index
  treats it as `assume-unchanged`. Should reject if the file's content
  differs from what's on disk.
- Player claims `tests/unit/foo/test_x.py` and `src/foo/x.py`; only
  the test file is staged. Should reject with both dropped paths
  surfaced.

## References

- **Parent investigation**:
  [`tasks/completed/TASK-INV-AB1-autobuild-approves-empty-implementations.md`](../../tasks/completed/TASK-INV-AB1-autobuild-approves-empty-implementations.md)
- **Sibling fix (the previous remediation, completed)**:
  [`tasks/completed/2026-05/TASK-AB-FIX-INVAB1/TASK-AB-FIX-INVAB1.md`](../../tasks/completed/2026-05/TASK-AB-FIX-INVAB1/TASK-AB-FIX-INVAB1.md)
- **Rule that captures the defect class**:
  [`.claude/rules/absence-of-failure-is-not-success.md`](../../.claude/rules/absence-of-failure-is-not-success.md)
- **Affected code (likely patch points)**:
  - The orchestrator's per-turn checkpoint step (search:
    `[guardkit-checkpoint] Turn` literal in
    `guardkit/orchestrator/`)
  - `CoachValidator.evaluate` in
    `guardkit/orchestrator/quality_gates/coach_validator.py` —
    add `category: "claim_audit"` issue handling
  - `CoachVerifier` in `guardkit/orchestrator/coach_verification.py`
    — add a `_verify_claims_were_staged` method that mirrors
    `_verify_files_exist` but checks the staged set instead of the
    on-disk set
- **Forensic trail (study-tutor side)**:
  - `study-tutor/.guardkit/autobuild/TASK-NATS-PH1-002/{player_turn_1,coach_turn_1,task_work_results}.json`
    (in commit `54d8cbb`)
  - `study-tutor/.gitignore:284-298` (the unanchored `adapters/` rule
    + narrow re-includes — patched in study-tutor post-mortem)
  - `study-tutor` commit `f06f982` — chore(FEAT-39E1) reopen 6 false-
    completed tasks
