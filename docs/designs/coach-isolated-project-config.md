# Coach isolated tests carry the project's configuration

**Status:** design only, 20 October 2026. Implementation waits for independent design acceptance.

**Candidate base:** `d628b822009fbf18bd137c6ae6f1a36c07c2875b` (`origin/main`).

## Problem

For a parallel wave, `CoachValidator._run_isolated_tests` copies the worktree and runs the project's declared test command in that copy. The copy deliberately excludes `.git` and the whole `.guardkit` directory. `_ISOLATION_NEVER_LINK` also prevents either directory from being linked back to the worktree.

That is correct for generated build state, but `.guardkit/config.yaml` is project input. A declared command in any language may read it while it runs. In the isolated copy the read currently fails because the file is absent. The command can therefore fail only in a parallel wave even though the project source is valid.

The command itself is already selected from the task's pinned declaration. This change does not reload or reinterpret the declaration. It only gives that command the same project configuration file it can read in the worktree.

## Rule

Keep excluding all of `.guardkit`, then copy one allowlisted file into the snapshot: the canonical `CONFIG_RELATIVE_PATH`, `.guardkit/config.yaml`.

The copy is a byte snapshot, never a link. This keeps `.guardkit/autobuild`, `.guardkit/autobuild-private`, `.guardkit/worktrees`, bootstrap records and reports out of the copied tree. The existing links to bootstrap-created environments (for example `.guardkit/buildenv`) remain supported; those dependencies are deliberately linked rather than copied. `.git` remains excluded and never linked.

Use a small helper called from `_run_isolated_tests` immediately after the ordinary source copy, before `_reach_into_snapshot` adds dependency links and before the command starts:

1. Look up the source path with `lstat`. `FileNotFoundError` and `NotADirectoryError` mean the optional project configuration is absent; return without creating `.guardkit` in the snapshot. This preserves the existing behavior for projects with no configuration file.
2. If the path exists, open it read-only with `O_NONBLOCK`, then check the opened descriptor with `fstat`. `FileNotFoundError` or `NotADirectoryError` from this open also means absence, matching the strict declaration loader (including a dangling source symlink). Other open errors, including a symlink loop, are refused. The opened object must be a regular file. This prevents a FIFO or device from hanging the Coach and closes the lookup/open race.
3. Preserve the current loader behavior for a source symlink whose target is a readable regular file: read the opened target, but write those bytes into a newly created regular destination file. The snapshot therefore cannot follow later changes to the source target.
4. Create the destination `.guardkit` directory if needed. Check it with `lstat`: it must be a real directory inside the snapshot, never a symlink. Tolerate an existing real directory. Open destination `config.yaml` exclusively and without following a final symlink, then write the captured bytes. Do not widen `_ISOLATION_SKIP_DIRS` or `_ISOLATION_NEVER_LINK`. Run the existing `_reach_into_snapshot` afterwards: nested bootstrap environments still link under the real directory, while its existing destination check prevents replacement of that directory by a link to the whole source `.guardkit`. If an unusual bootstrap layout needs the whole `.guardkit` directory, preserve the existing command-start fallback; do not link or copy the whole state directory to make it work.
5. If a path exists but cannot be opened, is not regular when opened, cannot be read, or cannot be written into the snapshot, stop before the declared command runs. Return the existing `check_could_not_run` outcome with a plain detail naming `.guardkit/config.yaml` and the copy error.

A required-configuration copy failure must not use the normal fallback that runs the command in the mutable worktree. Add one explicit result flag, defaulting to the current fallback behavior, and set it to refuse fallback only for this failure. The caller returns that `check_could_not_run` result directly. All other isolated-copy failures keep today's worktree fallback.

This is one file-specific boundary because `.guardkit/config.yaml` is the canonical project declaration already shared by the toolchain and launch loaders. Copying the directory, consulting ignore rules, inferring files from command text, or adding a configurable list would mix generated factory state into the test snapshot or create a second configuration system.

## Code changes

- `guardkit/orchestrator/quality_gates/coach_validator.py`
  - Import and reuse `CONFIG_RELATIVE_PATH`.
  - Add the bounded regular-file snapshot helper.
  - Invoke it while assembling the isolated copy.
  - Add the default-true worktree-fallback flag to `IndependentTestResult.could_not_run`; set it false only when this required snapshot cannot be made, and honor it at the parallel isolation caller.
- `tests/unit/test_coach_isolated_copy_location.py`
  - Add connected tests through the real isolated-copy and parallel-wave paths. Do not add a language-specific branch.

No factory test project, declaration loader, generated-state layout, or serial-wave path changes.

## Acceptance tests

Add these cases to `tests/unit/test_coach_isolated_copy_location.py`:

1. A real arbitrary shell command, with no Python invocation, reads a marker from `.guardkit/config.yaml` in the isolated copy. During the command it changes a regular file targeted by a source config symlink, then confirms the snapshot still has the original bytes and `test ! -L .guardkit/config.yaml` succeeds.
2. The same command confirms `.git`, `.guardkit/autobuild`, `.guardkit/autobuild-private`, `.guardkit/worktrees`, and a representative bootstrap-state file are absent. This proves the allowlist did not copy or link generated state.
3. With no `.guardkit/config.yaml`, the new helper adds nothing. Existing dependency links under `.guardkit` still work; an otherwise empty snapshot acquires no synthetic `.guardkit` merely because generated state exists in the worktree. Combine a regular config with a recorded `.guardkit/buildenv/bin/runner` and verify that the command reads the config and runs through that environment in the isolated copy. A bootstrap layout rooted at `.guardkit` must never replace the snapshot directory with a link; its existing command-start fallback remains available.
4. A source config symlink to a readable regular file succeeds as a regular, independent destination snapshot. A dangling source symlink behaves like an absent config, matching the strict loader. A symlink loop is a read failure. A destination `.guardkit` symlink is refused before the command runs.
5. A FIFO at the config path returns promptly as `check_could_not_run`; the command's marker is never written. This test has a short outer timeout so a blocking regression fails instead of hanging the suite.
6. An injected open/read/copy `OSError` returns the same plain `check_could_not_run` shape. Through `run_independent_tests`, neither this case nor the FIFO/symlink-loop case runs the command in the worktree. The existing fallback tests for unrelated isolation failures remain green.
7. The existing copy location, cleanup, Git ceiling, skipped-environment links, parallel routing, and could-not-run suites remain green.

Run from the candidate worktree on the estate test host through its scheduler, one process per command and without xdist. `GUARDKIT_TEST_PYTHON` names the main checkout's existing virtual-environment Python; the candidate is first on `PYTHONPATH`:

```sh
PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}" dell-test timeout 1800 "$GUARDKIT_TEST_PYTHON" -m pytest -p no:cacheprovider --no-cov -q tests/unit/test_coach_isolated_copy_location.py
PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}" dell-test timeout 1800 "$GUARDKIT_TEST_PYTHON" -m pytest -p no:cacheprovider --no-cov -q tests/unit/test_coach_check_could_not_run.py tests/unit/test_coach_parallel_isolation.py
```

Acceptance requires both commands to pass and the new connected tests to show that the shell command read only a regular snapshot of project configuration, saw no generated state or Git metadata, and never ran after a required-configuration copy failure.
