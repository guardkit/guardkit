# Implementation Plan — TASK-FIX-WTESCAPE01

**Title**: Player file writes escape the worktree via absolute paths
**Intensity**: light (fresh task, complexity 5)
**Date**: 2026-06-12

## Root cause

`deepagents.backends.filesystem.FilesystemBackend._resolve_path` with
`virtual_mode=False` (deliberately set by TASK-HMIG-002R-NOVMODE) returns
absolute paths **as-is** and resolves relative `..` traversal without a
containment check. The Player's Write/Edit tools therefore honour absolute
host-repo paths fed in by task context, landing edits in the operator's
main checkout (observed FEAT-C332 run 2).

## Mechanism choice

A delegating backend wrapper (`PathConfinedBackend`), same pattern as the
existing `TruncatingBackend` in
`guardkitfactory/src/guardkitfactory/harness/backend_config.py`.

The permissions-middleware route is **not viable**: DeepAgents'
`FilesystemMiddleware` raises `NotImplementedError` for permissions on
execute-capable backends, and upstream declined to fix (#2894 — see
`permissions.py` docstring, TASK-HMIG-002R-NOPERMS).

## Decisions (made with defaults, no human present)

1. **Reject, not rebase** (AC-001). Rebasing absolute host paths into the
   worktree would recreate the doubly-nested-path silent failure that
   NOVMODE was introduced to kill — same shape, inverse direction. A clear
   tool error (`WriteResult(error=...)` / `EditResult(error=...)`) gives
   the model actionable feedback to retry with a worktree path.
2. **guardkitfactory symlink: ALLOWED** (AC-002). The
   `<worktrees-dir>/guardkitfactory` sibling symlink is intentional;
   cross-repo tasks (sibling TASK-AB-XREPOEV01) legitimately write through
   it. Policy: writes are confined to `worktree.resolve()` **plus** the
   resolved target of a sibling symlink literally named `guardkitfactory`
   in `worktree.parent`, **plus** any caller-supplied `extra_write_roots`.
   Any other escape (including other symlinks) is rejected.
3. **Writes only**. Confine `write`/`awrite`/`edit`/`aedit`. Reads, ls,
   glob, grep stay unconfined (Coach legitimately reads orchestrator-fed
   absolute paths; reads cannot corrupt the host repo). `execute` is out
   of scope per the documented operator-trust threat model
   (backend_config.py docstring).

## Files

### guardkitfactory (`../guardkitfactory`)

| File | Change |
|---|---|
| `src/guardkitfactory/harness/backend_config.py` | Add `PathConfinedBackend` wrapper; wire into `build_autobuild_backend` (wrap `local_shell` before `TruncatingBackend`); new optional kwarg `extra_write_roots`; module docstring section |
| `tests/harness/test_backend_config.py` | ~12 new tests (AC-001..AC-004, incl. host-git-clean integration test and async variants) |

### guardkit (this repo)

| File | Change |
|---|---|
| `tasks/in_progress/TASK-FIX-WTESCAPE01-*.md` | AC checkboxes, completion notes |
| `docs/state/TASK-FIX-WTESCAPE01/implementation_plan.md` | this file |

No orchestrator code change needed: `selector.py` already passes
`cwd=worktree` to `build_autobuild_backend`; the confinement claim at
`selector.py:363` becomes true for file tools. Adding an optional kwarg
does not break the cross-repo seam test
(`test_build_autobuild_backend_accepts_orchestrator_params` asserts
presence of existing params only).

## Containment algorithm

```
on write/edit(file_path):
    p = Path(file_path); base = p if p.is_absolute() else inner.cwd / p
    resolved = base.resolve()          # symlink-aware (task requirement)
    if not any(resolved.is_relative_to(root) for root in allowed_roots):
        log WARNING (AC-004)
        return Write/EditResult(error="...use a worktree-relative path...")
    return inner.write/edit(...)
```

`allowed_roots` computed once in `build_autobuild_backend`:
`[worktree.resolve()] + [sibling guardkitfactory symlink target if present]
+ [r.resolve() for r in extra_write_roots or []]`.

## Test plan (AC mapping)

- AC-001: absolute-outside write + edit rejected with tool error;
  relative `../` traversal write rejected; in-worktree symlink pointing
  outside rejected; absolute-INSIDE-worktree write still works (NOVMODE
  preserved); relative write works; async `awrite`/`aedit` confined.
- AC-002: sibling `guardkitfactory` symlink target allowed; other sibling
  symlinks NOT allowed; `extra_write_roots` allows.
- AC-003: integration test — temp host git repo + temp worktree; write and
  edit attempts to absolute host paths; assert tool errors AND
  `git status --porcelain` clean in host repo.
- AC-004: `caplog` asserts WARNING on rejected write.

## Out of scope (follow-ups noted in task file)

- Orchestrator-side host-repo `git status` backstop after each turn
  (fix direction #3 — defence-in-depth, "can" not "must").
- Prompt-assembly rewriting of absolute host paths (fix direction #2).
- SDK-harness equivalent confinement (defect observed on LangGraph only).

## Estimates

~150 LOC production, ~200 LOC tests, single session.
