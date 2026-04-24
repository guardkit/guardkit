---
id: TASK-DOC-7A06
title: AutoBuild stall-diagnosis runbook + knowledge-graph seeding for player-invocation stalls
status: completed
created: 2026-04-24T12:55:00Z
updated: 2026-04-24T13:40:00Z
completed: 2026-04-24T13:40:00Z
completed_location: tasks/completed/TASK-DOC-7A06/
previous_state: in_progress
priority: low
tags: [docs, runbook, autobuild, graphiti, knowledge-graph]
parent_review: TASK-REV-E4F5
feature_id: FEAT-7A00
implementation_mode: direct
wave: 1
conductor_workspace: autobuild-sdk-stall-resilience-w1-4
complexity: 2
depends_on: []
graphiti_seed_uuid: 932dcd2f-0a1a-4b29-b614-2f83b7cd59a8
---

# Task: Runbook + knowledge-graph seed for player-invocation stalls

## Description

Bundle of recommendations **R5** + **R6** + **R7** from review TASK-REV-E4F5.
Now that the class-of-defect "Player invocation systematically errored and
the orchestrator misnamed the problem" has occurred twice (TASK-REV-8A08 on
FEAT-486D/TASK-AD-004 in Apr, and TASK-REV-E4F5 on FEAT-FORGE-002 in Apr), it
warrants:

1. A short runbook section so future users can self-diagnose.
2. A Graphiti knowledge-graph entry so future `/task-review` runs on similar
   symptoms will surface the prior art automatically.
3. An upstream issue on `anthropics/claude-agent-sdk-python` documenting the
   `rate_limit_event` gap, if current PyPI-latest still lacks parsing for it.

This task is `implementation_mode: direct` — no code changes, doc + graph
seed only. No Coach quality gates on code coverage.

## Acceptance Criteria

- [x] `docs/guides/autobuild-instrumentation-guide.md` gains a section
      **"If AutoBuild stalls immediately"** with a 3-line triage table
      (added as first subsection under `## Troubleshooting` so it's the
      first thing stall-diagnosers hit; also linked from the Table of
      Contents).
- [x] Cross-link from within the runbook back to TASK-REV-E4F5 review report
      and TASK-REV-8A08 review report (plus cross-link to TASK-FIX-7A01 for
      the active SDK-pin fix).
- [x] Graphiti graph seed into `guardkit__project_decisions`. Seeded via
      the Python client path (equivalent to the CLI's `add_episode` —
      `guardkit graphiti add-context` only accepts file paths, not inline
      payloads, so the "`--inline` or the equivalent command from the
      Python client" phrasing in the original brief routed to the latter).
      Episode uuid: `932dcd2f-0a1a-4b29-b614-2f83b7cd59a8`.
- [x] Verified seed is findable: `guardkit graphiti search "player
      invocation stall"` returns score-2.00 hit ("Player-invocation stall
      must be classified distinctly from coach-feedback stall") plus
      related extracted facts (`player_result.error`,
      `recovery_metadata`, SDK-auth tie to TASK-REV-E4F5).
- [x] R7 (upstream `claude-agent-sdk-python` issue): **not needed**.
      Verified `claude-agent-sdk` 0.1.66 (latest PyPI at 2026-04-24) now
      parses `rate_limit_event` — `RateLimitEvent`, `RateLimitInfo`,
      `RateLimitStatus`, `RateLimitType` are exported from
      `claude_agent_sdk.__init__` and referenced in
      `_internal/message_parser.py`. Upstream gap is closed. No issue
      filed. (This bullet in the brief was explicitly optional — "only if
      the upstream gap is confirmed".)
- [x] Update `CLAUDE.md`'s "Key References" table — new
      **AutoBuild Stall Runbook** row pointing at the section anchor.

## Files

- `docs/guides/autobuild-instrumentation-guide.md` (add triage section)
- `CLAUDE.md` (Key References table — add runbook entry)
- No source-code changes.

## Implementation Notes

- Use `mcp__graphiti__add_memory` (Claude Code MCP tool) if available in the
  session; fall back to `guardkit graphiti add-context --inline` CLI otherwise
  — see `.claude/rules/graphiti-knowledge-graph.md`.
- The graph-seed content above is a draft; tune wording but preserve the key
  spans (task IDs, graph-content terms) so future searches link up.
- No tests required — this is `implementation_mode: direct`. Quality gates
  are: (a) the runbook file exists and includes the required table; (b) the
  graph seed is findable via search.

## Notes

- Cross-link: recommendations R5, R6, R7 in TASK-REV-E4F5.
- Wave 1 parallel — touches only docs + knowledge graph, no source-code
  conflict with any other subtask.
- TASK-FIX-7A04 should cross-link this runbook for the `bootstrap_failure_mode`
  documentation.
