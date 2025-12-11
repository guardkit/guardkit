# Implementation Guide: Claude Code Rules Structure

## Execution Strategy

This guide provides a wave-based execution plan for implementing Claude Code rules structure support in GuardKit. Tasks are organized to maximize parallel execution opportunities using Conductor.build.

## Wave Overview

```
Wave 1: Foundation (Sequential)
└── CRS-001: Increase size limit

Wave 2: Core Implementation
└── CRS-002: RulesStructureGenerator

Wave 3: Integration (Parallel: 3 tasks)
├── CRS-003: CLI flag
├── CRS-004: Path inference
└── CRS-005: template-create docs

Wave 4: Template Refactoring (Parallel: 5 tasks)
├── CRS-006: fastapi-python
├── CRS-007: react-typescript
├── CRS-008: nextjs-fullstack
├── CRS-009: react-fastapi-monorepo
└── CRS-010: default

Wave 5: Documentation (Parallel: 3 tasks)
├── CRS-011: Quick-start guide
├── CRS-012: Root CLAUDE.md
└── CRS-013: Template READMEs
```

---

## Wave 1: Foundation

**Duration**: 1-2 hours
**Parallel Opportunities**: None (single task)

### TASK-CRS-001: Increase Size Limit to 25KB

**Method**: Direct implementation (simple code change)

```bash
# Direct edit - no /task-work needed
# Modify 2 files, 2 lines each
```

**Files**:
- `installer/core/lib/template_generator/models.py:409`
- `installer/core/commands/lib/template_create_orchestrator.py:125`

**Change**: `10 * 1024` → `25 * 1024`

**Verification**:
```bash
pytest tests/lib/template_generator/test_orchestrator_split_claude_md.py -v -k size
```

---

## Wave 2: Core Implementation

**Duration**: 4-6 hours
**Parallel Opportunities**: None (single task, critical path)

### TASK-CRS-002: RulesStructureGenerator Class

**Method**: `/task-work` (complex implementation, quality gates required)

```bash
/task-work TASK-CRS-002
```

**Key Deliverables**:
1. New file: `installer/core/lib/template_generator/rules_structure_generator.py`
2. `RulesStructureGenerator` class with:
   - `generate()` method returning dict of file paths → content
   - `_generate_core_claudemd()` for minimal core (~5KB)
   - `_generate_code_style_rules()` with extension detection
   - `_generate_testing_rules()` with test path patterns
   - `_generate_pattern_rules()` for architecture patterns
   - `_generate_agent_rules()` with paths frontmatter
3. Unit tests in `tests/lib/template_generator/test_rules_generator.py`

**Conductor Workspace**: `claude-rules-wave2-1`

---

## Wave 3: Integration

**Duration**: 5-8 hours total
**Parallel Opportunities**: HIGH (3 independent tasks)

### Conductor Setup

```bash
# Create 3 parallel workspaces
conductor create claude-rules-wave3-1  # CRS-003
conductor create claude-rules-wave3-2  # CRS-004
conductor create claude-rules-wave3-3  # CRS-005
```

### TASK-CRS-003: CLI Flag --use-rules-structure

**Method**: Direct implementation

**Workspace**: `claude-rules-wave3-1`

**Files**:
- `installer/core/commands/lib/template_create_orchestrator.py`

**Changes**:
1. Add `use_rules_structure: bool = False` to `OrchestrationConfig`
2. Add argument parser for `--use-rules-structure`
3. Add `_write_rules_structure()` method
4. Conditional logic in `_write_output()`

### TASK-CRS-004: Path Pattern Inference

**Method**: `/task-work` (complex logic)

**Workspace**: `claude-rules-wave3-2`

```bash
/task-work TASK-CRS-004
```

**Key Deliverables**:
1. `PathPatternInferrer` class
2. Layer-based path inference
3. Technology-based pattern mapping
4. Fallback heuristics

### TASK-CRS-005: template-create Documentation

**Method**: Direct implementation

**Workspace**: `claude-rules-wave3-3`

**File**: `installer/core/commands/template-create.md`

**Changes**:
- Add usage examples
- Document output structure
- Add to flags reference
- Update workflow phases

---

## Wave 4: Template Refactoring

**Duration**: 20-30 hours total
**Parallel Opportunities**: MAXIMUM (5 independent tasks)

### Conductor Setup

```bash
# Create 5 parallel workspaces
conductor create claude-rules-wave4-1  # CRS-006 fastapi-python
conductor create claude-rules-wave4-2  # CRS-007 react-typescript
conductor create claude-rules-wave4-3  # CRS-008 nextjs-fullstack
conductor create claude-rules-wave4-4  # CRS-009 react-fastapi-monorepo
conductor create claude-rules-wave4-5  # CRS-010 default
```

### Execution Priority

