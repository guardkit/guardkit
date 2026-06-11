---
id: TASK-REV-9DDE
title: "Plan: Add a --json flag to /task-status that emits the dashboard as machine-readable JSON"
status: completed
created: 2026-06-11T12:08:26Z
updated: 2026-06-11T13:20:00Z
priority: high
task_type: review
tags: [feature-planning, task-status, json-output, cli]
complexity: 0
decision_required: true
clarification:
  context_a:
    timestamp: 2026-06-11T12:08:26Z
    decisions:
      focus: all
      tradeoff: balanced
  context_b:
    timestamp: 2026-06-11T13:18:00Z
    decisions:
      approach: option_1_deterministic_producer_script
      execution: sequential
      testing: standard
review_results:
  mode: decision
  depth: standard
  findings_count: 3
  recommendations_count: 2
  decision: implement
  feature_id: FEAT-9DDE
  report_path: .claude/reviews/TASK-REV-9DDE-review-report.md
  completed_at: 2026-06-11T13:20:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Plan: Add a --json flag to /task-status that emits the dashboard as machine-readable JSON

## Description

Feature planning review for adding a `--json` flag to the `/task-status` slash command. When the flag is provided, the command should emit the task dashboard (task counts by state, individual task summaries, epic/feature context where available) as machine-readable JSON instead of the human-readable formatted dashboard.

This enables downstream tooling: scripts, CI pipelines, dashboards, and other agents can consume task state programmatically without scraping formatted terminal output.

## Analysis Scope (Context A)

- **Focus**: All aspects (technical approach, JSON schema design, backwards compatibility, fit with markdown-driven command model)
- **Trade-off priority**: Balanced (reasonable delivery speed with solid quality)

## Acceptance Criteria (for the review)

- [ ] Identify how /task-status is currently implemented (markdown-interpreted vs producer script)
- [ ] Propose 2-3 technical options for emitting JSON output
- [ ] Define the JSON schema shape for the dashboard
- [ ] Assess backwards compatibility (default output unchanged)
- [ ] Recommend an approach with effort estimate and task breakdown

## Review Findings

See [.claude/reviews/TASK-REV-9DDE-review-report.md](../../../.claude/reviews/TASK-REV-9DDE-review-report.md). Decision: [I]mplement — Option 1 (deterministic producer script). Feature FEAT-9DDE created with 2 tasks (TASK-TSJ-001, TASK-TSJ-002).
