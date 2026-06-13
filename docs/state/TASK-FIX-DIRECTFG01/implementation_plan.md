# Implementation Plan — TASK-FIX-DIRECTFG01

> Close the `direct` implementation_mode false-green: run AC-level / wiring /
> bin-entry verification even when Coach gates are `required=False`.
> Phase 2 plan (software-architect) + Phase 2.5B architectural review (74/100,
> APPROVE-WITH-RECOMMENDATIONS). Design corrected per the R1-blocker ruling.

## Live mechanism (confirmed)

- `implementation_mode: direct` → `agent_invoker.py::_invoke_player_direct` (~6038)
  → `_write_direct_mode_results` (~6277) writes `task_work_results.json` with
  `quality_gates.quality_gates_relaxed: True` (the only writer of that flag;
  full task-work never sets it → sound AC5 guard).
- Live Coach path = `_invoke_coach_primary` (autobuild.py:5575) →
  `CoachValidator.gather_evidence` (:5639). Legacy `validate()` only under
  `GUARDKIT_COACH_LEGACY=1`.
- Precedent: `_evidence_repo_gate` runs in BOTH paths (primary :5675, legacy
  :5484) AFTER `gather_evidence` and BEFORE the LLM Coach, blocking
  deterministically via `_emit_synthetic_coach_feedback` (:5844-5896). A red
  signal must not be approved over by LLM leniency (BDDW-002 lesson).

## Design (the approved shape)

Add a sibling deterministic gate `_direct_mode_evidence_gate(...)` in
`autobuild.py`, wired into BOTH Coach paths immediately after the
`_evidence_repo_gate` call, returning `None` (nothing to block) or a blocking
`_emit_synthetic_coach_feedback(...)` result. Internally gated on
`task_work_results["quality_gates"]["quality_gates_relaxed"] is True`.

When direct-mode, it runs three checks and collects `must_fix` issues:

### AC1 — AC-level disk verification
Reuse `CoachValidator.validate_requirements` (the existing AC↔evidence matcher)
against `acceptance_criteria` + authored files. In direct mode, an
`all_criteria_met == False` becomes blocking:
`{"severity":"must_fix","category":"direct_mode_ac_unverified","description":...}`
naming the unmet criteria. (Full mode keeps its current non-direct behaviour —
this only fires under the relaxed flag.)

### AC2 — Wiring consultation
Call the existing module-level `_run_wiring_analysis(worktree_path, authored_files,
task_type="feature", ...)` explicitly (do NOT mutate the resolved task_type in any
call frame — factory uses task_type only for the outer FEATURE/REFACTOR/INTEGRATION
gate). An `UNWIRED_PATH` finding on an authored file that is a registered bin-entry
→ `{"must_fix","direct_mode_wiring_gap",...}`. Factory unavailable → absent signal,
non-blocking (matches coach_validator.py:660 guard).

### AC3 — Bin-entry producer execution (NEW)
Private module-level `_check_direct_mode_bin_entries(worktree_path, authored_files,
timeout)`:
- Discover targets = paths in `<worktree>/installer/core/commands/bin-entries.txt`
  (bare repo-relative paths, `#` comments ignored; basename→command) ∩ authored
  files (`files_created ∪ files_modified`). Never execute non-authored scripts.
- For each authored `.py` target: `subprocess.run([python, path], cwd=worktree.path,
  env={**os.environ, "PYTHONPATH": str(worktree.path)}, stdin=DEVNULL,
  capture_output=True, text=True, timeout=_DIRECT_MODE_BIN_PROBE_TIMEOUT_S)`.
  - **Clean PYTHONPATH = worktree only** — do NOT inherit ambient PYTHONPATH
    (guardkit's own `src` would mask the import failure). (COACHCWD01 lesson.)
  - ABSENT (→ `{"must_fix","direct_mode_bin_entry_broken",...}` incl. stderr head)
    iff: stderr contains a Python `Traceback (most recent call last)` (the AC3
    "raises" case — the actual FEAT-9DDE ModuleNotFoundError), OR
    (returncode != 0 AND stdout empty). Include stderr head in feedback so a
    false-positive is diagnosable in one turn.
  - PRESENT (no issue) iff returncode == 0 (stdout may be empty — a module that
    loads silently is fine; do NOT penalise exit-0).
  - `TimeoutExpired` → ABSENT (`...broken`, "execution timed out").
- Non-`.py` authored bin-entry → `{"should_fix","direct_mode_bin_entry_unverifiable"}`
  advisory (absent signal, non-blocking — never crash / never false-pass).
  Per stack-plugin-architecture.md this is *execution* (plugin-acceptable), not
  static analysis; degrade for non-Python, do not build a stack-blind monolith.

### Blocking
If any `must_fix` issue collected → `_emit_synthetic_coach_feedback(...)` with a
rationale naming the categories + details; return it (block before LLM Coach).
Else return `None`. Non-blocking advisories ride `advisory_issues`. No new field
on `CoachEvidenceBundle` (YAGNI).

## Files
- `guardkit/orchestrator/autobuild.py`: `_DIRECT_MODE_BIN_PROBE_TIMEOUT_S=10`
  constant; `_check_direct_mode_bin_entries(...)` module fn; `_direct_mode_evidence_gate(...)`
  method; two call-sites (primary after ~5677, legacy after ~5486).
- `tests/orchestrator/test_direct_mode_false_green_regression.py` (new): AC4
  broken-wrapper regression + working-entry + non-python-advisory + full-mode-skip
  + unmet-ACs + timeout + authored-scoping. AC4 test MUST assert
  `invoke_coach` was NOT called when the gate blocks (proves pre-LLM block).

## AC5 safety
Every new check is gated on `quality_gates_relaxed is True`, written ONLY by the
direct-mode results writer. Full task-work tasks lack the flag → gate is a no-op
→ structurally unchanged. Full-mode verified correctly in run 3.

## Estimate
~1 prod file (autobuild.py, ~150-200 LOC) + 1 test file (~400 LOC). Complexity 5.
