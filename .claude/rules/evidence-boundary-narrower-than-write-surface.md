# Evidence boundary narrower than the write surface

> **Source**: Seeded by TASK-AB-XREPOEV01 (2026-06-13, commit `0fadbd4f`).
> Pair with the Graphiti design-rule node *"evidence boundary narrower than
> write surface is an absent-signal instance"* under
> `guardkit__project_decisions`. Sibling of
> [`absence-of-failure-is-not-success.md`](absence-of-failure-is-not-success.md)
> (false-green inverse), [`path-string-mismatch-is-not-dishonesty.md`](path-string-mismatch-is-not-dishonesty.md)
> (false-red inverse), and [`harness-cancellation-contract.md`](harness-cancellation-contract.md)
> (same guardkit ↔ guardkitfactory cross-repo seam) — all four are instances
> of the broader meta-frame: *a binary verdict from a low-fidelity oracle that
> cannot distinguish "no signal" from "positive/negative signal"*.

## The rule

A Coach gate (or any orchestrator oracle) whose **evidence boundary is
spatially narrower than the task's write surface** is an absent-signal
generator. When a task can legitimately write *outside* the scope the
evidence loop collects from — most concretely, into a declared sibling repo
reached from the worktree via a symlink — the loop sees zero evidence for
that work and the gate reads "no signal" as a verdict. The evidence loop MUST
widen to cover the task's full declared write surface, **explicitly** (a
declared allow-list, never implicit scanning of arbitrary parent dirs).

This defect is distinct from its three siblings in one important way: those
three are *interpretation* defects (the oracle sees a signal — a zero count, a
path miss, a cancel no-op — and misreads it). This one is a *collection*
defect: the oracle never sees the work at all because its aperture is too
narrow. And uniquely, the same too-narrow boundary produces **both**
directions of error:

- **false-red** when the out-of-boundary work *is* the deliverable (the
  gate honestly rejects "no implementation provided"), and
- **false-green** when out-of-boundary work is *approved on the strength of
  in-boundary tests that secretly depend on it*, then never versioned.

The rule applies to **any** evidence-collection component scoped to a single
root: a post-turn `git diff`, a file-existence verifier, a checkpoint commit,
an independent test runner. Each must collect from every declared evidence
root, not just the worktree.

## Why this rule exists

The class-of-defect emerged the week the autobuild evidence loop met a task
whose deliverable lived in the sibling `guardkitfactory` repo:

1. **2026-06-12** — FEAT-C332 run 1 **false-red**. TASK-QAWE-001's deliverable
   (2,100+ lines, on-spec) landed in `guardkitfactory`, reached from the
   feature worktree via the `.guardkit/worktrees/guardkitfactory` symlink. The
   post-turn `git diff --name-only <baseline>` ran in the **guardkit worktree
   only**, so factory writes never reached `files_modified` / `files_created`.
   The Coach saw "0 files modified" and honestly rejected every turn with
   "No implementation provided". Two turns of identical evidence; the Player's
   factory WIP had to be salvaged from a stash and completed manually.

2. **2026-06-12** — FEAT-E2CB run 2 / TASK-BDDW-002 **false-green** (worse).
   The task wrote the real `ReqnrollPlugin.discover` / `CucumberJSPlugin.discover`
   routing logic into `guardkitfactory` via the same symlink. The Coach
   *approved* on guardkit-side tests that call the REAL factory `discover()`
   (only `subprocess.run` is patched) — tests that pass **only while the
   uncommitted factory edits sit in the editable-install working tree**.
   `/feature-complete` merged the guardkit half; the factory half was never
   committed anywhere — one `git clean` / `git checkout` in the factory away
   from breaking merged main.

Both incidents share a mechanism: **the orchestrator's evidence loop has a
narrower spatial boundary (the worktree) than the task's actual write surface
(worktree + a declared sibling repo).** The defect surfaced the moment a task
was *expected* to write outside the worktree; it would not appear for any
purely in-worktree task.

The fix (TASK-AB-XREPOEV01) widened the boundary via an explicit
`evidence_repos` declaration and a single-source-of-truth repo-qualified path
contract (`guardkit/orchestrator/evidence_repos.py`), threaded through the
post-turn diff, Coach honesty verification, checkpoints, and independent
tests.

## Symptom

The class surfaces in two opposite shapes, both rooted in the same too-narrow
boundary:

**False-red shape:**
- The Coach fires `decision: feedback` with the rationale *"No implementation
  provided"* / *"0 files modified"* on a turn where on-spec work demonstrably
  exists on disk **in a declared (or about-to-be-declared) sibling repo**.
- The Player's `task_work_results.json` `files_modified` / `files_created`
  lists are empty *for the worktree* but the sibling repo's working tree has
  uncommitted, on-spec changes.
