# Implementation Plan: TASK-SELFFIX-002

## Task
behavioural_oracle.command for any stack

## Plan Status
**Completed** — Implementation and tests written, all passing.
Updated: 2026-07-25T14:40:21.242228

## Acceptance Criteria
- [x] AC-001: Command exits 0 → {status: "ran", passed: true, exit_code: 0, duration, timed_out: false, output_tail, provenance naming the command and its YAML origin}
- [x] AC-002: Command exits non-zero → {status: "ran", passed: false} with failure output in output_tail
- [x] AC-003: Command exceeds GUARDKIT_ORACLE_TIMEOUT → timed_out: true, subprocess killed
- [x] AC-004: Precedence — when roundtrip.py exists, command is NOT used
- [x] AC-005: YAML-declared command is operator policy, never downgraded to not_independent
- [x] AC-006: Hermetic tests cover all four shapes using fake commands (true/false/sleep)
- [x] AC-007: All modified files pass project-configured lint/format checks

## Implementation

### Files Modified
- `guardkit/orchestrator/quality_gates/coach_validator.py`
  - Added `task` parameter to `_produce_behavioural_oracle()` (optional, backward-compatible)
  - Added `_extract_command()` — extracts `behavioural_oracle.command` from task YAML (supports dict and string forms)
  - Added `_produce_python_oracle()` — refactored Python roundtrip execution (unchanged logic)
  - Added `_run_shell_command()` — executes shell command via `subprocess.run(shell=True)`
  - Added `_execute_oracle()` — shared subprocess execution with timeout/failure handling
  - Updated call site in `gather_evidence()` to pass `task` dict

### Files Created
- `tests/orchestrator/test_behavioural_oracle_command.py` — 15 tests covering:
  - `TestCommandExitZero` (3 tests): command exits 0, output capture, bare-string command
  - `TestCommandExitNonZero` (2 tests): command exits non-zero, failure output capture
  - `TestCommandTimeout` (2 tests): timeout returns timed_out=True, subprocess killed
  - `TestPrecedence` (2 tests): roundtrip.py takes precedence, failing roundtrip still takes precedence
  - `TestOperatorPolicy` (2 tests): command not downgraded when authored, no independence check
  - `TestAbsent` (2 tests): no oracle + no command → None, None task → None
  - `TestGatherEvidenceIntegration` (2 tests): end-to-end through gather_evidence

### Key Design Decisions
1. **Backward-compatible signature**: `task` parameter is optional (`None` by default) to avoid breaking existing callers
2. **Command extraction**: supports both `behavioural_oracle: {command: ...}` and `behavioural_oracle: "..."` (string shortcut)
3. **Shell execution**: uses `subprocess.run(command, shell=True, cwd=worktree_root, env=os.environ.copy())`
4. **Provenance naming**: `yaml_command:<command>` for shell commands, `independent` for Python oracles
5. **Operator policy**: shell commands bypass the independence check entirely — result is never `not_independent`
6. **Timeout**: uses `GUARDKIT_ORACLE_TIMEOUT` env var (default 300s), subprocess killed on timeout

## Test Results
- 15 new tests: all passing
- 13 existing behavioural_oracle tests: all passing (no regression)
- Total: 28 tests passing, 0 failures

## Notes
This plan was auto-generated because the task was created via /feature-plan
with pre-loop disabled (enable_pre_loop=False).
The detailed specifications are in the task markdown file.
