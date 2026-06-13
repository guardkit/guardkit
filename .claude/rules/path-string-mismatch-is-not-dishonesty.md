# Path-string mismatch is not dishonesty

> **Source**: Seeded by TASK-DOC-1B4D (2026-05-06). Pair with the Graphiti
> design-rule node *"path-string-mismatch-is-not-dishonesty"* under
> `guardkit__project_decisions`, which has an `IS_INVERSE_SHAPE_OF` edge
> to *"absence-of-failure-is-not-success"*.

## The rule

A Coach gate that compares a Player-reported file-path string against the
filesystem with `Path.exists()` and treats every miss as a critical
honesty discrepancy is a false-red generator. When the path-string the
Coach checks was injected by the orchestrator's *own* mid-turn filesystem
mutation (not by the Player), and a peer path under the same task
identity does exist on disk, "path string does not exist" is not the
same as "Player lied about its work".

The rule applies to **any** boolean honesty gate downstream of a path
string drawn from the Player report, when an orchestrator-side component
is also free to mutate that report or the worktree behind the Player's
back. Two known instances are documented below; future incidents that
match the same shape should be folded under this rule rather than
retried as ad-hoc fixes.

## Why this rule exists

The class-of-defect emerged the same week Coach honesty verification was
wired into the deterministic path:

1. **2026-05-06** — FFC3 honesty false-fail
   ([TASK-REV-1B452](../../.claude/reviews/TASK-REV-1B452-review-report.md)
   v2). When `state_bridge.transition_to_design_approved`
   used `shutil.move()` to relocate `tasks/backlog/TASK-FFC3-005-*.md`
   to `tasks/design_approved/...`, the orchestrator's post-turn
   `git diff --name-only <baseline>` (no `-M` rename detection) reported
   the pre-move path as deleted. The union-merge at
   [`agent_invoker.py:2796-2797`](../../guardkit/orchestrator/agent_invoker.py)
   injected that ghost path into `report["files_modified"]` alongside the
   Player's honest production-code paths. CoachVerifier's
   `_verify_files_exist` ([`coach_verification.py:231-257`](../../guardkit/orchestrator/coach_verification.py))
   ran `Path.exists()` against the post-move worktree, the ghost path
   missed, a critical `file_existence` discrepancy fired, and the
   short-circuit at [`coach_validator.py:850-872`](../../guardkit/orchestrator/quality_gates/coach_validator.py)
   dropped 16 acceptance criteria unchecked. The Player had never
   written `tasks/backlog/...` to its `files_modified` list — the
   orchestrator had.

   **Fix landed in two layers, both load-bearing**:

   - **Layer 1** ([TASK-FIX-1B4A](../../tasks/completed/), commit
     `9d2fe52d`, 2026-05-06): `CoachVerifier._verify_files_exist` now
     consults `TaskStateBridge.canonical_path_for(task_id)` before
     emitting a critical `file_existence` discrepancy. When the Player's
     claimed string misses but the task's *current* canonical path
     resolves and exists, the discrepancy is suppressed and the
     resolution is recorded on `HonestyVerification.resolved_paths` for
     audit. Genuine missing files still fail honesty.
   - **Layer 3'** ([TASK-FIX-1B4C](../../tasks/completed/), commit
     `2c19aefc`, 2026-05-06): `state_bridge` now persists every
     `shutil.move` it performs to
     `.guardkit/autobuild/{task_id}/state_transitions.json` (atomic
     `.tmp + rename`). `AgentInvoker._create_player_report_from_task_work`
     subtracts `TaskStateBridge.orchestrator_induced_paths_for(task_id, repo_root)`
     from `report["files_modified"]` and `report["files_created"]`
     immediately after the union-merge, so the ghost path never reaches
     the Player report or the Coach. Either layer alone closes the FFC3
     reproducer; together they're defence-in-depth for the class.

