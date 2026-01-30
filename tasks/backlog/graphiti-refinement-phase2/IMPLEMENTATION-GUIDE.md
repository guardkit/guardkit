# Implementation Guide: Graphiti Refinement Phase 2

**Feature ID**: FEAT-0F4A
**Approach**: Parallel Tracks
**Testing Mode**: Standard (quality gates)

## Execution Strategy

### Wave 1: Foundation Features (Parallel)

**Wall-clock time**: ~19h (max of GR-003 and GR-004)
**Conductor recommended**: Yes - use 2 workspaces

#### Track A: Feature Spec Integration (GR-003)

| Task | Title | Estimate | Mode | Workspace |
|------|-------|----------|------|-----------|
| TASK-GR3-001 | Implement FeatureDetector class | 2h | task-work | wave1-gr003 |
| TASK-GR3-002 | Implement FeaturePlanContext dataclass | 2h | direct | wave1-gr003 |
| TASK-GR3-003 | Implement FeaturePlanContextBuilder | 3h | task-work | wave1-gr003 |
| TASK-GR3-004 | Integrate with /feature-plan command | 2h | task-work | wave1-gr003 |
| TASK-GR3-005 | Add --context CLI option | 1h | direct | wave1-gr003 |
| TASK-GR3-006 | Add AutoBuild context queries | 2h | task-work | wave1-gr003 |
| TASK-GR3-007 | Add tests for context building | 2h | task-work | wave1-gr003 |
| TASK-GR3-008 | Update documentation | 1h | direct | wave1-gr003 |

**Track A Total**: 15h

#### Track B: Interactive Knowledge Capture (GR-004)

| Task | Title | Estimate | Mode | Workspace |
|------|-------|----------|------|-----------|
| TASK-GR4-001 | Implement KnowledgeGapAnalyzer | 3h | task-work | wave1-gr004 |
| TASK-GR4-002 | Implement InteractiveCaptureSession | 3h | task-work | wave1-gr004 |
| TASK-GR4-003 | Create CLI capture command | 2h | direct | wave1-gr004 |
| TASK-GR4-004 | Add fact extraction logic | 2h | task-work | wave1-gr004 |
| TASK-GR4-005 | Implement Graphiti persistence | 2h | task-work | wave1-gr004 |
| TASK-GR4-006 | Add /task-review --capture-knowledge | 2h | task-work | wave1-gr004 |
| TASK-GR4-007 | Add AutoBuild workflow customization | 2h | task-work | wave1-gr004 |
| TASK-GR4-008 | Add tests | 2h | task-work | wave1-gr004 |
| TASK-GR4-009 | Update documentation | 1h | direct | wave1-gr004 |

**Track B Total**: 19h

---

### Wave 2: Knowledge Query Commands (Sequential)

**Wall-clock time**: 13h
**Requires**: Wave 1 complete

| Task | Title | Estimate | Mode | Dependencies |
|------|-------|----------|------|--------------|
| TASK-GR5-001 | Implement `show` command | 2h | task-work | Wave 1 |
| TASK-GR5-002 | Implement `search` command | 2h | task-work | Wave 1 |
| TASK-GR5-003 | Implement `list` command | 1h | direct | TASK-GR5-001 |
| TASK-GR5-004 | Implement `status` command | 1h | direct | TASK-GR5-001 |
| TASK-GR5-005 | Add output formatting utilities | 1h | direct | TASK-GR5-001 |
| TASK-GR5-006 | Create TurnStateEpisode schema | 1h | task-work | Wave 1 |
| TASK-GR5-007 | Add turn state capture to feature-build | 2h | task-work | TASK-GR5-006 |
| TASK-GR5-008 | Add turn context loading | 1h | task-work | TASK-GR5-007 |
| TASK-GR5-009 | Add tests | 2h | task-work | All GR5 tasks |
| TASK-GR5-010 | Update documentation | 1h | direct | All GR5 tasks |

**Wave 2 Total**: 13h (wall-clock: 13h)

---

