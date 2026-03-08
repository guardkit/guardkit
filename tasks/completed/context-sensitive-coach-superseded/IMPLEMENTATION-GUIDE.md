# Implementation Guide: Context-Sensitive Coach

## Wave Execution Strategy

This feature uses parallel execution with Conductor workspaces for maximum efficiency.

## Wave 1: Foundation (Parallel)

**Tasks**: TASK-CSC-001, TASK-CSC-002
**Estimated Duration**: 4-6 hours
**Parallelizable**: Yes (no dependencies between tasks)

### TASK-CSC-001: Data Models and Universal Context Gatherer
- Create `UniversalContext` dataclass
- Create `ContextAnalysisResult` dataclass
- Implement `UniversalContextGatherer` class
- Git diff analysis (lines added/modified/deleted)
- File categorization (source, test, config)

### TASK-CSC-002: Fast Classification Gate
- Create `FastClassifier` class
- Implement `_is_obviously_trivial()` (<30 LOC, 1-2 files)
- Implement `_is_obviously_complex()` (>300 LOC, >10 files)
- Add logging for classification decisions

## Wave 2: AI Analysis (Parallel)

**Tasks**: TASK-CSC-003, TASK-CSC-004
**Estimated Duration**: 6-8 hours
**Parallelizable**: Yes (no dependencies between tasks)
**Depends On**: Wave 1

### TASK-CSC-003: AI Context Analysis
- Create `AIContextAnalyzer` class
- Define analysis prompt
- Implement `_invoke_ai_analysis()` using existing agent infrastructure
- Parse and validate AI response
- Add testability scoring logic

### TASK-CSC-004: Context Caching
- Create `ContextCache` class
- Implement cache key computation (based on file hashes)
- Add cache invalidation for changed files
- Implement cache persistence between turns

## Wave 3: Integration (Sequential)

**Tasks**: TASK-CSC-005
**Estimated Duration**: 4-6 hours
**Parallelizable**: N/A (single task)
**Depends On**: Wave 2

### TASK-CSC-005: CoachValidator Integration
- Create `ContextSensitiveCoachValidator` class
- Wire up universal context → classification → AI analysis → profile selection
- Integrate with existing `CoachValidator.validate()` method
- Add feature flag for gradual rollout
- Preserve backward compatibility

## Wave 4: Quality Assurance (Parallel)

**Tasks**: TASK-CSC-006, TASK-CSC-007
**Estimated Duration**: 4-6 hours
**Parallelizable**: Yes (no dependencies between tasks)
**Depends On**: Wave 3

### TASK-CSC-006: Testing
- Unit tests for `UniversalContextGatherer`
- Unit tests for `FastClassifier`
- Unit tests for `AIContextAnalyzer`
- Integration test with mock AI responses
- Test cache invalidation

### TASK-CSC-007: Documentation
- Update proposal with final implementation details
- Add usage guide to CLAUDE.md
- Document configuration options

## Conductor Workspace Assignment

| Wave | Task | Workspace Name |
|------|------|----------------|
| 1 | TASK-CSC-001 | csc-wave1-models |
| 1 | TASK-CSC-002 | csc-wave1-classifier |
| 2 | TASK-CSC-003 | csc-wave2-analyzer |
| 2 | TASK-CSC-004 | csc-wave2-cache |
| 3 | TASK-CSC-005 | csc-wave3-integration |
| 4 | TASK-CSC-006 | csc-wave4-tests |
| 4 | TASK-CSC-007 | csc-wave4-docs |

## Quality Gate Profiles for These Tasks

| Task | task_type | Profile | Rationale |
|------|-----------|---------|-----------|
| CSC-001 | feature | standard | Data models with validation |
| CSC-002 | feature | standard | Logic with branching |
| CSC-003 | feature | standard | AI integration complexity |
| CSC-004 | feature | standard | Cache with state management |
| CSC-005 | feature | strict | Integration - higher risk |
| CSC-006 | testing | infrastructure | Test files |
| CSC-007 | documentation | documentation | Docs only |

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| AI analysis latency | Fast classification gate skips AI for obvious cases |
| AI response parsing errors | Robust JSON parsing with fallback to standard profile |
| Cache consistency | Cache invalidation based on file hashes |
| Backward compatibility | Feature flag for gradual rollout |

## Success Criteria

1. Trivial tasks (<30 LOC) pass with minimal profile
2. Declarative code (DTOs, configs) passes without coverage gate
3. Complex tasks still get full validation
4. Latency < 3s for AI analysis cases
5. Latency < 100ms for cached/obvious cases
6. All existing tests continue to pass
