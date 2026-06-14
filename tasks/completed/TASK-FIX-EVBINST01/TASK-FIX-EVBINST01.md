---
id: TASK-FIX-EVBINST01
title: Strip bootstrap install artefacts (.local / site-packages / .venv) from the evidence boundary (Player report + Coach claim audit)
status: completed
task_type: fix
created: 2026-06-14T11:30:00Z
updated: 2026-06-14T11:55:00Z
completed: 2026-06-14T11:55:00Z
completed_location: tasks/completed/TASK-FIX-EVBINST01/
priority: high
complexity: 3
related: [TASK-FIX-PCN, TASK-FIX-1B4C, TASK-FIX-BSEXTRAS01, FEAT-9DDE]
implementation_mode: direct
tags: [autobuild, evidence-boundary, claim-audit, honesty, files-modified, ghost-paths]
---

# Task: strip install artefacts from the Player-report / claim-audit evidence boundary

## Why this task exists

FEAT-9DDE **run 6**: the Player's `files_modified` carried **136 of 143**
entries under `.local/lib/python3.12/site-packages/_pytest/...` — pip-install
artefacts, not Player work. The Coach claim audit then emitted **~136 spurious
`claim_audit_unmodified` (should_fix) honesty records** (coach_turn_3.json: 144
issues, 142 honesty/should_fix), drowning the 2 real findings.

This is the **over-WIDE direction** of the evidence-boundary defect
(`.claude/rules/evidence-boundary-narrower-than-write-surface.md`): the
post-turn `git diff` aperture collects orchestrator-installed environment
artefacts and attributes them to the Player — the same union-merge ghost-path
mechanism as `.claude/rules/path-string-mismatch-is-not-dishonesty.md`.

## Root cause (mechanism, end-to-end)

1. Bootstrap writes pytest/its deps into the worktree `.local/site-packages`
   (PEP-668 `--user`/userbase fallback). Related to TASK-FIX-BSEXTRAS01.
2. The worktree inherits the repo `.gitignore`, which ignores `.venv/` (and
   `.venv-*/`, `.venv312/`) but **not `.local/`** (`.gitignore:55-57`).
3. The per-turn checkpoint `git add -A` (`worktree_checkpoints.py:471-474`)
   **commits** the non-ignored `.local/` tree (this is why the worktree
   `git status --porcelain` later showed 0 `.local` entries — already
   committed).
4. `_detect_git_changes` (`agent_invoker.py`) computes modified files via
   `git diff --name-only <baseline>`. `--exclude-standard` applies only to the
   untracked `git ls-files --others` branch, NOT the tracked `git diff`
   branch — so once `.local/` is committed, .gitignore offers no protection.
5. The union-merge folds those 136 paths into `report["files_modified"]`;
   `_strip_orchestrator_managed_paths` (the TASK-FIX-PCN filter) did not cover
   `.local/`/`site-packages/`/`.venv*/`, so they survived to the Coach.
6. Coach claim audit (`coach_verification.py`, which late-imports
   `_is_orchestrator_managed_path`) classifies each as `tracked_unmodified` →
   a `claim_audit_unmodified` should_fix Discrepancy.

## Fix

One surgical change: extend the existing
`_ORCHESTRATOR_MANAGED_PATH_PATTERNS` constant in
`guardkit/orchestrator/agent_invoker.py` with three anchored / segment-scoped
patterns:

```python
re.compile(r"^\.local/"),               # PEP-668 --user / userbase installs
re.compile(r"(?:.*/)?site-packages/"),  # any site-packages tree (match() needs (?:.*/)?)
re.compile(r"^\.venv[^/]*/"),           # .venv, .venv-*, .venv312
```

This one constant is consumed by **both** the Player-report writer
(`_strip_orchestrator_managed_paths`, final step before disk write) **and**
the Coach claim audit (late-imports `_is_orchestrator_managed_path`), so the
single change fixes both the `files_modified` pollution and the
`claim_audit_unmodified` noise. It catches already-committed/tracked artefacts
(the run-6 case) where a `.gitignore`-only fix cannot.

> **Implementation note:** the patterns are applied with `re.match` (anchored
> at start), so `site-packages/` needs the leading `(?:.*/)?` to match a
> mid-path segment like `lib/python3.12/site-packages/...` (caught a real bug
> in the first draft).

## Acceptance Criteria

- [x] `.local/...`, `**/site-packages/...`, `.venv*/...` are stripped from
      `files_modified` / `files_created` / `tests_written` / completion
      promises before the Player report reaches the Coach.
- [x] The same paths are dropped by the Coach claim audit (shared constant),
      so they generate no `claim_audit_unmodified` records.
- [x] Over-reach guard: real Player paths (`guardkit/cli/...`, `tests/...`,
      `.claude/task-plans/...`, `docs/local-setup.md`, `src/relocal/...`) pass
      through unchanged.

## Tests (all green)
- `tests/unit/test_orchestrator_induced_path_filter.py::TestInstallArtifactFilter` (3).
- Regression sweep: 595 passed / 7 skipped (induced-path-filter + neighbours).

## Companion (done)
Added `.local/` to the repo-root `.gitignore` (next to the `.venv*/` ignores)
so the checkpoint `git add -A` stops committing it at the source. The
pattern-filter remains the load-bearing fix (it alone catches already-tracked
+ absolute-form paths); the `.gitignore` change is defence-in-depth only.

## Evidence
- Preserved: `docs/retro/run6-evidence/player_turn_3.json` (143 files_modified,
  136 `.local`/site-packages), `coach_turn_3.json` (144 issues, 136 mention
  `.local`).
- Rules: `.claude/rules/evidence-boundary-narrower-than-write-surface.md`,
  `.claude/rules/path-string-mismatch-is-not-dishonesty.md`.
