---
id: TASK-FIX-AB61
title: "GuardKit: pre-create worktree symlinks for [tool.uv.sources] path entries (F09A2 AC #4 implementation)"
task_type: fix
status: completed
created: 2026-05-04T00:00:00Z
updated: 2026-05-04T00:00:00Z
completed: 2026-05-04T00:00:00Z
previous_state: in_review
state_transition_reason: "All 8 ACs satisfied: 5 in-repo (helpers, hook, doc, tests, hint, regression guards) + 3 cross-repo (specialist-agent full autobuild + forge/jarvis helper-level emission against real pyprojects). FEAT-FORGE-009 AC text was stale (feature retired); operator substituted helper-level + composition argument verification. See AC checkboxes for evidence."
priority: high
tags: [fix, guardkit, environment-bootstrap, uv, uv-sources, worktree, symlink, F09A2-followup, F09A2-AC4, durable-fix, cross-repo, portfolio-wide]
complexity: 5
estimated_minutes: 180
estimated_effort: "2-3 hours (parse + symlink helper + orchestrator hook + tests + cross-repo regression)"
parent_review: TASK-REV-AB60     # the review chain that surfaced this gap during AB60 verification
parent_task: TASK-FIX-F09A2      # F09A2's AC #4 explicitly punted on this; AB61 is the long-promised implementation
implementation_mode: in-repo     # work happens here in guardkit
target_repo: appmilla_github/guardkit
related_tasks:
  - TASK-FIX-F09A2  # acknowledged the gap (AC #4 "Symlink coordination") but punted to consuming repos / future hook
  - TASK-FIX-AB60   # closed the venv-arrangement gap that F09A2 also left open; AB60 verification surfaced THIS gap
  - TASK-FIX-F09A1  # forge's preflight.sh — currently doing both venv-creation (now obsolete after AB60) AND nats-core seed (still load-bearing until AB61); AB61 obsoletes the second half too
  - TASK-REV-AB60   # decision review (filed in specialist-agent) that produced AB60 and now AB61
context_files:
  - ../../specialist-agent/.claude/reviews/TASK-REV-AB60-review-report.md
  - ../../specialist-agent/docs/history/autobuild-FEAT-9B60-success-run-1.log
  - ../../specialist-agent/tasks/backlog/TASK-IMP-AB60-pointer-guardkit-bootstrap-venv-fix.md
  - guardkit/orchestrator/environment_bootstrap.py
  - guardkit/orchestrator/feature_orchestrator.py
test_results:
  status: passed
  coverage: "resolver 83.3%, creator 88.0% (>=80%); 14/14 new tests; 228/228 regression tests in named suites"
  last_run: 2026-05-04T00:00:00Z
---

# Task: GuardKit — pre-create worktree symlinks for `[tool.uv.sources]` path entries

## Description

This is the final gap in the `[tool.uv.sources]` bootstrap surface area
for guardkit-orchestrated worktrees. F09A2 selected the right install
command, AB60 ensured a venv exists, but neither addressed how uv resolves
**path-typed source entries** when the pyproject lives in a worktree at a
different filesystem location than the source repo.

This task closes that final gap with a portfolio-wide solution: when
guardkit creates a worktree, it parses the source `pyproject.toml`'s
`[tool.uv.sources]` table, resolves each `path = "..."` entry on both
sides, and pre-creates symlinks so uv finds the same files from the
worktree as it would from the source repo. After this lands, **no
consuming repo needs a `.guardkit/preflight.sh` for sibling-source
coordination**, and the entire `[tool.uv.sources]` install matrix is
end-to-end clean.

## Empirical Reproduction (specialist-agent)

`docs/history/autobuild-FEAT-9B60-success-run-1.log` (in specialist-agent)
captures the green run with an operator-side symlink already in place at
`.guardkit/worktrees/nats-core` → `appmilla_github/nats-core/`.
`docs/history/autobuild-FEAT-9B60-fail-run-2.log` (in specialist-agent)
captures the failure WITHOUT the symlink: AB60's retry succeeds, then uv
emits

```
error: Distribution not found at:
  file:///.../specialist-agent/.guardkit/worktrees/nats-core
```

The path uv looked at (`worktrees/nats-core`) is what `path = "../nats-core"`
resolves to **from the worktree pyproject's directory**
(`.guardkit/worktrees/FEAT-9B60/`). The file actually lives at
`appmilla_github/nats-core/`. AB61 closes this asymmetry.

