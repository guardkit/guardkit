---
id: TASK-REV-CSC1
title: "Plan: Implement context-sensitive Coach"
status: review_complete
created: 2026-01-23T11:00:00Z
updated: 2026-01-23T11:45:00Z
priority: high
tags: [context-sensitive-coach, quality-gates, coach-validator, autobuild, architectural-review]
task_type: review
complexity: 8
source_document: docs/research/context-sensitive-coach-proposal.md
clarification:
  context_a:
    timestamp: 2026-01-23T11:00:00Z
    decisions:
      focus: balanced
      tradeoff: maintainability
      plugins: recommend
  context_b:
    timestamp: 2026-01-23T11:40:00Z
    decisions:
      approach: ai_based_no_plugins
      execution: parallel_conductor
      testing: standard
review_results:
  mode: decision
  depth: comprehensive
  decision: implement
  feature_id: FEAT-4C15
  subtasks_created: 7
  feature_folder: tasks/backlog/context-sensitive-coach/
---

# Plan: Implement Context-Sensitive Coach

## Background

This review task analyzes the context-sensitive Coach proposal documented in `docs/research/context-sensitive-coach-proposal.md` and creates an implementation plan with subtasks.

### Source Proposal Summary

The proposal describes a CoachValidator that adapts quality gate thresholds based on actual implementation context rather than static task_type profiles. Key components:

**Three-Tier Analysis Architecture:**
- **Tier 1 (Universal)**: Git diff statistics, file counts, line counts - works for ALL languages (~50ms)
- **Tier 2 (Tree-sitter)**: AST-based analysis for 40+ languages (~100-200ms/file)
- **Tier 3 (Plugins)**: Language-specific pattern detection (Python, TypeScript, C#)

**Core Features:**
- Scope classification: trivial → simple → moderate → complex → critical
- Dynamic profile selection based on classification
- Contextual coverage evaluation (testable lines vs total lines)
- Pattern detection for testability analysis
- Caching between turns for performance
- Incremental analysis (only re-analyze changed files)

**Performance Targets:**
- Total context gathering: < 1 second
- Turn 2+ with no changes: ~10ms (cache hit)
- Turn 2+ with few changes: ~100ms (incremental)

### Problem Being Solved

The current quality gate system is binary - a 20-line FastAPI initialization faces the same 60-point arch review threshold and 80% coverage requirement as a 500-line authentication system. This causes:
- Simple configuration code to fail arch review
- Declarative code (Pydantic models, dataclasses) to fail coverage gates
- AutoBuild tasks to fail even when implementations are correct

### Review Context

**Clarification Decisions (Context A):**
- Focus: Balanced (architecture, implementation, performance, integration)
- Trade-off Priority: Maintainability (clear abstractions, extensible)
- Language Plugins: Recommend based on effort/value analysis

## Review Objectives

1. **Architecture Analysis**: Evaluate the three-tier design for clarity and extensibility
2. **Implementation Breakdown**: Create detailed subtasks for phased implementation
3. **Integration Strategy**: How to integrate with existing CoachValidator
4. **Performance Validation**: Confirm latency targets are achievable
5. **Plugin Recommendation**: Analyze whether Tier 3 plugins should be included initially

## Scope

### In Scope
- Full analysis of `docs/research/context-sensitive-coach-proposal.md`
- Review of current `guardkit/orchestrator/quality_gates/coach_validator.py`
- Review of `guardkit/models/task_types.py` (current profile system)
- Integration design with existing AutoBuild workflow
- Subtask generation for phased implementation

### Out of Scope
- Implementation (this is planning only)
- Changes to task_type system (preserved for backwards compatibility)
- Performance benchmarking (deferred to implementation)

## Acceptance Criteria

- [ ] Review report with architecture assessment
- [ ] Phased implementation plan (waves for parallel execution)
- [ ] Clear integration points identified
- [ ] Risk assessment and mitigation strategies
- [ ] Recommendation on Tier 3 plugins for initial release
- [ ] Subtasks ready for `/feature-build` or `/task-work`

## References

- **Proposal**: `docs/research/context-sensitive-coach-proposal.md`
- **Current Coach**: `guardkit/orchestrator/quality_gates/coach_validator.py`
- **Task Types**: `guardkit/models/task_types.py`
- **Related Reviews**: TASK-REV-FB22 (identified the need for context-sensitive validation)
