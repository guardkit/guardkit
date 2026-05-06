---
id: TASK-REV-FFC6
title: "Review: autobuild bootstrap leaks worktree path into parent venv editable install"
status: review_complete
created: 2026-05-06T00:00:00Z
updated: 2026-05-06T00:00:00Z
priority: high
task_type: review
review_mode: architectural
review_depth: standard
tags: [autobuild, environment-bootstrap, editable-install, worktree, venv, ffc3-bug-4]
complexity: 6
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: architectural
  depth: comprehensive
  score: 62
  findings_count: 11
  recommendations_count: 3
  decision: refactor
  layers_to_ship: [1, 3]
  layers_to_skip: [2]
  test_invariant_fix_required: true
  report_path: .claude/reviews/TASK-REV-FFC6-review-report.md
  completed_at: 2026-05-06T00:00:00Z
  revisions:
    - 2026-05-06 v1: initial review (standard depth, 7 findings)
    - 2026-05-06 v2: revised comprehensive (11 findings + C4 + 6 sequence diagrams; surfaced F2/F3 additional leak paths and F5 test-encodes-leak)
---

# Task: Review — autobuild bootstrap leaks worktree path into parent venv editable install

## Description

Bug 4 of the FEAT-FFC3 incident series (companion to TASK-REV-1B452, TASK-REV-FFC4, TASK-REV-FFC5).
Discovered 2026-05-06 after `/feature-complete FEAT-FFC3` ran the standard worktree cleanup.

**Source incident**: [`autobuild-FFC3-editable-install-leak-incident.md`](../../../specialist-agent/docs/history/autobuild-FFC3-editable-install-leak-incident.md)

**Symptom (real-world consequence)**: After `/feature-complete` cleanly merged FEAT-FFC3 and removed
the worktree at `.guardkit/worktrees/FEAT-FFC3/`, three Claude Desktop MCP servers
(`architect-agent`, `product-owner-agent`, `study-tutor`) failed to start on the next Claude Desktop
restart. All three crashed at `from specialist_agent.cli.main import cli` with `ModuleNotFoundError`.

**Root cause** (per incident report): the autobuild's `environment_bootstrap` step ran `uv pip install -e .`
from the worktree directory while the **parent project's** `.venv` was active. That wrote the worktree's
`src/` path into the parent venv's editable `.pth` file:

```
$ cat .venv/lib/python3.14/site-packages/_editable_impl_specialist_agent.pth
/Users/.../specialist-agent/.guardkit/worktrees/FEAT-FFC3/src
```

The autobuild log itself acknowledged the unsafe state but proceeded:

```
INFO:guardkit.orchestrator.environment_bootstrap:
  Bootstrap: install ran against parent venv;
  venv_python set to sys.executable=/usr/local/bin/python3
```

Everything worked while the worktree existed. `/feature-complete`'s worktree cleanup then deleted the
referenced directory, leaving the parent venv pointing at a deleted path. The breakage is silent — no
error at autobuild time, no error at `/feature-complete` time — and cascades across every process that
later uses that venv (Claude Desktop MCPs, IDE Python interpreters, shell scripts, cron jobs).

**Why this is high severity**:
1. The user did the right thing (ran `/feature-complete`) and was punished minutes later.
2. The orchestrator detected the unsafe state ("install ran against parent venv") and chose to proceed.
3. Failure mode looks unrelated to the autobuild — high triage cost.
4. Cascades across processes using the same venv.

## Context

**Affected component**: `guardkit.orchestrator.environment_bootstrap` (the `uv pip install -e .` step at
autobuild startup).

**Companion incidents from same FFC3 run**:
- [TASK-REV-1B452](TASK-REV-1B452-honesty-verification-false-fail-after-state-bridge-move.md) — Bug 1: honesty path-mismatch false fail
- [TASK-REV-FFC4](TASK-REV-FFC4-record-honesty-nonetype-crash.md) — Bug 2: `_record_honesty()` NoneType crash
- [TASK-REV-FFC5](TASK-REV-FFC5-resume-fully-completed-feature.md) — Bug 3: `--resume`-on-all-completed
- This task — Bug 4: editable install leak

**Manual repair required by users hitting this**:
```bash
cd /path/to/parent/project
uv pip install -e . --no-deps
# Then restart Claude Desktop / IDE / language servers
```

## Suggested Fix Layers (from incident report — to be validated during review)

The incident report proposes three layers in priority order. Layer 1 alone resolves the bug; Layers 2
and 3 are progressively weaker fallbacks. Review should decide which layer(s) to ship.

### Layer 1 (load-bearing) — worktree-local venv

Bootstrap creates and uses `<worktree>/.venv` for `uv pip install -e .`. Venv lives and dies with the
worktree. Never write to the parent project's `.venv`.