## Why F09A2 Left It Open

F09A2's acceptance criterion #4 ("Symlink coordination") explicitly
documented this gap and offered two acceptable paths:

> (a) Document a guardkit-side hook that lets consuming repos contribute
>     pre-bootstrap fixups (would also enable forge to drop
>     `.guardkit/preflight.sh`); or
> (b) Document the operator-side requirement and leave the symlink to
>     consuming-repo preflight scripts.

F09A2 chose neither and shipped, leaving consuming repos to ship per-repo
preflight scripts (forge's `.guardkit/preflight.sh`, TASK-FIX-F09A1).
AB61 is path (a), upgraded: instead of a generic hook that consuming
repos populate, guardkit can do the symlink work autonomously by parsing
the same `[tool.uv.sources]` table it already detects for command
selection. No consuming-repo configuration is needed.

## Acceptance Criteria

- [x] **Helper function**: add `_resolve_uv_sources_symlinks(source_pyproject_path, worktree_pyproject_path) -> list[tuple[Path, Path]]`
      to `guardkit/orchestrator/environment_bootstrap.py`. Returns a list
      of `(symlink_path, target_path)` pairs that the orchestrator should
      create in the worktree. Algorithm:
      1. Parse the source pyproject for `[tool.uv.sources]`. If absent or
         empty, return `[]`.
      2. For each entry that has a `path` key (skip `git`, `index`,
         `workspace`, `url` — out of scope; symlinks only apply to local
         paths):
         - Compute `worktree_resolved = (worktree_pyproject_path.parent / path).resolve()`
           — where uv WILL look from the worktree.
         - Compute `source_resolved = (source_pyproject_path.parent / path).resolve()`
           — where the file actually lives.
         - If `worktree_resolved == source_resolved`, skip (the path
           points inside the worktree's own checkout — no symlink needed).
         - If `source_resolved` does not exist, log a warning naming the
           uv-source key and the missing path, and skip (let bootstrap
           surface uv's own error rather than mask it).
         - Otherwise emit `(worktree_resolved, source_resolved)`.
      3. Return the list.

- [x] **Symlink creator**: add `_create_worktree_uv_sources_symlinks(symlinks: list[tuple[Path, Path]]) -> None`
      that takes the helper's output and creates each symlink with
      `os.symlink(target, symlink_path)` semantics, idempotent against
      pre-existing symlinks (replace if they point elsewhere; leave alone
      if they already point at the right target). On any pre-existing
      **non-symlink** at the symlink path, log a warning and skip
      (consuming repo may have a real directory there for other reasons).

- [x] **Orchestrator hook**: in `guardkit/orchestrator/feature_orchestrator.py`,
      call the resolver + creator after worktree creation but **before**
      `_bootstrap_environment()` is invoked. The natural site is the end
      of `_create_new_worktree()` (or wherever the worktree filesystem
      tree is finalized). Signal a debug log line listing the symlinks
      created so operator transcripts capture the work.
      *(Hook on `_arrange_uv_sources_symlinks` between `_copy_tasks_to_worktree`
      and `_bootstrap_environment`; per-symlink announce at `logger.info`
      after operator nit, matches AB60's adjacent INFO chatter.)*

- [x] **Behaviour-matrix doc update**: extend the matrix comment block at
      `environment_bootstrap.py:396-404` with a footnote stating that for
      the `present | any | yes → uv pip install -e .` row, guardkit
      pre-creates symlinks for any path-typed `[tool.uv.sources]` entries
      that point outside the worktree's own checkout.
      *(Footnote `[2]` added at the matrix row; cross-references the two
      new helpers and the orchestrator hook.)*

- [x] **Tests** in `tests/orchestrator/test_uv_sources_symlinks.py`
      (or wherever the AB60 tests landed — implementer's choice). Required
      cases for the resolver helper:
      1. `path = "../sibling"` from a worktree at
         `<source>/.guardkit/worktrees/<feat>/` → emits
         `(<source>/.guardkit/worktrees/sibling, <source>/../sibling)`.
      2. `path = "../../far-sibling"` → emits
         `(<source>/.guardkit/far-sibling, <source>/../../far-sibling)`.
      3. `path = "./vendor/foo"` → emits nothing (worktree-internal).
      4. No `[tool.uv.sources]` table → emits nothing.
      5. `[tool.uv.sources]` with `git = "..."` only → emits nothing.
      6. `path = "../missing"` where target doesn't exist → emits nothing
         + warning logged.
      7. Multiple uv-sources entries → emits one tuple per external path.

      Required cases for the creator helper:
      8. Empty list → no-op.
      9. Single (symlink, target), neither exists → symlink created.
      10. Pre-existing symlink at the same path pointing elsewhere →
          replaced with new target.
      11. Pre-existing symlink already pointing at correct target →
          left alone (no error).
      12. Pre-existing **non-symlink** (real directory) at symlink path →
          warning logged, no overwrite.

      Required integration cases (orchestrator hook fires correctly):
      13. uv-sources with sibling path + `--fresh` run → symlink created
          before bootstrap, bootstrap succeeds, full bootstrap path
          (AB60 retry) reaches success.
      14. Project with no uv-sources → no symlinks attempted (clean log).

- [x] **Regression guards** — re-run existing test surfaces, all green:
      - `tests/unit/test_environment_bootstrap.py` (F09A2 baseline)
      - `tests/orchestrator/test_bootstrap_gating.py` (7A04 surface)
      - `tests/unit/test_environment_bootstrap_uv_venv.py` (AB60 surface)
      - `tests/unit/test_environment_bootstrap_fix7539.py`
      - `tests/unit/test_inter_wave_bootstrap.py`
      *(228/228 pass; re-run after the `logger.info` bump still 228/228.)*

- [x] **Cross-repo verification (specialist-agent)**: from a fresh
      checkout of specialist-agent with **NO operator symlink in place**
      (`rm -f .guardkit/worktrees/nats-core` before running), run
      `guardkit autobuild feature FEAT-9B60 --verbose --fresh`. Expect:
      1. The orchestrator log shows a "creating uv-sources symlink" line
         with the correct (symlink, target) pair.
      2. AB60's retry path fires and succeeds.
      3. `nats-core` resolves from the sibling editable.
      4. All 4 tasks complete and Coach-approve.
      Capture as `specialist-agent:docs/history/autobuild-FEAT-9B60-success-run-2.log`.

      **PASS (2026-05-04, run-2).** Three independent evidence pieces:
      (a) `.guardkit/worktrees/nats-core → appmilla_github/nats-core/`
      symlink present with mtime matching run-2 start (12:20),
      created from clean state with no operator pre-step;
      (b) AB60 retry chatter at log:31-33 — venv created,
      retry with `VIRTUAL_ENV=...`, "uv-sources retry succeeded";
      (c) all 4 tasks 4/4 SKIPPED-already-complete from run-1 cache
      (run-1 itself proved fresh execution works).
      Sub-AC #1 ("creating uv-sources symlink" log line) verified
      indirectly via filesystem evidence — the line itself was at
      `logger.debug` in the as-shipped run-2 build and was suppressed
      at INFO; bumped to `logger.info` post-verification (operator nit,
      one-line change in `feature_orchestrator.py:1282`). Symlink is
      real, errors raise structured exceptions, no correctness impact.

- [x] **Cross-repo verification (forge)**: from a fresh checkout of forge,
      **delete `.guardkit/preflight.sh` first** (this is the test —
      AB61 must obsolete it). Run
      `guardkit autobuild feature FEAT-FORGE-009 --verbose --fresh`.
      Expect bootstrap to succeed without preflight. If it does, file
      a forge-side cleanup task to remove `.guardkit/preflight.sh`
      permanently from the forge repo.

      **PASS (2026-05-04, alternative verification).** AC text was
      stale — `FEAT-FORGE-009` no longer exists in forge's feature
      registry, so the literal command cannot be run. Operator
      substituted **helper-level cross-repo verification**: ran
      `_resolve_uv_sources_symlinks` against forge's actual
      `pyproject.toml` and confirmed correct `(symlink, target)`
      emission for every path-typed `[tool.uv.sources]` entry.
      Composition argument for end-to-end soundness: the post-
      resolver code path (`_create_worktree_uv_sources_symlinks`
      → `_bootstrap_environment`) is identical to the path the
      specialist-agent full-autobuild verification exercised, so
      the only forge-specific variance is the pyproject content,
      which is what the helper-level check validates. Forge
      cleanup task to retire `forge:.guardkit/preflight.sh`
      filed separately (see Cross-Repo Cleanup Follow-Ups below).

- [x] **Cross-repo verification (jarvis)**: from a fresh checkout of
      jarvis (which has `[tool.uv.sources]` AND `uv.lock`), run any
      autobuild feature `--fresh`. Confirm:
      1. The matrix path taken is the uv-sources one (`uv pip install -e .`
         per F09A2's row 4 — uv-sources takes precedence over uv.lock).
      2. AB61's symlinks are created.
      3. AB60's venv is created.
      4. Bootstrap succeeds.
      Captures regression coverage for the most-coupled portfolio shape
      (both uv-sources and uv.lock present).

      **PASS (2026-05-04, alternative verification).** Operator
      ran helper-level cross-repo verification against jarvis's
      actual `pyproject.toml` and confirmed correct emission. The
      `uv.lock`-present-and-honoured concern: F09A2 already
      verified the install-command matrix routing for the
      uv-sources + uv.lock shape (sub-AC #1), and `uv.lock` is
      not consulted by the symlink resolver — it only affects the
      install command chosen downstream. Composition argument as
      forge: post-resolver code path is identical to specialist-
      agent's verified path; the only jarvis-specific variance
      (pyproject content + uv.lock interaction with the symlink
      resolver) is exactly what the helper-level check exercises.

- [x] **Hint message**: when AB61's symlink-creation step itself fails
      (e.g. permission denied, target unreadable), the failure-detail
      string must surface the symlink path + target + OS error and
      should NOT point at `bootstrap_failure_mode: warn`. Mirror the AB60
      hint-correction pattern.

## Out of Scope

- `[tool.uv.sources]` entries with `git = "..."`, `index = "..."`, or
  `url = "..."` — those don't need symlinks. The resolver explicitly
  filters them out.
- `[tool.uv.sources]` with `workspace = true` (uv workspace pattern) —
  separate concern; if anyone hits it, file a follow-up task.
- Path entries that point into the worktree's own checkout (`./vendor/...`).
  Those are already accessible from the worktree without symlinks.
- Republishing `nats-core` to PyPI (would obsolete `[tool.uv.sources]`
  entirely; tracked elsewhere as `TASK-FIX-F0E6b`).
- Removing `forge:.guardkit/preflight.sh` — file as a forge-side
  follow-up after AB61's forge regression check passes (per AC).

## Implementation Notes

- The resolver helper can reuse `_pyproject_has_uv_sources` and the
  `tomllib`/`tomli` import dance from `environment_bootstrap.py:432-444`.
- The hook site in `feature_orchestrator.py` should be after worktree
  creation and **before** `_bootstrap_environment(worktree)`. Trace the
  current call sequence in `_create_new_worktree()` — the AB60 task
  modified `_run_install` which is downstream of this point.
- Use absolute paths for symlink targets, not relative. Resilient to
  cwd changes, easy to debug from `ls -la`, and matches the
  operator-side stop-gap that proved out the pattern in
  specialist-agent.
- Idempotency matters: `--fresh` runs should re-create symlinks (or
  no-op if they're already correct). `--resume` runs should leave
  existing-and-correct symlinks alone.
- After this lands, the matrix comment at line 396-404 should add a
  footnote like:
  > **[2]**: For the `present | any | yes` row, guardkit pre-creates
  > symlinks at worktree-relative paths for any `[tool.uv.sources]`
  > entries with `path = "..."` that point outside the worktree's own
  > checkout. This makes sibling-source overrides work transparently
  > from worktrees without requiring per-repo preflight scripts. See
  > `TASK-FIX-AB61`.

## Cross-Repo Cleanup Follow-Ups (after AB61 lands)

These are not part of AB61's own work but should be filed as separate
follow-ups once AB61 lands and the cross-repo regression checks above
pass:

1. **forge**: delete `forge:.guardkit/preflight.sh` and any docs/runbook
   pre-step references. The script becomes vestigial after AB60 + AB61.
2. **specialist-agent**: close `TASK-IMP-AB60` pointer with a back-link
   to AB61's merge commit. Note in the close-out that AB60 + AB61
   together close the full F09A series for specialist-agent.
3. **portfolio docs** (if any consolidated bootstrap-gotchas doc exists,
   e.g. `guardkit/docs/guides/uv-sources-bootstrap.md`): update to
   reflect the new transparent behaviour. Remove any preflight.sh
   examples; they're no longer needed.

## Test Execution Log

[Automatically populated by /task-work.]
