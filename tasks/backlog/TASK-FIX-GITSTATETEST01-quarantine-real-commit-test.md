---
id: TASK-FIX-GITSTATETEST01
title: test_git_state_helper integration test commits against the enclosing repo
status: backlog
task_type: bugfix
priority: medium
created: 2026-07-05
tags: [tests, hermeticity, git]
---

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
