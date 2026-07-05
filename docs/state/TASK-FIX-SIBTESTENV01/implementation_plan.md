# Implementation Plan — TASK-FIX-SIBTESTENV01

> Phase 2 output, 2026-07-05. Sibling evidence-repo `test_command` interpreter
> resolution made per-repo; guardkit-worktree-venv pinning removed from the
> sibling path; collection ImportError reclassified as absent signal with
> feedback-stall immunity.

## Verified defect trace

- `_build_repo_test_argv` (`guardkit/orchestrator/evidence_repos.py:557`) pins a
  bare `pytest`/`python`/`python3` head to whatever `venv_python` the caller
  threads. Sole production caller: `CoachValidator.run_evidence_repo_tests`
  (`coach_validator.py:4082-4086`), which threads `self._venv_python` — the
  guardkit worktree venv.
- FEAT-10AC run-2 kill mechanism (from `.guardkit/autobuild/FEAT-10AC-run2-stdout.log`):
  three identical synthetic-feedback turns ("sibling-repo tests FAILED (exit 2)"),
  then `Feedback stall: identical feedback (sig=513cf5ef) for 3 turns with 0
  criteria passing` → `unrecoverable_stall`. The stall came from
  `_is_feedback_stalled` (`autobuild.py:3021-3032` / `4776`), NOT the checkpoint
  pollution path (`_extract_tests_passed` already returns None for synthetic
  feedback → checkpoints immune).

## Key decisions

1. **Q1 / AC-3**: classification inside `run_repo_tests` alone does NOT satisfy
   "cannot stack into unrecoverable_stall" — the feedback-stall detector hashes
   feedback text, and "could NOT run" text is just as identical turn-over-turn.
   Add targeted immunity in `_is_feedback_stalled` (schema-matched marker, never
   text-match). Gate outcome unchanged: unrunnable still blocks.
2. **Q2**: REMOVE `venv_python` from `run_repo_tests`/`run_all_repo_tests`;
   update the single coach_validator call site. No other production caller; no
   test passes it. Removal makes AC-2 structurally true.
3. **Q3**: `interpreter:` field — relative paths resolve against `repo.root`;
   missing path → loud WARNING → fall through (fail-open).
4. **Q4**: POSIX-only venv probe — REUSE `probe_worktree_venv` from
   `environment_bootstrap` (stdlib-only import, no cycle; covers `.venv/bin/python`
   + legacy `.guardkit/venv/bin/python`).
