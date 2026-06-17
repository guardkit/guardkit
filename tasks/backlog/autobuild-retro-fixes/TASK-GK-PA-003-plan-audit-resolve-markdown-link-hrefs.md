---
id: TASK-GK-PA-003
title: plan-audit resolves markdown-link hrefs and path-suffix matches
status: backlog
task_type: bug
priority: high
complexity: 3
created: 2026-06-17T11:00:00Z
tags: [autobuild, plan-audit, false-positive, path-string-mismatch]
source: docs/retro/autobuild-retro-xref-2026-06-17.md
provenance: fleet-memory FEAT-MEM-07 Error 2 (RIP-002 unrecoverable_stall)
---

# Task: plan-audit resolves markdown-link hrefs and path-suffix matches

## Description

`agent_invoker._scan_ac_for_missing_paths` flags a **markdown-link label** as a missing
file. For an AC line `[relay/service.py](src/fleet_memory/relay/service.py)`, the
scanner's path regex (`[\w./\-]+\.\w{1,5}`, `agent_invoker.py:8567`) matches the **label**
`relay/service.py`. Because the label contains a `/`, the bare-basename skip does not
save it, and `(worktree / "relay/service.py").exists()` is false → `plan_audit` emits a
HIGH `violation` → `all_gates_passed=False` → criteria short-circuit →
`UNRECOVERABLE_STALL` — even though the **href** `src/fleet_memory/relay/service.py`
exists on disk.

*Verified live:* the regex returns **both** the label and the href tokens.

This is the inverse-shape sibling of `.claude/rules/path-string-mismatch-is-not-dishonesty.md`:
a path-string miss treated as a hard failure when the file actually exists under a
resolvable path.

## Acceptance Criteria

- [ ] Before tokenizing an AC line, **resolve markdown links** `[label](href)` to their
      **href** and use the href (not the label) for existence checks.
- [ ] For any multi-segment path token, treat it as a **path suffix**: a match anywhere
      in the worktree tree (e.g. `**/relay/service.py`) counts as "exists" before
      declaring it missing.
- [ ] Genuinely-missing paths still fail (no masking): a token that resolves to neither
      a real href nor any tree-suffix match remains a violation.
- [ ] Regression test: an AC line `[relay/service.py](src/pkg/relay/service.py)` where
      the label path does NOT exist but the href DOES → **no violation**. Plus a
      control where neither exists → violation.

## Implementation Notes

- Single-file change in `guardkit/orchestrator/agent_invoker.py`
  (`_scan_ac_for_missing_paths`, ~`:8484-8606`, primary regex `:8567`).
- Keep the existing PA-002 (AC-section-only) and AC-001 (skip bare basenames) guards;
  this adds href-resolution + suffix-matching on top.
- Authoring guidance also exists (write `src/pkg/relay/service.py` or
  `[src/pkg/relay/service.py](src/pkg/relay/service.py)`), but the scanner should be
  robust to the common `[label](href)` form rather than relying on authoring discipline.

## Provenance

FEAT-MEM-07 Error 2 (fleet-memory). Cross-reference report
`docs/retro/autobuild-retro-xref-2026-06-17.md` §3.2.
