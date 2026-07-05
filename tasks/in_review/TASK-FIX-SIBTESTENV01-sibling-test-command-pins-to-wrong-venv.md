---
id: TASK-FIX-SIBTESTENV01
title: Sibling evidence-repo test_command pins to the guardkit worktree venv, not the sibling's environment
task_type: fix
priority: high
status: in_review
updated: 2026-07-05T15:30:00+01:00
previous_state: backlog
state_transition_reason: "Automatic transition for task-work execution"
created: 2026-07-04T20:15:00+01:00
tags: [autobuild, evidence-repos, environment, false-red]
---

# Task: Sibling test_command interpreter resolution is substrate-blind to the sibling

## Incident (FEAT-10AC run 2, 2026-07-04)

A declared evidence repo with `test_command: python -m pytest tests/wiring -q`
failed **exit 2 (collection ImportError) every turn** → three ran-and-failed
sibling signals → `UNRECOVERABLE_STALL` — while the same suite passed green
(96 passed, 1.3s) in the sibling's own environment.

**Mechanism:** `_build_repo_test_argv`
(`guardkit/orchestrator/evidence_repos.py`) rewrites a bare `pytest`/`python`
head to run under `venv_python` — which is the **guardkit worktree venv**
(mirroring TASK-FIX-COACHPYENV). Correct for worktree tests; wrong for a
sibling repo: the worktree venv cannot import the sibling package or its deps
(here `guardkitfactory` + `tree_sitter`), so the pinned interpreter is
guaranteed-broken for any sibling with its own dependency set. The signal was
"ran and failed" in the *wrong* environment — a mis-environmented oracle, not
a deliverable defect.

This is the interpreter-resolution analogue of
`.claude/rules/watchdog-activity-signal-must-be-substrate-aware.md`: a
mechanism paired with one substrate (the worktree venv) silently mis-fires on
a second substrate (the sibling repo) it was never written for.

## Fix shape

In `run_evidence_repo_tests` / `_build_repo_test_argv`: resolve the pinning
interpreter **per repo**, preferring in order:

1. `repo.root / .venv/bin/python` when it exists (the sibling's own venv);
2. an explicit `interpreter:` field on the evidence-repo mapping (schema
   addition, optional);
3. fall back to running the command verbatim via shell in `cwd=repo.root`
   (NO pinning to the guardkit worktree venv — that fallback is the defect).

A command that cannot run should surface as ABSENT (`ran=False`), never as
ran-and-failed — exit 2 with an ImportError-in-collection signature from a
mis-resolved interpreter is a runner error, not a test failure (the
`absence-of-failure` family; compare `bdd_runner`'s `_PYTEST_EXIT_TIMEOUT` /
"not found" handling).

## Acceptance criteria

- [x] AC-1: sibling repo with its own `.venv` → bare `pytest`/`python`
  commands pin to `repo.root/.venv/bin/python`; reproducer proves the
  FEAT-10AC run-2 command now passes.
- [x] AC-2: no sibling venv → command runs verbatim via shell in the repo
  root; never pinned to the guardkit worktree venv.
- [x] AC-3: collection-error exit (2/3/4 with ImportError signature) from a
  pinning mismatch surfaces as `ran=False` absent signal (feedback,
  unverified), not ran-and-failed — and therefore cannot stack into
  `unrecoverable_stall`.
- [x] AC-4: existing worktree-side interpreter pinning (TASK-FIX-COACHPYENV)
  unchanged; all existing evidence-repos tests green.

## Workaround in the field (until fixed)

Declare the sibling `test_command` with an **absolute interpreter path**
(does not match the bare-head rewrite, runs verbatim):
`/abs/path/to/sibling/.venv/bin/python -m pytest tests/... -q` — applied to
`.guardkit/features/FEAT-10AC.yaml` for run 3.

## Related

- FEAT-10AC run 2 log: `.guardkit/autobuild/FEAT-10AC-run2-stdout.log`
- `.claude/rules/evidence-boundary-narrower-than-write-surface.md` (the
  sibling-signal machinery this hardens)
- TASK-FIX-XREPOPROM01 (run 1's false-red — the companion incident)

## Resolution (2026-07-05, /task-work)

Implemented per `docs/state/TASK-FIX-SIBTESTENV01/implementation_plan.md`
(arch review 82/100 approve-with-recommendations; CRITICAL-1 honoured;
code review APPROVE, 9/9 checklist).

- Per-repo interpreter resolution: explicit `interpreter:` field (new
  optional evidence-repo mapping key, validated in `feature_loader`) >
  `probe_worktree_venv(repo.root)` (reused from `environment_bootstrap`) >
  verbatim shell in `cwd=repo.root`. `venv_python` REMOVED from
  `run_repo_tests`/`run_all_repo_tests` — the worktree venv is structurally
  unreachable from the sibling path (AC-2 pinned by test).
- AC-3: exit 2/3/4 + ImportError-marker + tests-ran-veto classifier →
  `ran=False` absent (still blocks the turn); feedback-stall immunity via
  top-level `evidence_repo_signal_absent` synthetic-report key —
  `_is_feedback_stalled` excludes pure-absent sibling turns from the tally
  (the FEAT-10AC run-2 stall was `_is_feedback_stalled`, not checkpoints);
  mixed failed+unrunnable stays stall-stackable; bounded termination via
  max_turns preserved.
- Verification: 292 passed / 6 skipped across all affected + AC-4 suites;
  broader orchestrator/unit sweep failures (23+2) all reproduce on pristine
  HEAD (pre-existing). FEAT-10AC run-2 reproducer: real sibling venv with
  injected dep — caller interpreter provably cannot import it, sibling run
  passes, resolved interpreter asserted to be `sibling/.venv/bin/python`.
- Known residual (out of scope, pre-existing): `_build_repo_test_argv`
  uses naive `str.split()` — quoted args never survive argv pinning.
  Mitigated by verbatim-shell fallback + `interpreter:` escape hatch;
  upgrade to `shlex.split()` only if quoted test_commands become real.
