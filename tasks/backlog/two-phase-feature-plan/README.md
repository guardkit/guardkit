# FEAT-FP-002: Two-Phase Feature Plan Enhancements

Enhanced `/feature-plan` for two-phase AI workflows: research with frontier model → autonomous implementation with local model.

## Status

**Status:** Planned
**Complexity:** 7/10 (aggregate)
**Tasks:** 11
**Waves:** 4

## Quick Start

```bash
# Autonomous build (all 11 tasks)
/feature-build FEAT-FP-002

# Or task-by-task
/task-work TASK-FP002-001  # Start with Spec Parser
```

## Tasks

### Wave 1 (Foundation)
- [TASK-FP002-001](TASK-FP002-001-research-template-spec-parser.md) — Research Template Spec Parser (complexity: 5)
- [TASK-FP002-002](TASK-FP002-002-target-mode-configuration.md) — Target Mode Configuration (complexity: 3)

### Wave 2 (Core Generators)
- [TASK-FP002-003](TASK-FP002-003-adr-file-generator.md) — ADR File Generator (complexity: 4)
- [TASK-FP002-004](TASK-FP002-004-quality-gate-yaml-generator.md) — Quality Gate YAML Generator (complexity: 5)
- [TASK-FP002-005](TASK-FP002-005-task-metadata-enricher.md) — Task Metadata Enricher (complexity: 5)
- [TASK-FP002-006](TASK-FP002-006-warnings-extractor-and-seed-script.md) — Warnings + Seed Script Generator (complexity: 3)
- [TASK-FP002-010](TASK-FP002-010-documentation-research-template-guide.md) — Research Template Guide (complexity: 3)

### Wave 3 (Command Integration)
- [TASK-FP002-007](TASK-FP002-007-feature-plan-command-integration.md) — Feature-Plan Command Integration (complexity: 7)

### Wave 4 (Docs + Tests)
- [TASK-FP002-008](TASK-FP002-008-documentation-two-phase-workflow-guide.md) — Two-Phase Workflow Guide (complexity: 4)
- [TASK-FP002-009](TASK-FP002-009-documentation-feature-plan-reference.md) — Feature-Plan Reference (complexity: 3)
- [TASK-FP002-011](TASK-FP002-011-integration-and-e2e-tests.md) — Integration & E2E Tests (complexity: 7)

## Key Files

- Feature spec: `docs/research/system-level-understanding/FEAT-FP-002-two-phase-feature-plan-enhancements.md`
- Implementation guide: [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md)
- Feature YAML: `.guardkit/features/FEAT-FP-002.yaml`

## New Modules

All in `guardkit/planning/`:
- `spec_parser.py` — Parse Research Template markdown
- `target_mode.py` — Handle `--target` flag
- `adr_generator.py` — Generate ADR files
- `quality_gate_generator.py` — Generate quality gate YAML
- `task_metadata.py` — Enrich task markdown
- `warnings_extractor.py` — Extract warnings for Graphiti
- `seed_script_generator.py` — Generate Graphiti seeding scripts
