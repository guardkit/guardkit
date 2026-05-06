# Feature: Autobuild Bootstrap — Worktree Venv Isolation

**Feature ID:** FEAT-FFC6
**Parent review:** [TASK-REV-FFC6](../../in_review/TASK-REV-FFC6-autobuild-bootstrap-leaks-worktree-into-parent-venv.md)
**Review report:** [.claude/reviews/TASK-REV-FFC6-review-report.md](../../../.claude/reviews/TASK-REV-FFC6-review-report.md)
**Priority:** high
**Created:** 2026-05-06

## Problem Statement

The autobuild's `environment_bootstrap` step writes the **worktree's** `src/` path into the **parent project's** `.venv` editable `.pth` file. After `/feature-complete` (or any manual `git worktree remove`) deletes the worktree, the parent venv holds a dangling pointer that breaks every later process using that venv — Claude Desktop MCP servers, IDE language servers, shell scripts, cron jobs.

**The bug is silent** at autobuild time and at finalization time, and **cascades** across processes hours or days after the operation that introduced it. Manual repair (`uv pip install -e . --no-deps` from the parent project root) is needed at every affected venv.

The review surfaced **three** independent leak code paths (not the one originally reported):
1. `uv pip install -e .` (FFC3 case) — leaks via inherited `$VIRTUAL_ENV`
2. `uv sync --frozen` — leaks via inherited `$VIRTUAL_ENV` (project mode)
3. `[sys.executable, "-m", "pip", "install", "-e", "."]` — leaks via `sys.executable`'s `sys.prefix`, **independent of `$VIRTUAL_ENV`**, when guardkit was `pip install`-ed into the parent venv

It also surfaced a **test-suite defense-in-depth failure**: the existing test `test_preexisting_venv_succeeds_without_retry` actively encodes the leak as expected behaviour, which is why CI never caught the regression.

## Solution Approach

Ship two coordinated fixes plus a test-suite invariant fix:

- **TASK-FIX-FF61 (R1 + R3)** — eager worktree-local venv with explicit subprocess env isolation, applied to all three install paths, with a hard-fail invariant replacing the existing INFO-and-proceed false-success block. Bundled with the test invariant fix (every install-subprocess test must assert `env=` argument shape).
- **TASK-FIX-FF62 (R2)** — detect-and-warn pre-cleanup hook in `/feature-complete` that scans editable `.pth` files for references into the about-to-be-deleted worktree and prints a one-line repair command per match.

**Skipped (per review decision):** Layer 2 ("repoint parent venv at `/feature-complete`") is strictly weaker than Layer 1 once Layer 1 lands; it would only protect the `/feature-complete` happy path while leaving manual `git worktree remove` users exposed.

## Subtasks

| Wave | Task | Title | Method |
|------|------|-------|--------|
| 1    | [TASK-FIX-FF61](TASK-FIX-FF61-bootstrap-worktree-venv-isolation.md) | Bootstrap worktree-venv isolation across all three install paths | task-work |
| 2    | [TASK-FIX-FF62](TASK-FIX-FF62-feature-complete-detect-and-warn-on-pth-leak.md) | `/feature-complete` detect-and-warn on dangling editable `.pth` | task-work |

**Sequencing rationale:** TASK-FIX-FF62 calls into the `BootstrapEnvironmentLeakError` invariant introduced by TASK-FIX-FF61 for shared utility code (the `.pth` scanner). Sequential execution avoids merge conflict on the same file (`environment_bootstrap.py` introduces the `_isolated_env` helper that FF62 reuses).

## Implementation Mode

Both tasks: `task-work --mode=tdd --intensity=strict`. The review explicitly named the regression test shapes; tests should be written first and Layer 1 implementation must make them pass without breaking the existing AB60/F09A2/PEP-668 retry paths.

## Acceptance Criteria (rolled up)

- [ ] After autobuild + `/feature-complete` against a project with an active parent `.venv`, no editable `.pth` file in `<parent>/.venv/lib/python*/site-packages/` references the (now-deleted) worktree path. (Covered by FF61 + smoke test.)
- [ ] All three install paths (uv pip / uv sync / pip) write to `<worktree>/.venv` regardless of inherited `$VIRTUAL_ENV` and regardless of `sys.executable`. (Covered by FF61 unit tests.)
- [ ] The bootstrap raises `BootstrapEnvironmentLeakError` if it ever completes a Python install with `_venv_python` outside the worktree. (Covered by FF61 invariant test.)
- [ ] Existing tests `test_preexisting_venv_succeeds_without_retry` and siblings updated to assert `env["VIRTUAL_ENV"]` is worktree-local on every install subprocess. (Covered by FF61 R3.)
- [ ] `/feature-complete` warns (does not abort) on any pre-existing `.pth` leak referencing the about-to-be-removed worktree, with a one-line repair command. (Covered by FF62.)
- [ ] No regression in: PEP 668 fallback (`<worktree>/.guardkit/venv/`), AB60 uv-no-venv retry, FD32 uv-sync routing, F09A2 uv-sources detection, A7B6 extras install (when it lands).

## Out of Scope

- Refactoring the broader bootstrap pipeline.
- Migrating other autobuild workflows that don't write to global state (Node/.NET/Go/Rust/Flutter — verified leak-free by the review).
- Changing the `uv` vs `pip` decision logic.
- Layer 2 (repoint parent venv at `/feature-complete`) — explicitly skipped.

## References

- [Review report](../../../.claude/reviews/TASK-REV-FFC6-review-report.md) — comprehensive depth, includes C4 + 6 sequence diagrams
- [Original incident report](../../../specialist-agent/docs/history/autobuild-FFC3-editable-install-leak-incident.md)
- Sibling design rules: [.claude/rules/namespace-hygiene.md](../../../.claude/rules/namespace-hygiene.md), [.claude/rules/absence-of-failure-is-not-success.md](../../../.claude/rules/absence-of-failure-is-not-success.md)
- Companion FFC3 incidents: TASK-REV-1B452, TASK-REV-FFC4, TASK-REV-FFC5 (independent in mechanism; share only discovery context)
- Sequencing dependency: [TASK-FIX-A7B6](../TASK-FIX-A7B6-bootstrap-install-optional-extras.md) — touches the same call sites; FFC6 must merge first
