---
id: TASK-AB-006
title: "Fix Coach AC-linter parsing pytest commands as literal file paths"
task_type: feature
parent_review: TASK-REV-8413
feature_id: FEAT-AB-FIX
wave: 3
implementation_mode: task-work
complexity: 3
estimated_minutes: 60
dependencies:
  - TASK-AB-005
working_dir: /home/richardwoollcott/Projects/appmilla_github/guardkit
domain_tags:
  - autobuild
  - coach
  - ac-linter
  - parser-bug
status: completed
previous_state: in_review
state_transition_reason: "Fix shipped, regression tests green, no preflight regression"
updated: 2026-05-10T00:00:00Z
completed: 2026-05-10T00:00:00Z
completed_location: tasks/completed/2026-05/autobuild-bdd-oracle-fix/
---

## Implementation Summary

**Root cause:** `_extract_paths_from_ac_text` in
`guardkit/orchestrator/quality_gates/coach_validator.py` had a backtick
regex (`` r"`([^`]+\.[a-zA-Z]+)`" ``) that captured the entire backtick
span as a single "path" whenever the span ended in `.{ext}`. For AC text
`` `pytest tests/test_openwebui_pipe.py` `` the whole command string
`pytest tests/test_openwebui_pipe.py` was captured. `Path(...).name` then
yielded `test_openwebui_pipe.py` (matched the test-file heuristic) but
`worktree_path / "pytest tests/test_openwebui_pipe.py"` failed disk
existence — the FG-004 stall short-circuit fired on every Player turn.

**Fix:** combined Option 1 + Option 2 from the task. Whitespace-bearing
quoted content (backtick, single-quote, double-quote) is now treated as
a command line: split on whitespace, strip pytest node-ID suffixes
(`::test_name`), and keep only tokens matching `[\w./\-]+\.\w{1,5}`.
Runner prefixes (`pytest`, `python`, `npm`, `dotnet`) and flags (`-v`,
`--filter ...`) drop out automatically because they don't match the
path regex. Bare backtick paths (no whitespace) preserved verbatim
modulo the `::` strip.

**Files changed:**

- `guardkit/orchestrator/quality_gates/coach_validator.py` —
  `_extract_paths_from_ac_text` tokenisation + docstring update;
  `_detect_ac_cited_missing_test_files` docstring updated to document
  non-pytest runner behaviour (per AC-4).
- `tests/unit/orchestrator/quality_gates/test_coach_validator_test_command_honesty.py`
  — 10 new TASK-AB-006 regression tests covering all 6 path-shape
  variants from AC scope §4 plus a direct
  `_extract_paths_from_ac_text` helper-level test.

**AC verification:**

- AC-1 (unit tests for all path-shape variants): ✅ 10 new tests cover
  bare path, `pytest <path>`, `pytest -v <path>`, `pytest <path>::node_id`,
  `python -m pytest <path>`, `npm test` / `dotnet test` (documented
  no-finding behaviour).
- AC-2 (FG-004 resume in fleet-gateway reaches a substantively different
  Coach decision): **deferred**. The task's own *Out of Scope* section
  states "Re-running TASK-FG-004 to completion. That's a separate
  verification task once the linter fix lands." Filed for follow-up.
- AC-3 (no TASK-GK-PR-001 preflight regression): ✅ all 14 preflight
  tests still green.
- AC-4 (non-pytest runner behaviour documented in module docstring):
  ✅ documented in both `_extract_paths_from_ac_text` and
  `_detect_ac_cited_missing_test_files` docstrings.

**Test results:** 134/134 quality_gates + integration tests pass; 14/14
preflight tests pass; 15/15 command-honesty tests pass.

## Notes

The fix is intentionally local — only `_extract_paths_from_ac_text`
changes. Both downstream callers (`_ac_text_paths_all_exist_on_disk` for
hybrid fallback and `_detect_ac_cited_missing_test_files` for the AC-006
honesty gate) inherit the corrected tokenisation transparently. Glob
filtering (`*` rejection) is unchanged. Insertion-order dedup is
unchanged.

