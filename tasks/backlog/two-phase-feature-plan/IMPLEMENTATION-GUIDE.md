# Implementation Guide: FEAT-FP-002 — Two-Phase Feature Plan Enhancements

## Overview

This feature enhances `/feature-plan` to support two-phase AI workflows: Phase 1 (research & planning with frontier model) → Phase 2 (autonomous implementation with local model). All new modules live in `guardkit/planning/` with no changes to existing orchestrator or knowledge modules.

## Architecture

```
Research Template (.md)
        │
        ▼
┌──────────────────┐     ┌──────────────────┐
│   SpecParser     │     │   TargetMode     │
│   (TASK-001)     │     │   (TASK-002)     │
└────────┬─────────┘     └────────┬─────────┘
         │                        │
         ├────────────────────────┤
         │         │         │    │         │
         ▼         ▼         ▼    ▼         ▼
┌────────────┐ ┌────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐
│ADRGenerator│ │QGGen   │ │Metadata │ │Warnings  │ │DocGuide  │
│(TASK-003)  │ │(004)   │ │(005)    │ │+Seed(006)│ │(010)     │
└─────┬──────┘ └───┬────┘ └────┬────┘ └────┬─────┘ └──────────┘
      │            │           │            │
      └────────────┴───────────┴────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │  Command Integ.  │
              │  (TASK-007)      │
              └────────┬─────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│Workflow Guide│ │Ref Docs  │ │Integration   │
│(TASK-008)    │ │(009)     │ │Tests (011)   │
└──────────────┘ └──────────┘ └──────────────┘
```

## Execution Waves

### Wave 1: Foundation (No Dependencies)
Tasks that can run in parallel — they have no dependencies on each other.

| Task | Name | Complexity | Mode | Est. Time |
|------|------|-----------|------|-----------|
| TASK-FP002-001 | Research Template Spec Parser | 5/10 | task-work | 60 min |
| TASK-FP002-002 | Target Mode Configuration | 3/10 | task-work | 30 min |

### Wave 2: Core Generators (Depend on Wave 1)
All depend on TASK-001 (SpecParser output types). TASK-005 also depends on TASK-002.

| Task | Name | Complexity | Mode | Est. Time |
|------|------|-----------|------|-----------|
| TASK-FP002-003 | ADR File Generator | 4/10 | task-work | 45 min |
| TASK-FP002-004 | Quality Gate YAML Generator | 5/10 | task-work | 60 min |
| TASK-FP002-005 | Task Metadata Enricher | 5/10 | task-work | 60 min |
| TASK-FP002-006 | Warnings Extractor + Seed Script | 3/10 | task-work | 30 min |
| TASK-FP002-010 | Research Template Guide (Docs) | 3/10 | task-work | 30 min |

### Wave 3: Command Integration (Depends on Waves 1-2)
Integrates all modules into the `/feature-plan` command.

| Task | Name | Complexity | Mode | Est. Time |
|------|------|-----------|------|-----------|
| TASK-FP002-007 | Feature-Plan Command Integration | 7/10 | task-work | 90 min |

### Wave 4: Documentation + Tests (Depends on Wave 3)
Final wave — docs and comprehensive testing.

| Task | Name | Complexity | Mode | Est. Time |
|------|------|-----------|------|-----------|
| TASK-FP002-008 | Two-Phase Workflow Guide (Docs) | 4/10 | task-work | 45 min |
| TASK-FP002-009 | Feature-Plan Reference (Docs) | 3/10 | task-work | 30 min |
| TASK-FP002-011 | Integration & E2E Tests | 7/10 | task-work | 90 min |

**Total Estimated Duration:** ~570 min (~9.5 hours)

## Key Technology Seams

These are the module boundaries where integration errors typically occur. TASK-FP002-011 specifically tests each of these:

| Seam | Producer | Consumer | Data Type |
|------|----------|----------|-----------|
| 1 | SpecParser | ADRGenerator | `list[Decision]` |
| 2 | SpecParser | QualityGateGenerator | `list[TaskDefinition]` |
| 3 | SpecParser + TargetMode | TaskMetadataEnricher | `TaskDefinition` + `TargetConfig` |
| 4 | SpecParser | WarningsExtractor | `list[str]` (warnings) |
| 5 | ADRGenerator | SeedScriptGenerator | `list[Path]` (ADR file paths) |
| 6 | WarningsExtractor | SeedScriptGenerator | `Path` (warnings file) |
| 7 | TaskMetadataEnricher | YAML frontmatter | `str` (rendered markdown) |

## Quality Gates

```bash
# Lint all planning modules
ruff check guardkit/planning/

# Unit tests (all modules)
pytest tests/unit/test_spec_parser.py tests/unit/test_target_mode.py \
    tests/unit/test_adr_generator.py tests/unit/test_quality_gate_generator.py \
    tests/unit/test_task_metadata.py tests/unit/test_warnings_extractor.py \
    tests/unit/test_seed_script_generator.py -v --tb=short

# Integration tests (pipeline + seams)
pytest tests/integration/test_feature_plan_pipeline.py \
    tests/integration/test_planning_module_seams.py -v

# Import verification
python -c "
from guardkit.planning.spec_parser import parse_research_template
from guardkit.planning.target_mode import TargetMode, resolve_target
from guardkit.planning.adr_generator import generate_adrs
from guardkit.planning.quality_gate_generator import generate_quality_gates
from guardkit.planning.task_metadata import enrich_task, render_task_markdown
from guardkit.planning.warnings_extractor import extract_warnings
from guardkit.planning.seed_script_generator import generate_seed_script
print('All imports OK')
"
```

## Decision References

| Decision | Summary | Implemented In |
|----------|---------|---------------|
| D1 | `--target` flag with `interactive`/`local-model`/`auto` | TASK-002, TASK-007 |
| D2 | Research template as input via `--from-spec` | TASK-001, TASK-007 |
| D3 | Auto-generate ADR files from Decision Log | TASK-003 |
| D4 | Per-feature quality gate YAML | TASK-004 |
| D5 | Rich task metadata (domain tags, file constraints, turn budgets) | TASK-005 |
| D6 | 11-section Research Template as canonical format | TASK-001, TASK-010 |
| D7 | Generate Graphiti seeding script | TASK-006 |
| D8 | Documentation as required deliverable | TASK-008, TASK-009, TASK-010 |
| D9 | Backward compatibility (additive-only changes) | TASK-007 |
| D10 | Turn budget hints based on complexity | TASK-005 |

## Notes

- All new code in `guardkit/planning/` — no changes to orchestrator, knowledge, or CLI layers
- `pyyaml` is the only dependency (already in project)
- All tests use `tmp_path` — no writes to actual project directories
- Backward compatible — existing `/feature-plan "description"` behavior unchanged
