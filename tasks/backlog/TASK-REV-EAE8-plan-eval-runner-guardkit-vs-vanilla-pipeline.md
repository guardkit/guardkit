---
id: TASK-REV-EAE8
title: "Plan: Eval Runner GuardKit vs Vanilla Pipeline"
status: review_complete
created: 2026-03-01T00:00:00Z
updated: 2026-03-01T00:00:00Z
priority: high
tags: [architecture-review, eval-runner, guardkit-vs-vanilla, comparison-pipeline, decision-point]
complexity: 7
task_type: review
decision_required: true
review_results:
  mode: decision
  depth: standard
  score: 85
  findings_count: 3
  recommendations_count: 3
  decision: implement
  approach: "Option 3: Phased Hybrid (Standalone CLI first, NATS later)"
  feature_id: FEAT-4296
clarification:
  context_a:
    timestamp: 2026-03-01T00:00:00Z
    decisions:
      focus: all
      tradeoff: quality_reliability
  context_b:
    timestamp: 2026-03-01T00:00:00Z
    decisions:
      approach: phased_hybrid
      execution: auto_detect
      testing: full_tdd
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Plan: Eval Runner GuardKit vs Vanilla Pipeline

## Description

Feature planning review for the Eval Runner GuardKit vs Vanilla Comparison Pipeline. This system runs automated A/B comparisons of GuardKit pipeline vs vanilla Claude Code to measure whether GuardKit produces measurably better results.

## Scope

The specification covers:
- Workspace provisioning (forked pairs from separate templates)
- Input resolution (text, file, Linear ticket)
- Sequential arm execution (GuardKit then vanilla Claude Code)
- Quantitative metrics extraction from evidence files
- Delta-based LLM judging
- Result classification (PASSED/FAILED/ESCALATED)
- Graphiti storage with comparison-specific fields

## Context Files

- features/eval-runner-gkvv/eval-runner-gkvv_summary.md
- features/eval-runner-gkvv/eval-runner-gkvv.feature (32 BDD scenarios)
- features/eval-runner-gkvv/eval-runner-gkvv_assumptions.yaml (7 assumptions)

## Key Assumptions

- Pass threshold: 0.65 (ASSUM-005)
- Escalate threshold: 0.40 (ASSUM-006)
- Per-arm timeout: total_timeout / 2 (ASSUM-001)
- Local vLLM timeout multiplier: 4x (ASSUM-002)
- Evidence file format: key=value plain text (ASSUM-003)
- LLM judge retries: 5 with exponential backoff (ASSUM-004, overridden)
- Local JSON cache: results/{eval_id}.json (ASSUM-007)

## Review Scope

- Focus: All aspects (architecture, technical, performance, security)
- Trade-off priority: Quality/reliability

## Acceptance Criteria

- [x] Technical options analyzed with pros/cons (3 options evaluated)
- [x] Architecture implications assessed (reuses agent_invoker.py, GraphitiClient, WorktreeManager patterns)
- [x] Effort estimation provided (10 tasks, 4 waves, aggregate complexity 7/10)
- [x] Risk analysis completed (6 risks identified with mitigations)
- [x] Implementation breakdown created (10 tasks with dependencies and parallel groups)
- [x] Recommended approach justified (Option 3: Phased Hybrid — de-risks methodology before infrastructure)

## Implementation Notes

**Decision:** Option 3 — Phased Hybrid (Standalone CLI first, NATS later)

**Rationale:**
1. Validates comparison methodology before investing in NATS infrastructure
2. Existing prototypes directly usable for standalone execution
3. Runner interface identical whether called from CLI or NATS subscriber
4. 32 BDD scenarios provide comprehensive test targets regardless of execution mode

**Generated Artifacts:**
- Feature folder: `tasks/backlog/eval-runner-gkvv/`
- Feature YAML: `.guardkit/features/FEAT-4296.yaml`
- 10 task files with TDD testing depth
- IMPLEMENTATION-GUIDE.md with Mermaid diagrams (data flow, integration contracts, task dependencies)
- README.md with problem statement and solution overview
