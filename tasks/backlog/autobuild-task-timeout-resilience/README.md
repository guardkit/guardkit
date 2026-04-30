# FEAT-ATR — AutoBuild Task-Timeout Resilience

**Origin:** [jarvis] TASK-REV-E73C, 2026-04-30
**Trigger incident:** FEAT-J005-946D timed out at TASK-J005-005 turn 2 with
the per-task orchestrator logging `Coach approved` 68 ms after the feature-level
`asyncio.wait_for` timer fired (transcript lines 1800–1808). Per-task durable
state (`coach_turn_2.json`, frontmatter, git checkpoint `0069a0d`) said
`approved` and 15/15 ACs verified; feature YAML said `timeout`. Both writes
were correct from their respective layers; the disagreement is a real durable
race the per-task layer has already partially mitigated (TASK-ABFIX-004) but
the feature layer has not.

**Parent review:** Originated in jarvis at
`.claude/reviews/TASK-REV-E73C-review-report.md` (v2, code- and
worktree-validated).

## Problem statement

`asyncio.wait_for(asyncio.to_thread(...), timeout=task_timeout)` at
[guardkit/orchestrator/feature_orchestrator.py:2079–2087](../../../guardkit/orchestrator/feature_orchestrator.py#L2079-L2087)
hard-cancels the awaitable but cannot interrupt the worker thread. When the
timer fires while the per-task `CoachValidator` is mid-subprocess (pytest
fallback), the thread runs to completion in the milliseconds after the timer,
writing `coach_turn_<N>.json` with `decision=approve` and a git checkpoint
commit — all *after* the feature orchestrator has already recorded TIMEOUT.

The per-task layer already handles this race correctly via TASK-ABFIX-004
(autobuild.py:2192–2202: "approval-wins-over-timeout"). The feature layer
needs the symmetric mechanism.

A second issue surfaced by the review: each per-task turn runs Player +
specialist:test-orchestrator + specialist:code-reviewer + Coach inside the
same wall-clock budget. The specialists' `sdk_timeout` cap is computed from
a single `remaining_budget` snapshot at the top of `_execute_turn` and is
not refreshed between Phase 4 and Phase 5 invocations
([autobuild.py:2880–2909](../../../guardkit/orchestrator/autobuild.py#L2880-L2909)),
so Phase 5's cap doesn't reflect Phase 4's wall consumption.

A third issue is purely user-facing ergonomics: the feature-level
`task_timeout` (default 3000s after the TASK-ABSR-FLOR floor) is global,
but a small fraction of complexity-7 task-work tasks legitimately need
longer envelopes. The per-task `autobuild.sdk_timeout` frontmatter override
exists ([autobuild.py:2521–2523](../../../guardkit/orchestrator/feature_orchestrator.py#L2521-L2523))
but there's no symmetric `autobuild.task_timeout` override.

## Tasks

| ID | Title | Tier | Risk | LOC est. |
|---|---|---|---|---|
| TASK-ATR-001 | Per-task `task_timeout` frontmatter override | 1.1 | Low | ~30 |
| TASK-ATR-002 | Refresh `remaining_budget` between Phase 4/5 specialists | 1.2 | Low (with test) | ~15 |
| TASK-ATR-003 | Feature-level late-approval reconciliation | 2.1 | Low (read-only check) | ~40 |

All three are independent at the file level (different code regions) but
share the `_invoke_coach_safely` / specialist-pipeline test surface, so
test runs are best ordered ATR-001 → ATR-002 → ATR-003.

## Out of scope (separate items)

- Graphiti `edge_fulltext_search` circuit-breaker (TASK-REV-E73C report Tier 2.2).
  ~5 LoC in `guardkit/knowledge/falkordb_workaround.py`. File when it surfaces
  on its own; not blocking anything.
- Coach SDK pytest path failing exit-code-1 on macOS Framework Python +
  bundled CLI (TASK-REV-E73C report Tier 2.3). Reported workaround:
  `autobuild.coach.test_execution: subprocess` in `.guardkit/config.yaml`,
  applied in jarvis 2026-04-30. Upstream `claude-agent-sdk` 0.1.66 issue.

## Provenance

```yaml
parent_review:    TASK-REV-E73C   # in jarvis repo
feature_id:       FEAT-ATR
trigger_incident: FEAT-J005-946D run-1, 2026-04-29
report_path:      jarvis/.claude/reviews/TASK-REV-E73C-review-report.md
```
