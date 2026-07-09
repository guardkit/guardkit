---
id: TASK-FIX-GITSTATETEST01
title: test_git_state_helper integration test commits against the enclosing repo
status: completed
task_type: bugfix
priority: medium
created: 2026-07-05
closed: 2026-07-09
closed_by: WS3-S1 (L17)
tags: [tests, hermeticity, git]
---

> **CLOSED 2026-07-09 (WS3-S1, L17) — implemented.** Fixed by a module-wide
> autouse fixture `_isolated_git_repo` in `tests/unit/test_git_state_helper.py`
> that chdir's EVERY test into a throwaway `tmp_path` git repo (identity +
> `commit.gpgsign=false` configured, initial commit), so the real
> `git rev-parse` / `git add` / bare `git commit` in `git_state_helper` can only
> ever touch that temp repo. The scope was wider than the one named test:
> `commit_state_files` runs a bare `git commit` (no pathspec → commits the whole
> index), so the two `TestCommitStateFiles` real-commit tests and the
> `resolve_state_dir` tests dirtied the enclosing repo too — all now isolated.
> Added `test_workflow_leaves_an_outer_repo_index_and_head_untouched` pinning
> the acceptance criterion (a second repo with staged work survives the workflow
> untouched). Also removed the pre-existing tracked pollution
> `docs/state/TASK-TEST-WORKFLOW/test_state.txt` (committed by the old buggy test
> in `1b701954`, "Test workflow commit"). Verified: a full
> `pytest tests/unit/test_git_state_helper.py` with a file deliberately staged in
> the enclosing repo leaves its index + HEAD untouched (26 passed).

# Quarantine the real-commit git test

`tests/unit/test_git_state_helper.py::TestIntegrationScenarios::
test_complete_workflow_creates_and_commits_state` runs real `git add`/`git
commit` against the ENCLOSING repository during any full-suite run. During the
FEAT-ABL-001 hand-finish it swept an agent's staged work into a junk commit
("Save state for TASK-031") that had to be reset (see the hand-finish workflow
report, 2026-07-05, and `docs/retro/abl001-run3-*`). It also dirties
`.guardkit/memory-query-log.jsonl` and `docs/state/TASK-TEST-WORKFLOW/`.

Fix: run it against a temporary repo (tmp_path git init), or mark it
integration/quarantined out of the default unit run.

Acceptance: a full `pytest tests/unit -q` with files deliberately staged in
the repo leaves the index and HEAD untouched.
