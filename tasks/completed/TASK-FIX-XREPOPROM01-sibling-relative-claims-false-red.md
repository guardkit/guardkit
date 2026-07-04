---
id: TASK-FIX-XREPOPROM01
title: Sibling-relative unqualified claims false-red — widen promise-existence + claim-audit to declared evidence repos
task_type: fix
priority: critical
status: completed
created: 2026-07-04T19:10:00+01:00
completed: 2026-07-04T19:40:00+01:00
implementation_mode: direct
complexity: 3
tags: [autobuild, honesty, evidence-repos, false-red, qa-verifier]
---

# Task: Sibling-relative unqualified claims false-red

## Incident (FEAT-10AC run 1, 2026-07-04)

TASK-QAV-001 (L2 anti-stub scan, cross-repo into guardkitfactory) failed with
`HONESTY_COLLAPSE` after 3 turns (68m44s) — while the Player's work was real:
980 insertions (analyzer + 4 dialect DATA files + 463-line test suite)
committed to the factory as sibling-evidence checkpoints (`84b2abe`,
`70b5b80`). A textbook "Coach rejected but the work exists on disk".

**Mechanism:** TASK-AB-XREPOEV01 taught the *orchestrator-authored* claim
fields the `<repo>:<path>` qualified scheme (`files_modified` /
`files_created` were correctly qualified), but the two **Player-authored**
claim verifiers were never widened:

1. `_verify_completion_promises_files_exist` — unqualified fall-through
   checked only `worktree_path / impl_file`. The Player promised
   `src/guardkitfactory/wiring/analyzer.py` (sibling-relative, unqualified)
   → miss → critical `promise_file_existence` ×10-11 per turn.
2. `_verify_claims_were_staged` — dropped *qualified* claims but audited
   unqualified sibling-relative ones against the WORKTREE's
   `git status --porcelain` → absent → "fabricated" critical `claim_audit`.

Three identical turns (the Player could not fix a nonexistent problem) →
collapse. This is the `evidence-boundary-narrower-than-write-surface`
false-red at the Player-authored-claim arms.

## Fix

`guardkit/orchestrator/coach_verification.py`:

- New `_resolve_against_evidence_repos(rel_path)` — declaration-bounded:
  returns `repo.root / rel_path` iff it EXISTS under a declared evidence
  repo root; `None` otherwise. No declared repos → prior behaviour exact.
- Promise fall-through: on worktree miss, a sibling hit is recorded on
  `HonestyVerification.resolved_paths` (audit trail) and suppressed; a path
  existing nowhere stays critical — the FEAT-6CC5 fabrication class is
  untouched.
- Claim audit: unqualified claims that are worktree-missing AND
  sibling-present are dropped (sibling staging is the per-repo checkpoint
  manager's job — same rationale as the existing qualified drop); claims
  existing nowhere still classify fabricated-critical.

## Acceptance / evidence

- [x] Reproducer tests:
  `tests/unit/test_coach_verification_promises.py::TestSiblingRelativeClaimResolution`
  (7 tests: resolve-not-critical, missing-everywhere-critical,
  no-repos-prior-behaviour, claim-audit drop + fabricated control,
  end-to-end resolved_paths surfacing).
- [x] Full related surface green: 82 passed / 12 skipped
  (`-k "coach_verification or claim_audit or claims_were_staged"`), plus
  the XREPOEV01 false-red regression + seam suites (37 passed).
- [x] Rule doc updated:
  `.claude/rules/evidence-boundary-narrower-than-write-surface.md`
  (incident #3).

## Related

- `.claude/rules/evidence-boundary-narrower-than-write-surface.md` (parent
  rule; this closes its Player-authored-claim gap)
- `.claude/rules/path-string-mismatch-is-not-dishonesty.md` (fail-open
  discipline; resolution only on positive evidence)
- TASK-AB-XREPOEV01 (`0fadbd4f`) — the original widening this completes
- FEAT-10AC run 1 log: `.guardkit/autobuild/FEAT-10AC-run1-stdout.log`