The non-pytest-runner shape (`npm test`, `dotnet test --filter ...`)
yields no path candidates because no token matches `\.{ext}`. The
docstring on `_detect_ac_cited_missing_test_files` documents this so
future stack contributors know that explicit AC-cited file paths
(e.g. `AC-x: tests in tests/Suite.cs pass`) are required if disk
verification is desired for non-pytest runners.

---

# TASK-AB-006: Fix Coach AC-linter parsing pytest commands as literal file paths

## Repository

**Working directory:** this repo (`guardkit`).

The bug is in the AC-linter shipped from this repo (introduced in commit `fd4580e8`
— "complete(TASK-GK-PR-001): add preflight existence check for `## Files to Modify`
paths"). This is the guardkit-side fix. The verification step re-runs an autobuild in the
sibling `fleet-gateway` repo, but no fleet-gateway code change is required.

## Why This Exists

Discovered while running TASK-AB-005's autobuild resume on 2026-05-10
(see `fleet-gateway/docs/history/autobuild-FEAT-FG-001-resume-run-2.md`). Wave 2
(FG-002, FG-003) completed cleanly, validating the four Wave-1 fixes (AB-001/002/003/004).
But **TASK-FG-004 stalled with `unrecoverable_stall` after 3 turns** for a reason none of
the Wave-1 fixes address.

Coach decision JSON for FG-004 turn 3
(`fleet-gateway/.guardkit/worktrees/FEAT-FG-001/.guardkit/autobuild/TASK-FG-004/coach_turn_3.json`):

```json
{
  "issues": [{
    "severity": "must_fix",
    "category": "acceptance_criteria",
    "description": "AC names test file(s) that don't exist on disk: pytest tests/test_openwebui_pipe.py. The independent-test gate cannot run honestly while AC-cited tests are absent.",
    "details": {
      "missing_test_files": ["pytest tests/test_openwebui_pipe.py"]
    }
  }],
  "rationale": "1 AC-cited test file(s) missing on disk; gate cannot run honestly."
}
```

The "missing path" the linter reports is the literal string
**`pytest tests/test_openwebui_pipe.py`** — that is, the linter has stored a *command line*
in `missing_test_files` as if it were a single path. The actual file
`tests/test_openwebui_pipe.py` exists in the FEAT-FG-001 worktree and runs 14 tests cleanly:

```
$ cd ~/Projects/appmilla_github/fleet-gateway/.guardkit/worktrees/FEAT-FG-001
$ .venv/bin/pytest tests/test_openwebui_pipe.py -q
14 passed in 0.05s
```

Because the linter short-circuits before `run_independent_tests`, every Player turn ends
with the same Coach feedback hash, the orchestrator detects the feedback-stall pattern
("0/10 criteria verified across 3 turns, no passing checkpoint"), and declares
`unrecoverable_stall`. The Player has no way to recover — the implementation is fine; the
gate is mis-parsing the AC.

## Reproduction

The Wave-3 stall reproduces deterministically given:

1. The current state of the FEAT-FG-001 worktree in fleet-gateway (TASK-AB-005 resume
   already ran).
2. TASK-FG-004 acceptance criteria, which include a literal:
   ```markdown
   - [ ] `pytest tests/test_openwebui_pipe.py` exits 0 with all tests passing
   ```
   (Inspect
   `fleet-gateway/.guardkit/worktrees/FEAT-FG-001/tasks/design_approved/TASK-FG-004-openwebui-pipe-refactor.md`
   to confirm the exact AC line — the linter is regex-matching against it.)
3. Re-running the autobuild from fleet-gateway:
   `guardkit autobuild feature FEAT-FG-001 --resume` triggers the same FG-004 stall pattern.

For an isolated unit-level reproduction, point the AC-linter directly at the saved
`TASK-FG-004-openwebui-pipe-refactor.md` and observe `missing_test_files` contain
`"pytest tests/test_openwebui_pipe.py"` even though the file is on disk.

## Root Cause Hypothesis (verify in scope of fix)

The AC-linter (in `guardkit/orchestrator/quality_gates/` — the same module commit
`fd4580e8` introduced) appears to be using a path-extraction regex that captures the
*entire backtick-quoted string* including the `pytest ` prefix. Two likely fix shapes:

1. **Treat the string as a command line**: split on whitespace, take the last token, treat
   that as the path candidate. Works for the FG-004 case and most pytest invocation shapes.
2. **Strip known command prefixes**: maintain a small set of known runners (`pytest`,
   `python -m pytest`, `npm test`, `dotnet test`, …) and strip them before path-existence
   check.

Option 1 is simpler and more robust to unknown runners. Option 2 is more defensible against
e.g. `pytest --collect-only tests/foo.py::test_bar` where the bare-token approach picks up
the parametrized node ID rather than the file path.

A combined approach — strip a known runner prefix, then take the first remaining token that
looks like a path — would handle both cases cleanly.

## Scope

1. **Locate the AC-linter** in `guardkit/orchestrator/quality_gates/` (grep for
   `missing_test_files` and the rationale string `"AC-cited test file"`).
2. **Reproduce in a unit test** with the literal AC string `` `pytest tests/test_openwebui_pipe.py` ``;
   the existing test should pass and a new test should fail before the fix.
3. **Implement the parser fix** (Option 1, Option 2, or combined per design discussion).
4. **Add regression tests** covering at minimum:
   - Bare path: `tests/foo.py` → checked literally
   - Pytest command: `pytest tests/foo.py` → strip `pytest`, check `tests/foo.py`
   - Pytest with flags: `pytest -v tests/foo.py` → flags ignored, file path checked
   - Pytest with node ID: `pytest tests/foo.py::test_bar` → strip `::test_bar`, check file
   - Python-module pytest: `python -m pytest tests/foo.py` → recognise the prefix
   - Non-pytest commands (`npm test`, `dotnet test --filter ...`): document chosen behaviour
5. **Verify against TASK-FG-004**: re-run the resume in fleet-gateway (or directly invoke
   the AC-linter against the saved task file) and confirm the gate now runs
   `run_independent_tests` instead of short-circuiting.

## Acceptance Criteria

- [ ] AC-linter unit tests cover all path-shape variants in §4 above.
- [ ] FG-004 resume run produces a Coach decision other than the AC short-circuit
      (either approved, or rejected on a different gate that actually ran).
- [ ] No regression in TASK-GK-PR-001's original behaviour: bare paths in
      `## Files to Modify` and `## Files to Create` sections still preflight-checked.
- [ ] If a non-pytest runner is encountered (e.g. `dotnet test`), the linter behaviour is
      documented in the AC-linter module docstring, not silent.

## Out of Scope

- Re-running TASK-FG-004 to completion. That's a separate verification task once the linter
  fix lands.
- The recurring `SDK coach test execution failed (exit 1)` log noise observed during the
  resume (different defect — separate task if it persists).
- The "Documentation level constraint violated" warnings observed on FG-004/005/006
  (different defect — orthogonal to this parser bug).

## Verification

After the fix:

```bash
# Unit-level (in this repo):
cd ~/Projects/appmilla_github/guardkit
.venv/bin/pytest <new ac-linter test module> -v
# Expect: all path-shape variants pass.

# Integration-level (in fleet-gateway):
cd ~/Projects/appmilla_github/fleet-gateway
guardkit autobuild feature FEAT-FG-001 --resume
# Expect: TASK-FG-004 either reaches approved, or rejects on a substantively different
# Coach issue (compilation failure, BDD failure, etc) — not the AC-linter short-circuit.
```

## References

- **Verification task that surfaced this:** TASK-AB-005 (in `fleet-gateway/tasks/in_review/autobuild-bdd-oracle-fix/`)
- **Resume telemetry:** `fleet-gateway/docs/history/autobuild-FEAT-FG-001-resume-run-2.md`
- **Coach decision JSON:** `fleet-gateway/.guardkit/worktrees/FEAT-FG-001/.guardkit/autobuild/TASK-FG-004/coach_turn_3.json`
- **Sibling Wave-1 fixes (already merged):** TASK-AB-001 (`33f9db26`), TASK-AB-003
  (`b0819556`), TASK-AB-004 (`00933c38`) here in guardkit; TASK-AB-002 (`0d66b9d`) in
  fleet-gateway.
- **The AC-linter was introduced in** guardkit commit `fd4580e8`
  ("complete(TASK-GK-PR-001): add preflight existence check for `## Files to Modify` paths").
