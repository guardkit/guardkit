---
id: TASK-DOC-7A06
title: AutoBuild stall-diagnosis runbook + knowledge-graph seeding for player-invocation stalls
status: backlog
created: 2026-04-24T12:55:00Z
updated: 2026-04-24T12:55:00Z
priority: low
tags: [docs, runbook, autobuild, graphiti, knowledge-graph]
parent_review: TASK-REV-E4F5
feature_id: FEAT-7A00
implementation_mode: direct
wave: 1
conductor_workspace: autobuild-sdk-stall-resilience-w1-4
complexity: 2
depends_on: []
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

- [ ] `docs/guides/autobuild-instrumentation-guide.md` gains a section
      **"If AutoBuild stalls immediately"** with a 3-line triage table:
      | Symptom (from summary) | Likely cause | Quick check |
      |---|---|---|
      | `player_invocation_stall` + auth error | Not logged into Claude on this host | `claude` CLI login |
      | `player_invocation_stall` + "Unknown message type" | SDK version skew | `pip show claude-agent-sdk` vs. working host |
      | `player_invocation_stall` + stream/timeout | Network or endpoint config | `ANTHROPIC_BASE_URL` + vllm-serve.sh (see TASK-REV-8A08) |
- [ ] Cross-link from within the runbook back to TASK-REV-E4F5 review report
      and TASK-REV-8A08 review report.
- [ ] Graphiti graph seed via `guardkit graphiti add-context --inline` (or
      the equivalent command from the Python client):
      - `group_id: guardkit__project_decisions`
      - content: _"Player-invocation stall (3× SDK error before any work) must
        be classified distinctly from coach-feedback stall at the final-summary
        layer. Observed twice: TASK-REV-8A08 (FEAT-486D, SDK stream timeout)
        and TASK-REV-E4F5 (FEAT-FORGE-002, SDK auth + version skew). The
        orchestrator captures the signal in `player_result.error` /
        synthetic-report `recovery_metadata` but does not consult it at
        summary-time."_
- [ ] Verify the seed arrives in the graph: `guardkit graphiti search
      "player invocation stall"` returns the new fact.
- [ ] Coordinate with TASK-FIX-7A01: **before pinning** `claude-agent-sdk` to
      a version that parses `rate_limit_event`, verify whether any PyPI
      release exists. If not, file
      `https://github.com/anthropics/claude-agent-sdk-python/issues/new` with:
      - the Run 2 transcript's error quote
      - the approximate SDK version where it first failed
      - a minimal repro (a small Python snippet streaming one `rate_limit_event`
        message type through the SDK's parser).
      Link the opened issue from TASK-FIX-7A01's Notes section. (This bullet
      is optional — only if the upstream gap is confirmed.)
- [ ] Update `CLAUDE.md`'s "Key References" table so the runbook section is
      discoverable.

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
