---
id: TASK-AB-XREPOEV01
title: Cross-repo evidence support for autobuild (Coach must see declared sibling-repo writes)
task_type: feature
status: completed
created: 2026-06-12T16:20:00Z
updated: 2026-06-13T00:00:00Z
completed: 2026-06-13T00:00:00Z
previous_state: in_review
state_transition_reason: "All 5 ACs verified; Phase-5 review findings fixed; gates passed (task-complete)"
completed_location: tasks/completed/TASK-AB-XREPOEV01/
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

- [x] AC-001: a task writing only to a declared sibling repo produces a
      Player report whose `files_modified`/`files_created` include the
      repo-qualified paths; the Coach can verify ACs against them.
      → `agent_invoker._create_player_report_from_task_work` merges
      `<repo>:<path>` paths; `CoachVerifier._verify_files_exist` /
      `_verify_completion_promises_files_exist` resolve them against the repo
      root. Tests: `test_evidence_repos_false_red_regression.py`.
- [x] AC-002: Coach independent tests can execute in the sibling repo and
      their results reach the evidence bundle.
      → `CoachValidator.run_evidence_repo_tests` +
      `CoachEvidenceBundle.evidence_repo_tests`; deterministic gate
      (`_evidence_repo_gate`) on BOTH primary and legacy Coach paths.
- [x] AC-003: undeclared sibling-repo writes remain invisible (no implicit
      scanning of arbitrary parent dirs).
      → only declared+resolved repos are baselined/diffed; empty by default.
      Test: `...::test_undeclared_repo_writes_stay_invisible`.
- [x] AC-004: turn checkpoint/restore covers (or explicitly disclaims)
      sibling-repo state.
      → commit form: `WorktreeCheckpointManager` per-repo commit + guarded
      per-repo rollback (`evidence_commits`). Tests:
      `test_worktree_checkpoints_evidence.py`.
- [x] AC-005: regression test reproducing the FEAT-C332 run-1 false-red:
      synthetic task whose only writes are in a declared sibling repo must
      NOT be rejected as "no implementation provided".
      → `test_evidence_repos_false_red_regression.py::TestSiblingRepoOnlyFalseRedRegression`.

## Implementation summary (2026-06-13, task-work)

**Scope chosen:** Full — all 5 ACs incl. per-repo Coach test execution (AC-002)
and per-repo checkpoint commits (AC-004 commit form).

**Central contract** (single source of truth, per namespace-hygiene):
`guardkit/orchestrator/evidence_repos.py` — repo-qualified path scheme
`<repo>:<path>` (`qualify`/`split_qualified`/`resolve_qualified_path`),
`EvidenceRepo`, `resolve_evidence_repos` (relative to source repo root,
follows symlinks, AC-003 fail-safe), per-repo git baseline+diff,
`run_repo_tests`, and `evidence_repo_tests_blocking_reason`
(absence-of-failure: a declared-but-unrunnable suite blocks, never silently
passes).

**Declaration:** `Feature.evidence_repos` (feature YAML, validated) and
single-task frontmatter fallback. Resolved once per feature in
`FeatureOrchestrator._setup_phase`, threaded to every per-task
`AutoBuildOrchestrator` → `AgentInvoker` / `CoachValidator` /
`WorktreeCheckpointManager`.

**Rule adherence:**
- `path-string-mismatch-is-not-dishonesty`: unknown/unresolvable repo-qualified
  claims are fail-open (skipped), never a new false-red; worktree-specific
  audits (`_verify_claims_were_staged`) drop qualified paths.
- `absence-of-failure-is-not-success`: unrunnable sibling tests are feedback,
  not approval.
- `namespace-hygiene` / `harness-cancellation-contract`: cross-repo seam test
  (`test_evidence_repos_seam.py`) fails loudly in CI if any wiring link is
  removed.

**Code review (Phase 5):** independent review found and FIXED a CRITICAL
(Coach's own honesty `CoachVerifier` in `coach_validator._verify_honesty`
lacked `evidence_repos` → sibling-file lies undetected), a HIGH (AC-002 gate
absent on the legacy `GUARDKIT_COACH_LEGACY=1` path → factored into the shared
`_evidence_repo_gate`), a HIGH (unbounded sibling git commit under an fcntl
lock → `_EVIDENCE_GIT_TIMEOUT_S` timeout), and a MEDIUM (rollback divergence
logging). All guarded by seam/behavioural tests.

**Tests:** 64 new tests pass; new module at 88% line coverage. Zero regressions
(the 16 pre-existing orchestrator failures — drifted prompt-token counts,
unrelated langgraph/SDK-stream/BDD tests — fail identically on baseline).

## References

- Run log: `.guardkit/autobuild/FEAT-C332-run1-stdout.log`
- Coach verdicts: `.guardkit/worktrees/FEAT-C332/.guardkit/autobuild/TASK-QAWE-001/`
- Scope doc that hit this: `docs/features/qa-verifier-wiring-probes-scope.md` §5.5
- Sibling rules: `.claude/rules/absence-of-failure-is-not-success.md`,
  `.claude/rules/harness-cancellation-contract.md`,
  `.claude/rules/namespace-hygiene.md`
