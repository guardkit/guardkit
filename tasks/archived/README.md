# Archived Tasks

This directory contains tasks that have been archived for reference.

## Directory Structure

### superseded/
Tasks that have been replaced by newer approaches or completed through different means.

#### agent-discovery-old-approach/ (7 tasks)
**Archived**: 2025-11-21
**Reason**: Exploratory work on agent discovery using structured templates. Superseded by simpler Phase 8 incremental approach.

**Tasks**:
- TASK-AGENT-BOUND-20251121-151631.md
- TASK-AGENT-EXAMPLES-20251121-151804.md
- TASK-AGENT-GIT-20251121-152113.md
- TASK-AGENT-STRUCT-20251121-151631.md
- TASK-AGENT-STYLE-20251121-152113.md
- TASK-AGENT-VALIDATE-20251121-160001.md
- TASK-AGENT-ENHANCER-20251121-160000.md

**Replacement**: Phase 8 INCREMENTAL specification (TASK-PHASE-8-INCREMENTAL, completed Nov 21)

**Context**: These tasks represented a detailed, template-based approach to agent enhancement with explicit guidelines for structure, boundaries, examples, Git workflow, and code style. While well-designed, this approach was determined to be over-engineered for current needs. The simpler Phase 8 incremental approach achieves the same goals with less complexity.

#### phase-7-5-approach/ (1 task)
**Archived**: 2025-11-21
**Reason**: Phase 7.5 batch processing approach was implemented, tested, and then removed in favor of Phase 8 incremental approach.

**Tasks**:
- TASK-PHASE-7-5-SIMPLE-specification.md

**Replacement**: Phase 8 INCREMENTAL specification

**Git History**:
- Commit: "feat: Implement TASK-PHASE-8-INCREMENTAL" (Nov 21)
- Commit: "feat: Complete TASK-SIMP-9ABE - Remove Phase 7.5 agent enhancement" (Nov 21)

**Context**: Phase 7.5 attempted batch processing of multiple agents simultaneously. While functional, it proved less flexible and harder to debug than the incremental approach. Phase 8 processes agents one at a time with better error handling and progress tracking.

### future-enhancements/
Tasks for future phases or optional features not currently prioritized.

#### External Agent Discovery (2 tasks)
**Archived**: 2025-11-21
**Reason**: Phase 2 optional feature. Current focus is Phase 1 (core template creation).

**Tasks**:
- TASK-004-REDESIGN-ai-agent-discovery.md (External discovery)
- TASK-004A-ai-agent-generator.md (Agent generation)

**Status**: Deferred to Phase 2

**Context**: These tasks explore external agent discovery mechanisms (discovering agents from other projects, repositories, or sources). While potentially valuable for advanced use cases, they are not required for core template creation functionality. May be revisited in Phase 2 if there's demand for cross-project agent sharing.

## When to Review Archived Tasks

- **Learning**: Understand evolution of approaches (why certain designs were rejected)
- **Historical context**: Reference for design decisions
- **Feature resurrection**: If requirements change, archived features might become relevant again
- **Avoiding repetition**: Don't recreate the same solutions that were previously explored

## Do NOT Use These Tasks

Tasks in this directory are archived for reference only. Do not implement them unless:
1. Requirements have changed significantly
2. New context makes the approach viable
3. You've discussed with the team and updated the task
4. You've created a new task in backlog/ referencing the archived work

For current work, see:
- **Active tasks**: `tasks/backlog/` (organized by initiative)
- **Completed tasks**: `tasks/completed/` (finished work)

## Archive Organization Principles

Tasks are archived (not deleted) because:
1. They contain valuable analysis and design work
2. They document "roads not taken" for future reference
3. They prevent repeating the same exploration
4. They provide context for current implementations

## Statistics

**Total archived**: 10 tasks
- Superseded approaches: 8 tasks
- Future enhancements: 2 tasks

**Archive date**: 2025-11-21
**Part of**: Backlog cleanup initiative (80 → 54 active files)