5. **Precedence** (deviates from task's listed order, justified): explicit
   `interpreter:` field → `repo.root/.venv` probe → verbatim shell. Mirrors
   `_resolve_venv_python` precedent (explicit beats discovery, fall-through on
   missing); an operator field that only applied when `.venv` is absent would
   have no use case.

## Steps

### Step 1 — evidence_repos.py core
1. `EvidenceRepo`: add `interpreter: Optional[str] = None`.
2. `_parse_entry` → 3-tuple `(path, test_command, interpreter)`; thread through
   `resolve_evidence_repos`.
3. New `_resolve_repo_interpreter(repo) -> Optional[str]`: (a) `repo.interpreter`
   (relative → against repo.root; missing → WARNING + fall through);
   (b) `probe_worktree_venv(repo.root)`; (c) None. INFO-log resolution source.
   Docstring must state WHY explicit precedes probed: a stale sibling `.venv`
   must not silently override an operator declaration (arch-review REC-2).
4. `_build_repo_test_argv(test_command, interpreter)` — rename param, logic same.
5. `run_repo_tests(repo, timeout=600)` — drop `venv_python`; resolve per-repo;
   add AC-3 classification post-run. `run_all_repo_tests` — drop `venv_python`.
   Fix now-wrong "mirrors TASK-FIX-COACHPYENV" docstrings.

### Step 2 — AC-3 classification (evidence_repos.py)
```
_COLLECTION_ERROR_EXITS = (2, 3, 4)
_COLLECTION_IMPORT_ERROR_MARKERS = (
    "ImportError while importing test module",
    "ModuleNotFoundError: No module named",
    "ImportError: cannot import name",
)
_TESTS_ACTUALLY_RAN_RE = re.compile(r"\b\d+ (?:passed|failed)\b")
def _is_collection_import_error(returncode, output) -> bool
```
Rules: exit in (2,3,4); VETO when `_TESTS_ACTUALLY_RAN_RE` matches (tests ran →
stays ran-and-failed); require ≥1 ImportError marker (ambiguous exit-2 stays
ran-and-failed — bias to failure, bdd_runner precedent). When it fires:
`ran=False, passed=False, returncode=proc.returncode`, output_summary prefixed
"collection failed with an import error … suite NEVER ran … UNVERIFIED."
`evidence_repo_tests_blocking_reason` unchanged (unrunnable already blocks).

### Step 3 — coach_validator.py call site
Delete venv threading in `run_evidence_repo_tests`; fix docstrings (~1719-1731,
~4069). All worktree-side pinning untouched (AC-4).

### Step 4 — autobuild.py stall immunity
1. `_evidence_repo_gate`: `has_ran_and_failed = any(r.command and r.ran and not
   r.passed for r in results)`; pass `evidence_repo_signal_absent=(not
   has_ran_and_failed)` (pure-absent only; mixed sets stay stall-stackable).
2. `_emit_synthetic_coach_feedback`: new kwarg `evidence_repo_signal_absent:
   bool = False` → written into the synthetic report dict. Comment at the
   kwarg: only the `_evidence_repo_gate` call site sets this True; all other
   callers leave it False (arch-review REC-1).
3. `_is_feedback_stalled`: schema-match marker via
   `_extract_absent_evidence_repo_signal(turn_record)`; when True → WARNING +
   `return False` WITHOUT appending to the history window. Bounded termination
   preserved: permanently-unrunnable exits `max_turns_exceeded`, never approve.

**CRITICAL-1 (arch review 2026-07-05, must-honour):**
`evidence_repo_signal_absent` is a TOP-LEVEL key in the synthetic report dict
(same level as `coach_primary_synthetic_feedback`), NOT nested inside
`issues`. `_extract_absent_evidence_repo_signal` reads
`turn_record.coach_result.report.get('evidence_repo_signal_absent', False)`.
If the key were placed inside `issues`, the extractor would silently never
fire and the stall would return with no test failure — the stall-detection
tests MUST assert the marker is read from the top-level dict key.

### Step 5 — feature_loader.py schema
`_validate_evidence_repos` (~463): accept optional `interpreter` (string);
reject non-string loudly.

## Test plan (~19-21 new, 2 replaced)

- test_evidence_repos.py: replace `test_pytest_command_pinned_to_venv_python`;
  update `test_non_pytest_command_runs_via_shell`. New:
  `TestResolveRepoInterpreter` (6), `TestRunRepoTestsInterpreterResolution` (3,
  incl. `test_worktree_venv_structurally_unreachable`),
  `TestCollectionImportErrorAbsent` (5, incl. real-subprocess exit-2 shape +
  veto + still-blocks).
- NEW tests/integration/orchestrator/test_sibling_venv_interpreter_regression.py
  (2): real `python -m venv` sibling with injected site-packages dep — the
  FEAT-10AC run-2 reproducer (AC-1). Assert the resolved interpreter IS the
  sibling's `.venv/bin/python` (arch-review REC-3), not just pass/fail.
- tests/unit/test_autobuild_stall_detection.py (3): absent-marker never stalls;
  ran-and-failed still stalls at 3 (control); gate sets flag only when pure-absent.
- tests/unit/test_feature_loader.py (2): interpreter accepted/rejected.
- test_coach_validator_evidence_repos.py (1): sibling pin wins over worktree venv.

## Files / LOC

| File | Delta |
|---|---|
| guardkit/orchestrator/evidence_repos.py | +95 / −25 |
| guardkit/orchestrator/autobuild.py | +45 |
| guardkit/orchestrator/quality_gates/coach_validator.py | +6 / −4 |
| guardkit/orchestrator/feature_loader.py | +8 |
| tests (5 files, 1 new) | ~+340 |

## Risks

- Genuine broken sibling import masked as "absent": acceptable — turn still
  blocks with the ImportError tail quoted; only the terminal label changes; zero
  tests ran so there is no test verdict to lose.
- Stale sibling `.venv` pinned: logs name the interpreter; remedy = the
  `interpreter:` field (why it takes precedence).
- AC-4: structurally protected (no `_venv_python` touch) + untouched
  interpreter-selection/resume-venv suites.
- Veto regex over-match biases toward ran-and-failed — the safe direction.