Both fixes share a mechanism: **a path string draws from a source the
Player did not author (orchestrator-induced filesystem mutation observed
through git's no-rename diff), and a downstream verifier treats that
string as a Player honesty claim.** The defect surfaced as soon as the
deterministic Coach path actually started running CoachVerifier
([TASK-AB-FIX-INVAB1](../../tasks/completed/), commit `b9a45694`,
2026-05-06). It would have surfaced earlier had any test exercised the
post-baseline `state_bridge` interaction; that test gap was itself a
contributing factor.

## Symptom

- A Coach gate fires `decision: feedback` (turn-rejecting) on a turn
  where:
  - The Player's `task_work_results.json` `files_modified` /
    `files_created` lists contain only paths the Player actually wrote
    (production code, tests).
  - The merged `player_turn_N.json` `files_modified` list contains an
    *extra* path under `tasks/backlog/...` or `tasks/design_approved/...`
    that the Player did not author.
  - `coach_turn_N.json` shows exactly **one** `file_existence`
    discrepancy of `severity: "critical"`, with `claimed_path` matching
    the orchestrator-induced extra and `criteria_verification: []`
    (because the short-circuit fired before any AC was evaluated).
  - The peer task file under the *current* canonical path
    (e.g. `tasks/design_approved/TASK-X-foo.md`) exists on disk and is
    consistent with the task identity.
- Independent verification confirms tests pass and the production code
  paths the Player claims to have written do exist on disk and contain
  the expected work.
- The Coach's rationale is the verbatim string `"<N> honesty
  discrepancy/discrepancies. Adversarial verification overrode gate
  evaluation."` for `N == 1`, with the discrepancy resolving to a
  `tasks/...` path.

## Detection recipe

```bash
# 1. Grep for path-string equality checks in honesty-verification code
#    that do NOT consult task identity (no canonical_path_for, no
#    state_bridge resolution, no allow-list filter).
rg "Path\(.*worktree.*\) / .* \.exists\(\)" guardkit/orchestrator/
rg "_verify_files_exist|_verify_completion_promises_files_exist" \
   guardkit/orchestrator/coach_verification.py

# 2. Grep for orchestrator-side filesystem mutation that runs after
#    `_record_baseline` and before the Player SDK is invoked. Each
#    such mutation is a candidate ghost-path source.
rg "_record_baseline|_ensure_design_approved_state" \
   guardkit/orchestrator/agent_invoker.py
rg "shutil\.move|os\.rename|Path\.rename" guardkit/tasks/state_bridge.py

# 3. For every union-merge of `git_modified` into `report["files_modified"]`,
#    confirm that orchestrator-induced paths are filtered out before the
#    report reaches Coach.
rg "files_modified.*\|.*git_modified|original_modified \|" \
   guardkit/orchestrator/agent_invoker.py
rg "orchestrator_induced_paths_for" guardkit/

# 4. Grep for short-circuit branches that treat any single critical
#    file_existence discrepancy as turn-rejecting (`must_fix`) without
#    first attempting an identity-based resolution.
rg "honesty_issues|short[_-]?circuit" \
   guardkit/orchestrator/quality_gates/coach_validator.py

# 5. Cross-check against existing instances of this rule:
rg "path-string-mismatch" guardkit/ .claude/
```

## Remediation recipe

1. **Audit the boundary for orchestrator-induced filesystem mutations**.
   Any orchestrator-side component that mutates the worktree between
   `_record_baseline` and the Player SDK invocation is a candidate
   ghost-path source. Track those mutations explicitly (e.g.
   `state_transitions.json` per-task), and provide a public reader
   (e.g. `orchestrator_induced_paths_for(task_id)`) the union-merge can
   consult. Filter the orchestrator-induced set out of any field that
   will be attributed to the Player downstream.
2. **Add identity-based resolution before raising path-equality
   discrepancies**. Before emitting a critical `file_existence`
   discrepancy from a path-string miss, consult the task's *identity*
   (e.g. `state_bridge.canonical_path_for(task_id)`) to see if the
   claim resolves to a peer path under the same task. Record every
   resolution on the verification result (e.g. `resolved_paths`) so the
   audit trail in `coach_turn_N.json` shows the suppression. Refuse to
   resolve if no task identity is in scope (fail-open is preferable to
   silently masking a genuine honesty violation against another task).
3. **Demote single residual path-only discrepancies from `must_fix` to
   `should_fix`**. If a single `file_existence` discrepancy survives
   identity resolution and an orchestrator-side filter, the safe verdict
   is to surface it as `should_fix` feedback and let the gate evaluate
   the remaining ACs. Patterns (count > 1) and sophisticated lies
   (`promise_file_existence`, `test_result`, `test_count`) retain
   `must_fix` and short-circuit. The class is *one* path miss against
   a Player whose production-code claims are otherwise verifiable.
4. **Verify the resolution is identity-bounded**. The canonical-path
   lookup must consult only the validated task's identity. A claim
   referencing some other task's path must not be resolved away —
   that would mask a real cross-task honesty violation.
5. **Test the orchestrator-induced ghost case explicitly**. Every gate
   that compares Player path strings against the filesystem should
   have a regression test that:
   - records a baseline,
   - performs an orchestrator-induced `shutil.move` on a tracked file,
   - runs the gate against a synthetic Player report whose
     `files_modified` contains only honest production paths, and
   - asserts the gate does not fire `decision: feedback`.
6. **Document the new gate's identity surface** so future contributors
   know which `task_id` / `state_bridge` instance the gate consults
   and which mutations are filtered. The Layer-3' filter is narrow by
   construction (only `transition_to_design_approved` moves are
   recorded); broadening it is a separate architectural decision.

## Grep-able signature (for next agent)

```bash
# Active-hazard fingerprint: honesty gate path-equality with no identity
rg "Path\(.*worktree.*\) / .*\.exists\(\)" guardkit/orchestrator/coach_verification.py

# Ghost-path injection fingerprint: union-merge with no filter
rg -A 3 "original_modified \| git_modified" guardkit/orchestrator/agent_invoker.py

# Short-circuit fingerprint: any critical → return feedback, no demotion
rg -B 2 -A 8 "if honesty_issues:" guardkit/orchestrator/quality_gates/coach_validator.py

# Sibling-rule lookup (this rule)
rg "path-string-mismatch" .claude/rules/

# Sibling-rule lookup (false-green inverse)
rg "absence-of-failure" .claude/rules/
```

## Prior art

- **Sibling rule (false-green inverse)**:
  [`absence-of-failure-is-not-success.md`](absence-of-failure-is-not-success.md)
  — same shape (symptom + detection recipe + remediation recipe + grep
  signature), opposite direction. Both rules are instances of the
  shared meta-frame: *a binary verdict from a low-fidelity oracle that
  cannot distinguish "no signal" from "positive/negative signal"*. The
  false-green sibling guards against `count_failed == 0` approving when
  the count of attempts is also zero. This rule guards against
  `Path.exists() == False` rejecting when the path string was not
  authored by the Player and a peer path under the same identity does
  exist.
- **Sibling rule (collection-boundary instance)**:
  [`evidence-boundary-narrower-than-write-surface.md`](evidence-boundary-narrower-than-write-surface.md)
  — same meta-frame. This rule keeps a path miss from becoming a false-red
  when the orchestrator moved the file; the collection-boundary sibling keeps
  the *fix* for one of its directions (resolving a repo-qualified claim
  against a sibling repo root) from re-introducing a ghost-path false-red:
  unknown / undeclared repo-qualified claims fail open, exactly as this rule
  requires. Seeded by TASK-AB-XREPOEV01 (2026-06-13).
- **Pair fact in Graphiti** (`guardkit__project_decisions`): node
  *"path-string-mismatch-is-not-dishonesty"* with an
  `IS_INVERSE_SHAPE_OF` edge to *"absence-of-failure-is-not-success"*
  and citations to the two known fix commits enumerated above.
- **Architectural review report**:
  [`.claude/reviews/TASK-REV-1B452-review-report.md`](../../.claude/reviews/TASK-REV-1B452-review-report.md)
  v2 contains the C4 component diagram and four sequence diagrams that
  motivate this rule, including the boundary table that traced every
  data-flow link from `_record_baseline` to the short-circuit.
- **Originating ghost-path injection point**:
  [`agent_invoker.py:2796-2797`](../../guardkit/orchestrator/agent_invoker.py)
  (union-merge of `git_modified` into `report["files_modified"]`).
- **Originating mutation site**:
  [`state_bridge.py`](../../guardkit/tasks/state_bridge.py)
  (`shutil.move` in `_move_task_to_state`, called by
  `transition_to_design_approved`).
- **Originating exists() check**:
  [`coach_verification.py:231-257`](../../guardkit/orchestrator/coach_verification.py)
  (`_verify_files_exist`).

## When this rule triggers

- Before introducing a new Coach gate that reads any path-string field
  from the Player report and compares it against the filesystem.
- Before adding a new orchestrator-side component that mutates the
  worktree between `_record_baseline` and the Player SDK invocation.
- Before broadening the Layer-3' filter beyond
  `transition_to_design_approved`-induced moves to cover additional
  state_bridge mutations.
- During Phase 2.5 architectural review for any task that touches
  `coach_verification.py`, `coach_validator.py` honesty path,
  `agent_invoker.py` union-merge, or `state_bridge.py` filesystem
  mutation paths.
- During any diagnostic session investigating a "Coach rejected the
  turn but the production code on disk looks correct" report.

## What the rule does NOT cover

- Cases where the Player legitimately reports a path it did not write
  (e.g. it claims to have created `src/X.py` but never invoked
  `Edit`/`Write` on it). That is a real Player honesty violation; the
  identity-resolution step must not mask it. The rule is permissive
  only when an orchestrator-side mutation can be shown to be the path's
  source.
- Multiple-discrepancy cases (count > 1). A pattern of misses is not
  one ghost path; it is either Player dishonesty or a deeper fixture
  drift. The Layer-2 demotion only fires for *single* path-only
  discrepancies.
- Non-`file_existence` honesty categories
  (`promise_file_existence`, `test_result`, `test_count`,
  `claimed_test_pass_count`, etc.). Those continue to short-circuit on
  any critical discrepancy because they verify Player-authored
  semantic claims, not orchestrator-observable filesystem state.
- Honesty checks on completion promises
  ([`coach_verification.py:259-305`](../../guardkit/orchestrator/coach_verification.py)
  `_verify_completion_promises_files_exist`). The completion-promise
  field is Player-authored and not subject to orchestrator injection;
  the FEAT-6CC5 case that motivated that check is unrelated to this
  rule and remains `must_fix`.
- Genuine cross-task path leakage (a Player report claims a path that
  belongs to a different task). The identity-bounded resolution
  refuses to resolve outside the validated task; this case correctly
  remains a critical discrepancy.
