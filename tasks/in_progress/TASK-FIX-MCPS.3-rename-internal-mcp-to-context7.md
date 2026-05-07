---
id: TASK-FIX-MCPS.3
title: Rename installer/core/lib/mcp/ to installer/core/lib/context7/
status: in_progress
task_type: implementation
parent_review: TASK-REV-MCPS
feature_id: FEAT-MCPS
related_to: TASK-REV-MCPS
related_tasks:
  - TASK-FIX-MCPS.1
  - TASK-FIX-MCPS.2
depends_on:
  - TASK-FIX-MCPS.1
  - TASK-FIX-MCPS.2
priority: medium
complexity: 3
wave: 2
implementation_mode: task-work
conductor_workspace: mcps-namespace-collision-wave2-rename
tags: [refactor, namespace-collision, mcps, root-cause]
created: 2026-04-24T00:00:00Z
updated: 2026-04-24T12:00:00Z
previous_state: backlog
state_transition_reason: "Automatic transition for task-work execution"
---

# Task: Rename internal mcp/ module to context7/

## Why

The root-cause collision is that `installer/core/lib/mcp/` shares a name with Anthropic's `mcp` PyPI package (the Model Context Protocol SDK). The module is actually a Context7 documentation client (Upstash's Context7 service) and has nothing to do with Anthropic's MCP. Renaming eliminates the collision class entirely — no future `sys.path.insert(0, installer/core/lib)` can re-activate the bug.

TASK-FIX-MCPS.1 + .2 fix the immediate outage and improve diagnostics. This task closes the root cause.

**Context**: see [docs/reviews/TASK-REV-MCPS-namespace-collision-review.md](../../../docs/reviews/TASK-REV-MCPS-namespace-collision-review.md) §3.2.

**Caller audit** (from review Workstream B): zero external callers. Only self-references within the four files of the module.

## What

1. Rename directory: `installer/core/lib/mcp/` → `installer/core/lib/context7/`
2. Update `installer/core/lib/context7/__init__.py` docstring and module header comments to reflect the new name (no export change — `DetailLevel`, `Context7Client`, `MCPMonitor`, `MCPRequest`, `MCPResponse`, `count_tokens` stay).
3. Grep audit: `rg "installer\.core\.lib\.mcp|from \.mcp\.|from \.\.mcp\."` across `.py`, `.md`, `.yaml`, `.json`, and `.toml` files. Update any hits.
4. Grep audit for string-based dynamic imports: `rg '"installer.core.lib.mcp"|"mcp.context7"|"mcp.monitor"'` — update any matches.
5. Consider (optional, judgement call during implementation): since `MCPMonitor` / `MCPRequest` / `MCPResponse` symbol names still carry the "MCP" prefix and are now mildly confusing (the module is no longer at `mcp` but the class name suggests it is), the implementer may propose renames to `Context7Monitor` / `Context7Request` / `Context7Response`. If zero external callers confirmed, do the rename; if any caller is found, leave symbol names alone and only rename the directory.

## Acceptance Criteria

- [ ] Directory `installer/core/lib/mcp/` no longer exists.
- [ ] Directory `installer/core/lib/context7/` exists and contains the four source files.
- [ ] `python -c "from installer.core.lib.context7 import Context7Client, DetailLevel"` succeeds.
- [ ] No file in the repo imports from `installer.core.lib.mcp` (grep returns zero).
- [ ] `python -c "import guardkit.cli.autobuild; import mcp; print(mcp.__file__)"` resolves `mcp` to site-packages from the `mcp` PyPI package, regardless of any `sys.path` state.
- [ ] Full pytest suite passes.
- [ ] `guardkit autobuild --help` and `guardkit autobuild feature --help` work.
- [ ] Commit message references TASK-REV-MCPS and namespace-hygiene rule.
- [ ] Graphiti update (post-flight): add episode to `guardkit__task_outcomes` noting the rename as an executed instance of the namespace-hygiene rule.

## Test Matrix

| Surface | Check |
|---|---|
| Editable install | `from installer.core.lib.context7 import Context7Client` → works. |
| Full pytest | No regressions. |
| Active shadow reproduction | `python -c "import sys; sys.path.insert(0, 'installer/core/lib'); import mcp; assert 'site-packages' in mcp.__file__"` → passes (because `installer/core/lib/` no longer has an `mcp/` subdir). |
| `guardkit autobuild --help` smoke | Works. |

## Risk / Rollback

Low risk. Zero external callers confirmed in review Workstream B. Revert is `git mv` in the other direction.

## Dependencies

Depends on TASK-FIX-MCPS.1 and TASK-FIX-MCPS.2 for a clean baseline (those must land first so the test suite is known-green before the rename modifies import paths).

## References

- Review: [docs/reviews/TASK-REV-MCPS-namespace-collision-review.md](../../../docs/reviews/TASK-REV-MCPS-namespace-collision-review.md) §3.2
- Rule: [.claude/rules/namespace-hygiene.md](../../../.claude/rules/namespace-hygiene.md)