```python
def bootstrap(worktree_path: Path) -> EnvironmentInfo:
    worktree_venv = worktree_path / ".venv"
    if not worktree_venv.exists():
        subprocess.run(["uv", "venv", str(worktree_venv)], check=True)
    subprocess.run(
        ["uv", "pip", "install", "-e", str(worktree_path)],
        env={**os.environ, "VIRTUAL_ENV": str(worktree_venv)},
        cwd=worktree_path,
        check=True,
    )
    return EnvironmentInfo(
        venv_python=worktree_venv / "bin" / "python",
        installed_locations=[worktree_venv],
    )
```

### Layer 2 (backstop) — repoint parent venv at `/feature-complete`

If parent venv must be touched, `/feature-complete`'s post-merge step re-runs `uv pip install -e .`
from the post-merge parent root before deleting the worktree. Strictly weaker — does not protect
manual `git worktree remove` users.

### Layer 3 (minimum mitigation) — detect-and-warn at finalization

Read every editable `.pth` under known venvs; warn if any point into the about-to-be-deleted worktree;
print a one-line repair command. Mitigation only.

## Acceptance Criteria (proposed — review must validate)

- [ ] Reproduction confirmed against current `main`: spin up an autobuild against a project with a
      parent `.venv`, run a no-op feature through `/feature-build` + `/feature-complete`, then verify
      `<parent>/.venv/bin/python -c "import <pkg>"` exits non-zero.
- [ ] Architectural review of `guardkit/orchestrator/environment_bootstrap.py` and the
      `/feature-complete` finalization path identifies the exact code path that selects which venv
      receives the editable install.
- [ ] Decision recorded on which Layer(s) to ship (1 alone vs. 1+3 vs. 2+3 vs. all three) with
      rationale tied to scope cost, regression risk, and protection coverage.
- [ ] Outcome of review is either:
      (a) An implementation task (or feature, if multi-task) with a concrete plan and dependencies
          mapped, or
      (b) A documented `wontfix` decision with rationale.
- [ ] Regression test specified: spin up an autobuild against a project with a parent `.venv`,
      run a no-op feature through `/feature-build` + `/feature-complete`, then assert
      `<parent>/.venv/bin/python -c "import <pkg>"` exits 0.
- [ ] Cross-check whether [TASK-FIX-A7B6](TASK-FIX-A7B6-bootstrap-install-optional-extras.md)
      already touches this code path; if so, sequence the fixes to avoid merge conflict.

## Review Scope

**In scope**:
- `guardkit/orchestrator/environment_bootstrap.py` and the venv-selection logic.
- The `/feature-complete` finalization path (worktree removal sequencing).
- Existing `installed_locations` / `venv_python` plumbing — does any downstream consumer rely on the
  parent venv being touched? Coach pytest runs in particular.
- Cross-template impact: does the same bootstrap run for non-Python templates (TypeScript, .NET)?
  If yes, are there equivalent leak modes (e.g. `npm link`, `dotnet add reference`)?

**Out of scope (unless review surfaces direct dependency)**:
- Refactoring the broader bootstrap pipeline.
- Changing the `uv` vs. `pip` decision.
- Migrating other autobuild workflows that are not affected by editable installs.

## Reproduction (from incident report)

1. Run `/feature-plan` + `/feature-build` for any feature against a project with a parent `.venv`
   (FEAT-FFC3 was the discovery case but this is generic).
2. After successful Coach approval of all tasks, run `/feature-complete <feature-id>`.
3. Verify the worktree at `.guardkit/worktrees/<feature-id>` is gone.
4. Inspect `<parent>/.venv/lib/python*/site-packages/_editable_impl_*.pth`. The path inside should
   reference the deleted worktree.
5. Run `<parent>/.venv/bin/<your-cli> --help`. Expect `ModuleNotFoundError`.
6. (Real-world) Restart Claude Desktop and watch any MCP that invokes `<parent>/.venv/bin/...`
   show "Server disconnected".

## Notes

- The autobuild log message
  `"Bootstrap: install ran against parent venv; venv_python set to sys.executable=..."`
  is the orchestrator detecting an unsafe state and choosing to proceed. That detection point is the
  natural place to either fail-fast or pivot to a worktree-local venv (Layer 1).
- This bug is **independent** of Bugs 1–3 from the same FFC3 run — those are honesty/orchestration
  defects in `autobuild.py`; this is an environment-bootstrap defect. They share only the discovery
  context.
- Layer 1 is preferred over Layer 2 even though Layer 2 is cheaper, because Layer 2 leaves manual
  `git worktree remove` users exposed and only fixes the `/feature-complete` happy path.
- Sibling design rule worth checking during review:
  [.claude/rules/namespace-hygiene.md](../../.claude/rules/namespace-hygiene.md) — the meta-rule
  about "local design decisions touching externally-defined namespaces" arguably covers this, since
  the parent venv is an externally-defined namespace from the autobuild's perspective.

## Next Steps

After review:
- If review concludes `[I]mplement`, create implementation task(s) via `/task-review TASK-REV-FFC6`
  with `[I]mplement` decision. Likely shape: one task for Layer 1 (worktree-local venv), optional
  task for Layer 3 (detect-and-warn).
- If review concludes `[A]ccept` with `wontfix`, document the rationale here and archive.
