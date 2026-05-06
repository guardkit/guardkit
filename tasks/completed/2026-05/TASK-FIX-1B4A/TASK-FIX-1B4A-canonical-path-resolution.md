---
id: TASK-FIX-1B4A
title: "Layer 1: Resolve files_modified claims through state-bridge canonical path before honesty verification"
status: completed
created: 2026-05-06T00:00:00Z
updated: 2026-05-06T18:25:00Z
completed: 2026-05-06T18:25:00Z
completed_location: tasks/completed/2026-05/TASK-FIX-1B4A/
previous_state: in_review
state_transition_reason: "All 8 ACs satisfied; quality gates green (5 new + 304 existing + 7 integration tests)"
priority: high
task_type: implementation
tags: [autobuild, coach, honesty-verification, state-bridge, layer-1, load-bearing]
parent_review: TASK-REV-1B452
feature_id: FEAT-1B452
implementation_mode: task-work
wave: 1
conductor_workspace: honesty-fix-wave1-1
complexity: 5
test_results:
  status: passed
  coverage: null
  last_run: 2026-05-06T18:15:00Z
  new_tests: 5
  existing_tests_pass: 304
---

# Task: Layer 1 — Canonical-path resolution in CoachVerifier

## Description

Restore the load-bearing fix for the FEAT-FFC3 false-fail by adding identity-based path resolution to `CoachVerifier._verify_files_exist`. When a Player-reported (or orchestrator-injected) path doesn't exist on disk, ask `state_bridge` for the task's current canonical path. If the canonical path exists and is for the same task, suppress the discrepancy and record the resolution for audit.