- Independent inspection confirms the deliverable exists — just not under the
  worktree root the evidence loop scans.

**False-green shape:**
- The Coach `decision: approve`s a turn whose passing tests call real code in
  a sibling repo, where that sibling code exists only as **uncommitted
  working-tree edits**.
- After merge, the sibling repo's contribution is present in no commit on any
  branch; `git status` in the sibling shows the approved work as still-dirty
  (or it has been `git clean`ed away and the merged main now imports a symbol
  that no longer exists).

## Detection recipe

```bash
# 1. Evidence-loop git operations scoped to a single root. Every one is a
#    candidate too-narrow boundary if the task can write elsewhere.
rg -n "git diff --name-only|git ls-files --others" guardkit/orchestrator/
rg -n "cwd=self\.worktree_path|cwd=str\(self\.worktree_path\)" guardkit/orchestrator/

# 2. File-existence / staging checks anchored only at the worktree root.
rg -n "self\.worktree_path / " guardkit/orchestrator/coach_verification.py

# 3. Checkpoint commits / test runs scoped to the worktree only.
rg -n "git\", \"add\", \"-A\"|git_executor\.execute" guardkit/orchestrator/worktree_checkpoints.py

# 4. The declared write surface: any symlink the Player can reach out through,
#    and any evidence_repos declaration the loop must honour.
rg -n "evidence_repos|worktrees/guardkitfactory|os\.symlink" guardkit/ installer/

# 5. Confirm the contract is single-source-of-truth (producer + consumer
#    cannot drift) and that a seam test guards it.
rg -n "split_qualified|qualify\(|resolve_evidence_repos" guardkit/orchestrator/
rg -n "evidence_repos" tests/orchestrator/test_evidence_repos_seam.py

# 6. Cross-check against existing instances of the meta-class.
rg "evidence boundary narrower|absence-of-failure|path-string-mismatch" .claude/rules/
```

## Remediation recipe

1. **Declare the extra evidence surface explicitly; never scan implicitly.**
   A feature/task names its sibling evidence repos (`evidence_repos:
   [../guardkitfactory]`). Resolve them once, relative to the source repo
   root, following symlinks. An *undeclared* sibling write must stay invisible
   — implicit scanning of arbitrary parent dirs is a different hazard (it
   sweeps unrelated work into the report). This is the AC-003 invariant.
2. **Centralise the cross-boundary contract in one module.** The producer
   (the report writer) and every consumer (file-existence verifier, checkpoint
   manager, test runner) must route through one qualify/split/resolve API so
   the two halves cannot drift — the namespace-hygiene lesson. In GuardKit
   this is `guardkit/orchestrator/evidence_repos.py` and the `<repo>:<path>`
   repo-qualified scheme.
3. **Widen every arm of the evidence loop, not just the diff.** Closing only
   the false-red (merging sibling writes into the report) leaves the
   false-green open. The file-existence verifier must resolve qualified claims
   against the right repo root; the checkpoint must commit the sibling repo
   (or *explicitly* disclaim it); the independent test runner must be able to
   run the sibling's tests and surface the result.
4. **Keep unknown qualified claims fail-open** (per
   `path-string-mismatch-is-not-dishonesty`): a qualified claim naming an
   *undeclared* repo resolves to nothing and is skipped, never a new
   false-red.
5. **Keep a declared-but-unrunnable sibling test as absent signal**, surfaced
   as feedback, never a silent pass (per `absence-of-failure-is-not-success`).
6. **Add a loud cross-repo seam test.** A feature that declares
   `evidence_repos` against an orchestrator that has dropped support must fail
   in CI, not silently degrade to absent-signal. See
   `tests/orchestrator/test_evidence_repos_seam.py`.
7. **Bound any cross-repo git operation that holds a cross-process lock.** A
   sibling checkpoint commit runs under an `fcntl` lock the *whole* shared
   repo contends on; an unbounded `git` there deadlocks every task that shares
   it. Timeout it (`_EVIDENCE_GIT_TIMEOUT_S`).

## Grep-able signature (for next agent)

```bash
# Too-narrow-boundary fingerprint: evidence-loop git scoped only to worktree
rg -n "cwd=self\.worktree_path" guardkit/orchestrator/agent_invoker.py

# Widened-boundary fingerprint: per-repo evidence detection threaded in
rg -n "detect_all_repo_changes|qualified_paths_for_changes" guardkit/orchestrator/

# Both-coach-paths gate fingerprint (the false-green half must gate too)
rg -n "_evidence_repo_gate|run_evidence_repo_tests" guardkit/orchestrator/

# Seam-test fingerprint (fail-loud, not absent-signal)
rg -n "evidence_repos" tests/orchestrator/test_evidence_repos_seam.py

# Sibling-rule lookup (this rule + the family)
rg "evidence-boundary-narrower|absence-of-failure|path-string-mismatch|harness-cancellation" .claude/rules/
```

