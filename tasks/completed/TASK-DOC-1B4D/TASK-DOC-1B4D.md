---
id: TASK-DOC-1B4D
title: "Add path-string-mismatch-is-not-dishonesty rule as inverse-shape sibling of absence-of-failure-is-not-success"
status: completed
created: 2026-05-06T00:00:00Z
updated: 2026-05-06T00:00:00Z
completed: 2026-05-06T00:00:00Z
completed_location: tasks/completed/TASK-DOC-1B4D/
previous_state: in_review
state_transition_reason: "All three ACs delivered and accepted; completing task and committing"
priority: medium
task_type: documentation
tags: [rules, design-rule, false-red, false-green, prior-art, graphiti]
parent_review: TASK-REV-1B452
feature_id: FEAT-1B452
implementation_mode: direct
wave: 3
conductor_workspace: honesty-fix-wave3-1
complexity: 2
depends_on:
  - TASK-FIX-1B4A
  - TASK-FIX-1B4C
test_results:
  status: n/a
  coverage: null
  last_run: null
  reason: "documentation-only task, direct mode, no test gates per task spec"
deliverables:
  - file: ".claude/rules/path-string-mismatch-is-not-dishonesty.md"
    action: created
    lines: ~220
  - file: ".claude/rules/absence-of-failure-is-not-success.md"
    action: edited
    change: "added Meta-frame section + cross-link to sibling under Prior art + IS_INVERSE_SHAPE_OF edge note"
  - graphiti:
      group_id: "guardkit__project_decisions"
      node_name: "path-string-mismatch-is-not-dishonesty"
      action: queued via mcp__graphiti__add_memory
      response_message: "Episode 'path-string-mismatch-is-not-dishonesty' queued for processing in group 'guardkit__project_decisions'"
      edge_described_in_body: "IS_INVERSE_SHAPE_OF → absence-of-failure-is-not-success"
landed_dependencies:
  - task: TASK-FIX-1B4A
    commit: 9d2fe52d
    summary: "Layer 1 — canonical-path resolution in CoachVerifier"
  - task: TASK-FIX-1B4C
    commit: 2c19aefc
    summary: "Layer 3' — filter orchestrator-induced ghosts at union-merge"
---

# Task: Sibling rule for false-red shape

## Description

Add `.claude/rules/path-string-mismatch-is-not-dishonesty.md` as the inverse-shape sibling of `.claude/rules/absence-of-failure-is-not-success.md`. Cross-link both. Add a paired Graphiti node under `guardkit__project_decisions` with an `IS_INVERSE_SHAPE_OF` edge to the existing rule's node.

This task must run **after** Layer 1 (TASK-FIX-1B4A) and Layer 3' (TASK-FIX-1B4C) land so the rule cites real fixed commits, not proposals.

## Context

The v2 review report (§AC-4) determined that the existing `absence-of-failure-is-not-success.md` rule is the wrong frame for the FFC3 false-fail in isolation. The two rules are **duals**:

| Property | `absence-of-failure-is-not-success` | this rule (sibling) |
|---|---|---|
| Direction | False-green | False-red |
| Verdict | `decision=approve` on absent oracle output | `decision=feedback` on degraded oracle output |
| Mechanism | Trusts Player counter at face value | Trusts Player path string at face value |
| Remediation pattern | Pair with `count_attempted > 0` precondition | Pair with identity-based path resolution |
| Grep-able signature | `task_work_results.get(...)` against `== 0` | `worktree_path / file_path` followed by `.exists()` |

Shared meta-frame: *a binary verdict from a low-fidelity oracle that cannot distinguish "no signal" from "positive/negative signal"*.

## Acceptance Criteria

- [x] **AC-DOC1**: `.claude/rules/path-string-mismatch-is-not-dishonesty.md` is created. Structure mirrors `absence-of-failure-is-not-success.md`:
  - **The rule** — one-line statement. ✓
  - **Why this rule exists** — chronological list of known instances. Initial entry: TASK-REV-1B452 (FEAT-FFC3 incident, 2026-05-06), with citations to the landed Layer 1 fix (TASK-FIX-1B4A, commit 9d2fe52d) and Layer 3' fix (TASK-FIX-1B4C, commit 2c19aefc). ✓
  - **Symptom** — bullet list of fingerprint signs. ✓
  - **Detection recipe** — grep commands targeting `worktree_path / .* exists` patterns in honesty-verification code paths. ✓
  - **Remediation recipe** — three-step pattern (audit boundary; identity-based resolution; demote single residual discrepancies). ✓
  - **Grep-able signature** — concrete grep commands. ✓
  - **Prior art** — cross-link to `.claude/rules/absence-of-failure-is-not-success.md` and the meta-frame statement. ✓
  - **When this rule triggers** — bullet list of trigger conditions. ✓
  - **What the rule does NOT cover** — explicit non-coverage. ✓

- [x] **AC-DOC2**: `.claude/rules/absence-of-failure-is-not-success.md` is updated to cross-link to the new rule. New "Meta-frame" section added before "Prior art" stating both rules are instances of *"a binary verdict from a low-fidelity oracle that cannot distinguish 'no signal' from 'positive/negative signal'"*. New "Sibling rule (false-red inverse direction)" entry added under "Prior art" referencing `path-string-mismatch-is-not-dishonesty.md`, plus `IS_INVERSE_SHAPE_OF` edge note added to the existing Graphiti node line.

- [x] **AC-DOC3**: A paired Graphiti node `path-string-mismatch-is-not-dishonesty` is queued under `guardkit__project_decisions` via `mcp__graphiti__add_memory`. The node body summarises the rule and lists the two known instances (TASK-FIX-1B4A and TASK-FIX-1B4C with their commit SHAs). The body explicitly describes the `IS_INVERSE_SHAPE_OF` edge to the existing `absence-of-failure-is-not-success` node so background extraction can materialise the relationship. MCP response message confirmed correct group routing per the TASK-INF-5053 verification protocol.

## Implementation Notes

**Files created / modified**:

1. `.claude/rules/path-string-mismatch-is-not-dishonesty.md` (new, ~220 lines).
2. `.claude/rules/absence-of-failure-is-not-success.md` (added Meta-frame section + sibling cross-link + Graphiti edge note under Prior art; ~40 lines added).
3. Graphiti write via `mcp__graphiti__add_memory` (group `guardkit__project_decisions`, name `path-string-mismatch-is-not-dishonesty`, source `text`, IS_INVERSE_SHAPE_OF edge described in body for background extraction).

**Graphiti write outcome**:

```
Response: "Episode 'path-string-mismatch-is-not-dishonesty' queued for
           processing in group 'guardkit__project_decisions'"
```

Per `.claude/rules/graphiti-knowledge-graph.md` (TASK-INF-5053 audit), the HTTP MCP server's response message accurately reflects the queued group. Background LLM extraction processes the episode asynchronously; if the node fails to appear under search later, the cause is extraction failure (TASK-INF-5054), not routing — check `docker logs graphiti-mcp --tail 50` on `promaxgb10-41b1`.

## Notes

- **Dependencies landed before this task ran**: TASK-FIX-1B4A (commit `9d2fe52d`, 2026-05-06 18:23) and TASK-FIX-1B4C (commit `2c19aefc`, 2026-05-06 18:30). Both are cited as load-bearing instances in the new rule.
- This is documentation only. Direct mode (no test gates).
- Risk: zero. Pure additive doc + knowledge-graph entries.
