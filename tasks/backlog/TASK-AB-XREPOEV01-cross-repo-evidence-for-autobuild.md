---
id: TASK-AB-XREPOEV01
title: Cross-repo evidence support for autobuild (Coach must see declared sibling-repo writes)
task_type: feature
status: backlog
created: 2026-06-12T16:20:00Z
priority: high
tags: [autobuild, coach, evidence, cross-repo, guardkitfactory]
complexity: 7
---

# Task: Cross-repo evidence support for autobuild

## Problem (observed FEAT-C332 run 1, 2026-06-12)

TASK-QAWE-001's deliverable lands in **guardkitfactory** (reached from the
feature worktree via the `.guardkit/worktrees/guardkitfactory` symlink), but
the orchestrator's evidence loop is scoped to the **guardkit worktree only**:

- The post-turn `git diff --name-only <baseline>` runs in the guardkit
  worktree, so factory-side writes never reach `files_modified` /
  `files_created` in the Player report.
- The Coach's independent-test gate and AC verification therefore see
  "0 files modified" and honestly reject every turn with "No implementation
  provided" — while 2,100+ lines of on-spec work sit in the factory repo.
- Turn checkpoints (`worktree_checkpoints`) also commit only guardkit-side
  files, so factory work is unrecoverable from checkpoints.

Two turns of identical evidence in
`.guardkit/autobuild/FEAT-C332-run1-stdout.log` and
`.guardkit/worktrees/FEAT-C332/.guardkit/autobuild/TASK-QAWE-001/coach_turn_{1,2}.json`.
The Player's factory WIP was salvaged to a guardkitfactory stash
("Player WIP TASK-QAWE-001 turns 1-2") and completed manually.

**Second instance (worse — a false-GREEN-adjacent hazard, found 2026-06-12):**
TASK-BDDW-002 (FEAT-E2CB run 2, APPROVED) wrote its factory half — the real
`ReqnrollPlugin.discover` / `CucumberJSPlugin.discover` routing logic — into
guardkitfactory via the same symlink. The Coach approved on guardkit-side
tests (`tests/unit/orchestrator/quality_gates/test_bdd_multi_stack_routing.py`)
that call the REAL factory `discover()` (only `subprocess.run` is patched), so
those merged tests pass ONLY while the uncommitted factory edits sit in the
editable-install working tree. `/feature-complete` merged the guardkit half;
the factory half was never committed anywhere — one `git clean`/`git checkout`
in the factory away from breaking merged main. The evidence gap thus produces
BOTH false-reds (QAWE-001) and silently-unversioned approved work (BDDW-002).

This is another instance of the absent-signal meta-class
(`.claude/rules/absence-of-failure-is-not-success.md` family): an oracle
whose **evidence boundary is narrower than the task's write surface**
generates false-reds for out-of-boundary work. Sibling of
`harness-cancellation-contract.md` (cross-repo seam) — the guardkit ↔
guardkitfactory boundary strikes again.

## Proposed shape

1. Feature YAML (or task frontmatter) declares additional evidence repos,
   e.g. `evidence_repos: [../guardkitfactory]` — explicit, never implicit.
2. `_record_baseline` records a baseline per declared repo;
   the post-turn diff merges per-repo `git_modified` sets into the Player
   report with repo-qualified paths (e.g. `guardkitfactory:src/...`).
3. CoachVerifier `_verify_files_exist` resolves repo-qualified claims
   against the right root (respect
   `.claude/rules/path-string-mismatch-is-not-dishonesty.md` — do not
   create a new ghost-path false-red source).
4. Turn checkpoints either commit per-repo (preferred: a checkpoint branch
   in each declared repo) or explicitly log that sibling-repo state is NOT
   checkpointed.
5. Coach independent tests may need a per-repo test command (factory tests
   run with the factory's pytest, guardkit tests with the worktree venv).
6. Per `.claude/rules/namespace-hygiene.md` prior art: add a seam test so
   a feature declaring `evidence_repos` fails loudly (not silently
   absent-signal) when the orchestrator version doesn't support it.

## Acceptance criteria

- [ ] AC-001: a task writing only to a declared sibling repo produces a
      Player report whose `files_modified`/`files_created` include the
      repo-qualified paths; the Coach can verify ACs against them.
- [ ] AC-002: Coach independent tests can execute in the sibling repo and
      their results reach the evidence bundle.
- [ ] AC-003: undeclared sibling-repo writes remain invisible (no implicit
      scanning of arbitrary parent dirs).
- [ ] AC-004: turn checkpoint/restore covers (or explicitly disclaims)
      sibling-repo state.
- [ ] AC-005: regression test reproducing the FEAT-C332 run-1 false-red:
      synthetic task whose only writes are in a declared sibling repo must
      NOT be rejected as "no implementation provided".

## References

- Run log: `.guardkit/autobuild/FEAT-C332-run1-stdout.log`
- Coach verdicts: `.guardkit/worktrees/FEAT-C332/.guardkit/autobuild/TASK-QAWE-001/`
- Scope doc that hit this: `docs/features/qa-verifier-wiring-probes-scope.md` §5.5
- Sibling rules: `.claude/rules/absence-of-failure-is-not-success.md`,
  `.claude/rules/harness-cancellation-contract.md`,
  `.claude/rules/namespace-hygiene.md`
