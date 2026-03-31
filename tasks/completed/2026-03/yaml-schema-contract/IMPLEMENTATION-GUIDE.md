# Implementation Guide: YAML Schema Contract Enforcement

**Feature ID**: FEAT-YSC
**Parent Review**: TASK-REV-YAML
**Total Tasks**: 5
**Estimated Duration**: 11-15 hours
**Waves**: 3

## Wave Breakdown

### Wave 1: Foundation (2 tasks, parallel)

No dependencies. Can be executed simultaneously.

| Task | Title | Mode | Complexity | Est. |
|------|-------|------|-----------|------|
| TASK-YSC-001 | Add schema ref to system-plan.md | direct | 2 | 1h |
| TASK-YSC-002 | Create Pydantic schema models | task-work | 6 | 4-6h |

**TASK-YSC-001** is a documentation-only change (add schema reference to `.claude/commands/system-plan.md`). Quick win that prevents the FEAT-AC1A class of bugs immediately.

**TASK-YSC-002** is the core fix. Replaces dataclasses with Pydantic models in `feature_loader.py` for strict type enforcement. This is the prerequisite for all subsequent tasks.

### Wave 2: Validation Layer (2 tasks, parallel)

Depends on: TASK-YSC-002

| Task | Title | Mode | Complexity | Est. |
|------|-------|------|-----------|------|
| TASK-YSC-003 | Add schema validation tests | task-work | 4 | 2-3h |
| TASK-YSC-004 | Add write-time validation | task-work | 4 | 2-3h |

**TASK-YSC-003** adds the missing test cases (invalid status, extra fields, round-trip).

**TASK-YSC-004** adds `validate_yaml()` to FeatureLoader and integrates it into all write paths.

### Wave 3: Developer Experience (1 task)

Depends on: TASK-YSC-004

| Task | Title | Mode | Complexity | Est. |
|------|-------|------|-----------|------|
| TASK-YSC-005 | CLI validate command | task-work | 4 | 2-3h |

**TASK-YSC-005** adds `guardkit feature validate FEAT-XXX` for pre-flight checks.

## Dependency Graph

```
TASK-YSC-001 ─────────────────────────── (independent)

TASK-YSC-002 ──┬── TASK-YSC-003
               └── TASK-YSC-004 ──── TASK-YSC-005
```

## Key Design Decisions

1. **Pydantic over JSON Schema**: Pydantic provides both runtime validation and JSON Schema export, avoiding maintaining two separate schemas
2. **`extra="warn"` not `extra="forbid"`**: Start with warnings to avoid breaking existing YAMLs, tighten later
3. **Write-time validation is defense-in-depth**: Even with Pydantic parse-time validation, write-time validation catches bugs in generators before files reach disk
4. **CLI validate is optional but valuable**: Provides explicit pre-flight check for CI/CD and manual workflows

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Breaking existing valid YAMLs | Use `extra="warn"`, comprehensive backward-compat tests |
| Pydantic v1 vs v2 API | GuardKit uses Pydantic v2, follow existing patterns |
| Performance regression | Pydantic validation adds ~1ms overhead, negligible |
| `generate_feature_yaml.py` breaks | Update in same PR as TASK-YSC-002 |