| Priority | Task | Template | Reason |
|----------|------|----------|--------|
| 1 | CRS-006 | fastapi-python | Largest (29.2KB), highest benefit |
| 2 | CRS-007 | react-typescript | Popular, medium complexity |
| 3 | CRS-008 | nextjs-fullstack | Complex server/client split |
| 4 | CRS-009 | react-fastapi-monorepo | Monorepo patterns |
| 5 | CRS-010 | default | Smallest, can be done last |

### TASK-CRS-006: Refactor fastapi-python

**Method**: `/task-work` (high impact)

**Workspace**: `claude-rules-wave4-1`

```bash
/task-work TASK-CRS-006
```

**Target Structure**:
```
fastapi-python/
├── .claude/
│   ├── CLAUDE.md (~5KB)
│   └── rules/
│       ├── code-style.md
│       ├── testing.md
│       ├── api/
│       │   ├── routing.md
│       │   ├── dependencies.md
│       │   └── schemas.md
│       ├── database/
│       │   ├── models.md
│       │   ├── crud.md
│       │   └── migrations.md
│       └── agents/
│           ├── fastapi.md
│           ├── database.md
│           └── testing.md
```

### TASK-CRS-007: Refactor react-typescript

**Method**: `/task-work`

**Workspace**: `claude-rules-wave4-2`

### TASK-CRS-008: Refactor nextjs-fullstack

**Method**: `/task-work`

**Workspace**: `claude-rules-wave4-3`

### TASK-CRS-009: Refactor react-fastapi-monorepo

**Method**: `/task-work`

**Workspace**: `claude-rules-wave4-4`

### TASK-CRS-010: Refactor default

**Method**: Direct implementation (simple)

**Workspace**: `claude-rules-wave4-5`

---

## Wave 5: Documentation

**Duration**: 9-13 hours total
**Parallel Opportunities**: HIGH (3 independent tasks)

### Conductor Setup

```bash
# Create 3 parallel workspaces
conductor create claude-rules-wave5-1  # CRS-011
conductor create claude-rules-wave5-2  # CRS-012
conductor create claude-rules-wave5-3  # CRS-013
```

### TASK-CRS-011: Quick-Start Guide

**Method**: Direct implementation

**Workspace**: `claude-rules-wave5-1`

**File**: `docs/guides/rules-structure-guide.md`

### TASK-CRS-012: Update Root CLAUDE.md

**Method**: Direct implementation

**Workspace**: `claude-rules-wave5-2`

**File**: `CLAUDE.md`

### TASK-CRS-013: Update Template READMEs

**Method**: Direct implementation

**Workspace**: `claude-rules-wave5-3`

**Files** (5 templates):
- `installer/core/templates/*/README.md`

---

## Execution Timeline

### Sequential Path (No Parallelization)

```
Wave 1: 1-2 hours
Wave 2: 4-6 hours
Wave 3: 5-8 hours (sum of 3 tasks)
Wave 4: 21-30 hours (sum of 5 tasks)
Wave 5: 9-13 hours (sum of 3 tasks)
─────────────────────
Total: 40-59 hours
```

### Parallel Path (With Conductor)

```
Wave 1: 1-2 hours (sequential)
Wave 2: 4-6 hours (sequential)
Wave 3: 3-4 hours (3 tasks in parallel, max duration)
Wave 4: 6-8 hours (5 tasks in parallel, max duration)
Wave 5: 4-6 hours (3 tasks in parallel, max duration)
─────────────────────
Total: 18-26 hours (55% faster)
```

---

## Quality Gates

### For `/task-work` Tasks (CRS-002, 004, 006-009)

- Phase 2.5: Architectural review (SOLID/DRY/YAGNI)
- Phase 4: Test execution (100% pass rate)
- Phase 4.5: Coverage enforcement (≥80%)
- Phase 5: Code review
- Phase 5.5: Plan audit

### For Direct Tasks (CRS-001, 003, 005, 010-013)

- Manual code review
- Verify changes compile/work
- Test with sample commands

---

## Rollback Plan

### If Issues Arise

1. **Size limit change** (CRS-001): Revert to 10KB if needed
2. **Rules structure** (CRS-002-005): Keep as opt-in, don't affect default
3. **Template refactoring** (CRS-006-010): Keep original structure alongside rules/
4. **Documentation** (CRS-011-013): No rollback needed (additive)

### Backward Compatibility

- Single CLAUDE.md remains default
- `--use-rules-structure` is opt-in
- Existing templates work unchanged
- Rules structure is additive, not replacement

---

## Next Steps

1. **Start Wave 1**: Execute CRS-001 (direct edit)
2. **Start Wave 2**: Execute CRS-002 with `/task-work`
3. **Plan Conductor**: Set up workspaces for Waves 3-5
4. **Execute in Parallel**: Use Conductor for maximum efficiency

```bash
# Quick start
/task-work TASK-CRS-001  # Or direct edit

# After Wave 1 complete
/task-work TASK-CRS-002

# After Wave 2, set up parallel workspaces
conductor create claude-rules-wave3-1
conductor create claude-rules-wave3-2
conductor create claude-rules-wave3-3
```