## Meta-frame

This rule and its three siblings are all instances of *a binary verdict from a
low-fidelity oracle that cannot distinguish "no signal" from
"positive/negative signal"*. Where they differ is **which part of the oracle
produces the spurious "no signal"**:

| Rule | Failure locus | Direction | Spurious "no signal" comes from… |
|---|---|---|---|
| `absence-of-failure-is-not-success` | interpretation | false-green | a zero counter read as a pass when zero attempts ran |
| `path-string-mismatch-is-not-dishonesty` | interpretation | false-red | a path miss read as a lie when the orchestrator moved the file |
| `harness-cancellation-contract` | dispatch | divergence | a cancel that no-ops on a substrate it wasn't written for |
| **`evidence-boundary-narrower-than-write-surface`** | **collection** | **both** | **work done outside the oracle's spatial aperture** |

The shared remediation is to pair the binary verdict with a positive-evidence
precondition. The other three pair it with a *logical* precondition (count of
attempts > 0; identity-based resolution; substrate-agnostic dispatch). This
one pairs it with a *spatial* precondition: the evidence aperture must cover
the declared write surface before any "no work here" verdict is trusted.

## Prior art

- **Sibling rule (false-green inverse direction)**:
  [`absence-of-failure-is-not-success.md`](absence-of-failure-is-not-success.md).
- **Sibling rule (false-red inverse direction)**:
  [`path-string-mismatch-is-not-dishonesty.md`](path-string-mismatch-is-not-dishonesty.md).
- **Sibling rule (same cross-repo seam, migrated-contract instance)**:
  [`harness-cancellation-contract.md`](harness-cancellation-contract.md) — the
  guardkit ↔ guardkitfactory boundary again; its cross-repo seam test
  (`tests/orchestrator/harness/test_xrepo_contract_seam.py`) is the CI-guard
  analogue of this rule's `tests/orchestrator/test_evidence_repos_seam.py`.
- **Sibling rule (single-source-of-truth contract)**:
  [`namespace-hygiene.md`](namespace-hygiene.md) — the broader "local decision
  touching an externally-defined contract must be audited against that
  contract" meta-rule. The repo-qualified `<repo>:<path>` scheme is exactly
  such a contract and is centralised in one module so producer and consumer
  cannot drift.
- **Pair fact in Graphiti** (`guardkit__project_decisions`): node *"evidence
  boundary narrower than write surface is an absent-signal instance"*.
- **Originating fix**: TASK-AB-XREPOEV01 (commit `0fadbd4f`, 2026-06-13).
  Central contract: `guardkit/orchestrator/evidence_repos.py`. Reproducers:
  `tests/integration/orchestrator/test_evidence_repos_false_red_regression.py`
  (false-red), `tests/unit/test_worktree_checkpoints_evidence.py` (the
  versioning half of the false-green).
- **Scope doc that hit it**:
  `docs/features/qa-verifier-wiring-probes-scope.md` §5.5.

## When this rule triggers

- Before introducing or modifying any evidence-collection component scoped to
  a single root (`agent_invoker` post-turn diff / `_record_baseline`,
  `coach_verification` file-existence checks, `worktree_checkpoints` commits,
  `coach_validator` independent test execution).
- Before authoring a task or feature whose deliverable is *expected* to land
  outside the autobuild worktree (a sibling repo, an editable-install
  dependency reached via symlink, a generated artefact in a parent dir).
- Before broadening or narrowing the `evidence_repos` resolution surface, or
  adding a new symlink the Player can write through.
- During Phase 2.5 architectural review for anything under
  `guardkit/orchestrator/` that reads or writes the evidence loop, or anything
  under `guardkitfactory/` reached across the repo split.
- During any diagnostic session investigating a "Coach rejected but the work
  exists on disk" report **or** a "Coach approved but the merged code is
  missing a dependency" report.

## What the rule does NOT cover

- **Implicit scanning of arbitrary parent directories.** Widening the boundary
  means honouring an *explicit* declaration, not sweeping every dir above the
  worktree. Undeclared sibling-repo writes must stay invisible (AC-003) — an
  over-wide boundary is its own hazard (it attributes unrelated work to the
  task).
- **In-worktree honesty defects.** A Player lying about a file under the
  worktree root is covered by the ordinary honesty path
  (`path-string-mismatch-is-not-dishonesty` governs the false-red side there).
- **Non-`file_existence` honesty categories** for repo-qualified claims still
  flow through their normal gates; the only change is *which root* the
  existence check resolves against.
- **Cross-task attribution inside a shared sibling repo** beyond the per-task
  baseline already recorded. Two parallel tasks writing the same sibling repo
  are attributed by each task's own pre-turn baseline; finer-grained
  attribution (e.g. per-file ownership) is out of scope.
