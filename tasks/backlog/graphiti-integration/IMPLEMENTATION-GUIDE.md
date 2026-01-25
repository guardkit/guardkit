# Graphiti Integration - Implementation Guide

## Overview

This guide describes the implementation order and parallel execution strategy for the Graphiti Integration feature set.

**Feature ID**: FEAT-GI
**Total Tasks**: 7
**Estimated Duration**: 1440 minutes (~24 hours)
**Recommended Parallel**: 2 (within each wave)

## Execution Waves

### Wave 1: Foundation (Parallel: 1 task)

| Task | Title | Complexity | Mode | Est. Time |
|------|-------|------------|------|-----------|
| TASK-GI-001 | Graphiti Core Infrastructure | 6 | task-work | 180 min |

**Wave 1 Deliverables:**
- Docker Compose setup for FalkorDB + Graphiti
- Python client wrapper with graceful degradation
- Configuration system (.guardkit/graphiti.yaml)
- Health check and initialization

**Gate**: All infrastructure working before proceeding to Wave 2.

---

### Wave 2: Knowledge Seeding (Parallel: 1 task)

| Task | Title | Complexity | Mode | Est. Time | Dependencies |
|------|-------|------------|------|-----------|--------------|
| TASK-GI-002 | System Context Seeding | 6 | task-work | 240 min | GI-001 |

**Wave 2 Deliverables:**
- Seeding script with ~67 episodes
- CLI command `guardkit graphiti seed`
- Verification queries
- Group ID organization

**Gate**: Seeding completes and knowledge is queryable.

---

### Wave 3: Context Usage (Parallel: 1 task)

| Task | Title | Complexity | Mode | Est. Time | Dependencies |
|------|-------|------------|------|-----------|--------------|
| TASK-GI-003 | Session Context Loading | 7 | task-work | 300 min | GI-001, GI-002 |

**Wave 3 Deliverables:**
- Context loader with scoped queries
- Context formatter for injection
- Integration with task-work, feature-build
- Architecture decision visibility

**Gate**: THIS IS THE ACTUAL FIX - context appears in sessions.

---

### Wave 4: Learning System (Parallel: 2 tasks)

| Task | Title | Complexity | Mode | Est. Time | Dependencies |
|------|-------|------------|------|-----------|--------------|
| TASK-GI-004 | ADR Lifecycle Management | 6 | task-work | 240 min | GI-001 |
| TASK-GI-005 | Episode Capture (Outcomes) | 5 | task-work | 180 min | GI-001 |

**Wave 4 Deliverables:**
- ADR entity model and service
- Decision capture from clarifying questions
- Task outcome capture on completion
- Learning loop established

**Gate**: Decisions and outcomes are being captured.

---

### Wave 5: Extended Sync (Parallel: 2 tasks)

| Task | Title | Complexity | Mode | Est. Time | Dependencies |
|------|-------|------------|------|-----------|--------------|
| TASK-GI-006 | Template/Agent Sync | 4 | task-work | 120 min | GI-001 |
| TASK-GI-007 | ADR Discovery from Code | 5 | task-work | 180 min | GI-001, GI-004 |

**Wave 5 Deliverables:**
- Template metadata sync to Graphiti
- Agent capabilities queryable
- Discovered ADRs from code analysis
- Full knowledge ecosystem

**Gate**: All templates and patterns queryable semantically.

---

## Critical Path

```
Wave 1: TASK-GI-001 (Infrastructure)
    |
    v
Wave 2: TASK-GI-002 (Seeding)
    |
    v
Wave 3: TASK-GI-003 (Context Loading) <- THE ACTUAL FIX
    |
    v
Wave 4: TASK-GI-004, TASK-GI-005 (Learning)
    |
    v
Wave 5: TASK-GI-006, TASK-GI-007 (Extended)
```

**Waves 1-3 are the critical path** to fixing the memory problem.
**Waves 4-5 make the system learn and improve** over time.

## Conductor Usage

For parallel execution within waves, use Conductor workspaces:

```bash
# Wave 4 parallel execution
conductor spawn wave4-1  # TASK-GI-004
conductor spawn wave4-2  # TASK-GI-005

# Wave 5 parallel execution
conductor spawn wave5-1  # TASK-GI-006
conductor spawn wave5-2  # TASK-GI-007
```

## AutoBuild Execution

Execute the entire feature with:

```bash
/feature-build FEAT-GI
```

This will:
1. Create feature worktree
2. Execute tasks in wave order
3. Run Player-Coach validation for each task
4. Preserve worktree for human review

## Prerequisites

1. **Docker**: Required for FalkorDB + Graphiti containers
2. **OpenAI API Key**: Required for embeddings (set OPENAI_API_KEY)
3. **Python 3.10+**: Required for async support
4. **graphiti-core**: Python SDK for Graphiti

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Docker unavailable | Graceful degradation - commands work without Graphiti |
| OpenAI API key missing | Document requirement, support alternative providers later |
| Context too verbose | Limit results per category in Wave 3 |
| Seeding drift | Version seeding script, re-seed when GuardKit changes |

## Success Criteria

After Wave 3 completion, sessions should:
1. Know what GuardKit is (product knowledge)
2. Know critical architecture decisions (SDK not subprocess)
3. Know what NOT to do (failure patterns)
4. Make system-compatible decisions

After Wave 5 completion:
1. All templates/agents semantically queryable
2. Decisions captured and retrievable
3. Task outcomes inform future sessions
4. Complete learning loop operational