This is Layer 1 of three from the [v2 review](../../../.claude/reviews/TASK-REV-1B452-review-report.md). Independently load-bearing — alone, it closes the FFC3 reproducer. Pair with TASK-FIX-1B4C (Layer 3') for defence-in-depth.

## Context

**Failure mechanism** (validated end-to-end in v2 review):

`CoachVerifier._verify_files_exist` at [`coach_verification.py:231-257`](../../../guardkit/orchestrator/coach_verification.py) does naive `(worktree_path / file_path).exists()` for every entry in `files_modified` / `files_created` / `tests_written`. When state_bridge has moved the task file from `tasks/backlog/...` to `tasks/design_approved/...` mid-turn, any entry referencing the pre-move path triggers a critical discrepancy. The short-circuit at [`coach_validator.py:850-872`](../../../guardkit/orchestrator/quality_gates/coach_validator.py) then drops the 16-AC evaluation.

`state_bridge.py:287-316` already implements the lookup mechanism internally (`_get_current_state(self) -> Tuple[str, Path]` via `state_dir.rglob(f"{self.task_id}*.md")`). The public surface is missing — the fix exposes it as `canonical_path_for()`.

## Acceptance Criteria

- [ ] **AC-A1**: `TaskStateBridge` exposes a public method `canonical_path_for(self) -> Optional[Path]` that wraps `_get_current_state()`. Returns the task's current canonical path on success; returns `None` when `_get_current_state()` raises `TaskNotFoundError` (does not propagate the exception).
- [ ] **AC-A2**: `CoachVerifier.__init__` accepts optional `task_id: Optional[str]` and `state_bridge: Optional[TaskStateBridge]` parameters. When both are provided, identity resolution is enabled. When either is None, current exact-match behaviour is preserved (fail-open).
- [ ] **AC-A3**: `CoachVerifier._verify_files_exist` emits **no** `file_existence` discrepancy when (a) `(worktree / claimed_path).exists()` is False, AND (b) `state_bridge.canonical_path_for()` returns a path, AND (c) `(worktree / canonical_path).exists()` is True. The resolution is recorded on a new field `HonestyVerification.resolved_paths: List[ResolvedPath]` (default `[]`) where `ResolvedPath` is a new dataclass with fields `claimed: str`, `resolved_to: str`, `task_id: str`.
- [ ] **AC-A4**: `CoachVerifier._verify_files_exist` **still** emits a critical `file_existence` discrepancy when neither `claimed_path` nor `canonical_path` exists on disk (genuine missing-file case). The identity resolution is gated by canonical-path existence.
- [ ] **AC-A5**: `coach_validator.py:_verify_honesty` (line 5039-5076) constructs `CoachVerifier` with `task_id` (passed in from `validate(task, ...)`) and a `TaskStateBridge` instance for the worktree. The `repo_root` argument to `TaskStateBridge` is the worktree path (matching the existing pattern at `agent_invoker.py:5491-5495`).
- [ ] **AC-A6**: `coach_turn_N.json` schema is extended to include `honesty_verification.resolved_paths` (list of `{claimed, resolved_to, task_id}` dicts). The serialisation update is in `CoachValidationResult.to_dict()` (around `coach_validator.py:393-410` per existing honesty_verification serialisation pattern).
- [ ] **AC-A7**: All five regression tests in the new module `tests/unit/test_coach_verification_state_bridge.py` pass:
  - `test_state_bridge_move_does_not_false_fail_honesty` — Player report cites pre-move path, state-bridge has moved file, resolution suppresses discrepancy.
  - `test_genuine_missing_file_still_fails_honesty` — file doesn't exist anywhere, critical discrepancy fires.
  - `test_state_bridge_unavailable_falls_back_to_exact_match` — no state_bridge injection, exact-match behaviour preserved.
  - `test_canonical_path_for_returns_none_when_task_not_found` — `state_bridge.canonical_path_for()` swallows `TaskNotFoundError`.
  - `test_resolution_recorded_on_resolved_paths_field` — successful resolutions appear on `HonestyVerification.resolved_paths` for audit.
- [ ] **AC-A8**: Existing tests in `tests/unit/test_coach_verification.py` and `tests/unit/test_coach_validator.py` still pass with no regression (run full unit suite for both modules).

## Implementation Notes

**Files to modify**:

1. `guardkit/tasks/state_bridge.py` (~5 lines added):
   - Add public `canonical_path_for(self) -> Optional[Path]` after `get_current_state()`.

2. `guardkit/orchestrator/coach_verification.py` (~25 lines added/modified):
   - Add `ResolvedPath` dataclass.
   - Extend `HonestyVerification` with `resolved_paths: List[ResolvedPath] = field(default_factory=list)`.
   - Extend `CoachVerifier.__init__` signature with `task_id` and `state_bridge` optional kwargs.
   - In `_verify_files_exist`, when `Path.exists()` is False, attempt resolution via `state_bridge.canonical_path_for()`. On success, append to `resolved_paths` and continue. On failure, append discrepancy as today.

3. `guardkit/orchestrator/quality_gates/coach_validator.py` (~10 lines modified):
   - In `_verify_honesty` (line 5055), pass `task_id` and `TaskStateBridge` to the `CoachVerifier(...)` constructor.
   - In `CoachValidationResult.to_dict` (around line 395-410), serialise `resolved_paths`.

4. `tests/unit/test_coach_verification_state_bridge.py` (new, ~150 lines):
   - 5 tests per AC-A7.

**Cross-cutting concerns**:

- **Idempotency**: re-running verification on the same report yields identical resolution events. `state_bridge.canonical_path_for()` is read-only.
- **Thread safety**: state_bridge in autobuild context uses `in_autobuild_context=True`. The public `canonical_path_for()` method is a thin read-only wrapper around the existing private method; no new locking required.
- **Concurrent worktree safety**: each worktree has its own `TaskStateBridge` instance; the verifier uses the worktree-local bridge instance. No cross-task contamination.

## Notes

- This is the **load-bearing** fix. Layer 3' (TASK-FIX-1B4C) is independent defence-in-depth; ship both in Wave 1.
- After this lands, TASK-FIX-1B4B (Layer 2) becomes implementable in Wave 2 — its tests assume Layer 1's resolution semantics.
- After this lands AND Layer 3' lands, TASK-DOC-1B4D becomes implementable — the sibling rule should cite the landed fix.
- Risk assessment is in v2 review report §AC-8: "Layer 1 risk: masking genuine Player honesty violations" with four mitigations.
- Bug 2 and Bug 3 from the FEAT-FFC3 incident doc are tracked separately (TASK-REV-FFC4, TASK-REV-FFC5) — do not bundle.

## Implementation Summary

**Files changed** (3 modified, 1 new):

- `guardkit/tasks/state_bridge.py` (+20 lines): public `canonical_path_for() -> Optional[Path]` wrapping the existing `_get_current_state()` and swallowing `TaskNotFoundError`.
- `guardkit/orchestrator/coach_verification.py` (+112 / -2 lines): new `ResolvedPath` dataclass; `HonestyVerification` extended with `resolved_paths: List[ResolvedPath]`; `CoachVerifier.__init__` accepts optional `task_id` + `state_bridge`; `_verify_files_exist` now performs single-shot canonical-path lookup and suppresses the `file_existence` discrepancy when the task file has been moved by state_bridge mid-turn.
- `guardkit/orchestrator/quality_gates/coach_validator.py` (+50 / -10 lines): `_verify_honesty` now constructs `CoachVerifier` with `task_id=self.task_id` and `TaskStateBridge(self.task_id, self.worktree_path, in_autobuild_context=True)`; `CoachValidationResult.to_dict()` serialises `resolved_paths` for `coach_turn_N.json`.
- `tests/unit/test_coach_verification_state_bridge.py` (new, 175 lines): five regression tests covering the AC-A7 grid (move-resolves, genuine-missing, fail-open without bridge, `TaskNotFoundError` swallowed, audit field populated).

**Approach**: identity-based resolution — when the claimed path is missing on disk, ask state_bridge for the task's current canonical path *once per call* and suppress the discrepancy if that path exists. The resolution is recorded on `HonestyVerification.resolved_paths` for audit. Wiring is fail-open: if `task_id` or `state_bridge` is None, exact-match behaviour is preserved.

**Outcome**: all 8 acceptance criteria satisfied. New tests 5/5 pass; existing 304 `test_coach_verification*` and `test_coach_validator*` tests pass; 7 `test_coach_honesty_restoration.py` integration tests pass (no schema break from the additive `resolved_paths` field).

**Lessons**:

- `TaskStateBridge.canonical_path_for()` returning `Optional[Path]` keeps the failure mode encapsulated — the verifier never has to think about `TaskNotFoundError`. Wrapping rather than re-raising at the public surface is the cleaner shape.
- Adding a new field to `HonestyVerification` did not break the existing `to_dict()` consumer assertions in `test_coach_honesty_restoration.py` because the test only asserts presence of specific keys, not the exact key set. This is the right contract for additive schema growth, but it's worth documenting that the integration test relies on it.
- Caching `canonical_path_for()` once per `_verify_files_exist` call (single resolution shared across all claimed paths) is correct — the bridge always returns the same path within a turn, and re-invoking would be wasted work. A second canonical lookup on every claim would also have made the over-suppression risk worse, not better.
- This task is intentionally permissive on its own: any non-existent claim could be suppressed if the task file exists somewhere. That risk is closed by Layer 3' (TASK-FIX-1B4C), which prevents the orchestrator-induced ghost path from entering `report["files_modified"]` in the first place. Layer 1 alone closes the FFC3 reproducer; pair both for defence-in-depth.