### Wave 3: Job-Specific Context Retrieval (Sequential)

**Wall-clock time**: 32h
**Requires**: Wave 2 complete

| Task | Title | Estimate | Mode | Dependencies |
|------|-------|----------|------|--------------|
| TASK-GR6-001 | Implement TaskAnalyzer | 3h | task-work | Wave 2 |
| TASK-GR6-002 | Implement DynamicBudgetCalculator | 4h | task-work | TASK-GR6-001 |
| TASK-GR6-003 | Implement JobContextRetriever | 4h | task-work | TASK-GR6-002 |
| TASK-GR6-004 | Implement RetrievedContext formatting | 3h | task-work | TASK-GR6-003 |
| TASK-GR6-005 | Integrate with /task-work | 2h | task-work | TASK-GR6-004 |
| TASK-GR6-006 | Integrate with /feature-build | 2h | task-work | TASK-GR6-005 |
| TASK-GR6-007 | Add role_constraints retrieval | 2h | task-work | TASK-GR6-003 |
| TASK-GR6-008 | Add quality_gate_configs retrieval | 2h | task-work | TASK-GR6-003 |
| TASK-GR6-009 | Add turn_states retrieval | 3h | task-work | TASK-GR6-003, Wave 2 |
| TASK-GR6-010 | Add implementation_modes retrieval | 1h | direct | TASK-GR6-003 |
| TASK-GR6-011 | Relevance tuning and testing | 3h | task-work | TASK-GR6-009 |
| TASK-GR6-012 | Performance optimization | 2h | task-work | TASK-GR6-011 |
| TASK-GR6-013 | Add tests | 3h | task-work | All GR6 tasks |
| TASK-GR6-014 | Update documentation | 1h | direct | All GR6 tasks |

**Wave 3 Total**: 32h (wall-clock: 32h)

---

## Timeline Summary

| Phase | Wall-clock Time | Cumulative |
|-------|-----------------|------------|
| Wave 1 (parallel) | 19h | 19h |
| Wave 2 | 13h | 32h |
| Wave 3 | 32h | 64h |

**Total Wall-Clock**: ~64 hours (~8 days)
**Total Effort**: 79 hours

## Quality Gates

### Standard Mode (All Tasks)
- **Coverage**: 80% for feature tasks, 60% for scaffolding
- **Architectural Review**: 60+ score for feature tasks
- **Tests Required**: Yes (pytest)

### Task Type Profiles
- `scaffolding`: No arch review, no coverage requirement
- `feature`: Full quality gates
- `testing`: Coverage requirement only
- `documentation`: No quality gates

## Verification Checkpoints

### After Wave 1
```bash
# Verify feature detection
/feature-plan "implement FEAT-TEST-001" --dry-run
# Should show: "Found feature spec: ..."

# Verify interactive capture
guardkit graphiti capture --interactive --focus project-overview
# Should show: Q&A session flow
```

### After Wave 2
```bash
# Verify query commands
guardkit graphiti show feature FEAT-TEST-001
guardkit graphiti search "authentication"
guardkit graphiti list features
guardkit graphiti status --verbose

# Verify turn state capture
# (requires feature-build run)
```

### After Wave 3
```bash
# Verify job-specific context
/task-work TASK-XXX --verbose
# Should show: "Job-Specific Context" section with budget used

# Verify AutoBuild context
/feature-build TASK-XXX --verbose
# Should show: role_constraints, quality_gate_configs, turn_states
```

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Wave 1 integration issues | Integration tests after both tracks complete |
| Turn state schema changes | Version schema, add migration path |
| Performance degradation | Add caching, benchmark early in Wave 3 |
| Context budget ineffective | Start with fixed allocation, tune based on telemetry |

## Next Steps

1. Start Wave 1 with Conductor (2 workspaces)
2. Run Track A (GR-003) and Track B (GR-004) in parallel
3. Integration testing after Wave 1 completion
4. Proceed to Wave 2 (GR-005)
5. Final integration and Wave 3 (GR-006)
