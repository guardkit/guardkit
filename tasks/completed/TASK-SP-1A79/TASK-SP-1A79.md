---
id: TASK-SP-1A79
title: Replace system_plan.py stub with working orchestrator
status: completed
created: 2026-02-14T10:00:00Z
updated: 2026-02-14T12:00:00Z
completed: 2026-02-14T12:00:00Z
completed_location: tasks/completed/TASK-SP-1A79/
priority: high
tags: [system-plan, orchestrator, graphiti, stub-replacement]
complexity: 6
feature_id: FEAT-SP-001
test_results:
  status: passed
  coverage: 91
  last_run: 2026-02-14T12:00:00Z
  tests_total: 56
  tests_passed: 56
  tests_failed: 0
organized_files:
  - TASK-SP-1A79.md
---

# Task: Replace system_plan.py stub with working orchestrator

## Description

`guardkit/planning/system_plan.py` is a 70-line stub where `run_system_plan()` does `pass`. This was identified by TASK-REV-STUB as the root cause of `/system-plan` failing to persist architecture to Graphiti. All supporting infrastructure is built and working — entity definitions, persistence layer, architecture writer, mode detector, CLI wiring, command spec — but the orchestrator that connects them is missing.

Replace the stub with a working `run_system_plan()` that parses a structured markdown spec file (`--context` flag), extracts entities (SystemContextDef, ComponentDef, CrosscuttingConcernDef, ArchitectureDecision), upserts them via `SystemPlanGraphiti`, generates markdown artefacts via `ArchitectureWriter`, and reports results.

## Acceptance Criteria

- [ ] AC-001: `run_system_plan()` function body is not a stub (contains actual orchestration logic, >50 meaningful lines)
- [ ] AC-002: `guardkit system-plan "GuardKit" --context docs/architecture/guardkit-system-spec.md` completes without error
- [ ] AC-003: Graphiti `project_architecture` group contains structured entities after run
- [ ] AC-004: Graphiti `project_decisions` group contains ADR entities after run
- [ ] AC-005: `run_system_plan()` calls `detect_mode()` when no `--mode` override provided
- [ ] AC-006: `run_system_plan()` calls `SystemPlanGraphiti.upsert_component()` for each parsed component
- [ ] AC-007: `run_system_plan()` calls `SystemPlanGraphiti.upsert_adr()` for each parsed ADR
- [ ] AC-008: `run_system_plan()` calls `SystemPlanGraphiti.upsert_system_context()` for system context
- [ ] AC-009: `run_system_plan()` calls `SystemPlanGraphiti.upsert_crosscutting()` for each concern
- [ ] AC-010: Architecture markdown artefacts generated via `ArchitectureWriter`
- [ ] AC-011: Console output reports number of entities persisted per type and files written
- [ ] AC-012: Graceful degradation when Graphiti unavailable (markdown-only mode, warning displayed)
- [ ] AC-013: Unit tests exist with >80% coverage of `run_system_plan()` logic
- [ ] AC-014: Unit tests mock Graphiti calls and verify correct entity counts passed to upsert methods

## Implementation Notes

### What Exists (DO NOT recreate)

| Module | Status |
|--------|--------|
| `guardkit/planning/graphiti_arch.py` (358 lines) | Fully implemented: `upsert_component()`, `upsert_adr()`, `upsert_system_context()`, `upsert_crosscutting()`, `has_architecture_context()`, `get_architecture_summary()`, `get_relevant_context_for_topic()` |
| `guardkit/planning/mode_detector.py` (~100 lines) | `detect_mode()` with graceful degradation |
| `guardkit/planning/architecture_writer.py` | Markdown artefact generation |
| `guardkit/knowledge/entities/component.py` (~80 lines) | `ComponentDef` dataclass |
| `guardkit/knowledge/entities/system_context.py` (~60 lines) | `SystemContextDef` dataclass |
| `guardkit/knowledge/entities/crosscutting.py` (~70 lines) | `CrosscuttingConcernDef` dataclass |
| `guardkit/knowledge/entities/architecture_context.py` (~90 lines) | `ArchitectureDecision` dataclass |
| `.claude/commands/system-plan.md` (400+ lines) | Full interactive flow specification |
| `guardkit/cli/system_plan.py` | CLI registered in `main.py` |

### Files to Create/Modify

- `guardkit/planning/system_plan.py` — **Replace stub** with ~200-300 line orchestrator
- `guardkit/planning/spec_parser.py` — Check if existing parser handles architecture specs, extend if needed
- `tests/unit/planning/test_system_plan.py` — Tests for orchestration logic
- `tests/unit/planning/test_spec_parser_arch.py` — Tests for architecture spec parsing (if parser extended)

### Files NOT to Touch

- `guardkit/planning/graphiti_arch.py` — Already complete
- `guardkit/planning/mode_detector.py` — Already complete
- `guardkit/planning/architecture_writer.py` — Already complete
- `guardkit/knowledge/entities/*.py` — Already complete
- `.claude/commands/system-plan.md` — Already complete
- `guardkit/cli/system_plan.py` — Already wired

### Key Technical Details

- Follow the pattern in `guardkit/cli/review.py` for async wrapping at CLI boundary
- Spec parser should be defensive — missing sections should produce warnings, not errors
- Entity IDs should follow the hash-based ID pattern per `.claude/rules/hash-based-ids.md`
- The `to_episode_body()` method on each entity dataclass returns the JSON for Graphiti — use it
- Check existing `spec_parser.py` first — it may already have infrastructure to build on
- Spec file format uses heading patterns: `### COMP-`, `### XC-`, `### ADR-SP-` prefixes

### Pre-Requisite

Before first run, clear stale Graphiti groups. Clear `project_architecture` and `project_decisions` groups. Keep `product_knowledge` and `project_overview`.

## Test Requirements

- [ ] Unit tests for spec parsing (entity extraction from markdown)
- [ ] Unit tests for orchestration flow (mock Graphiti, verify upsert calls)
- [ ] Unit tests for graceful degradation (Graphiti unavailable scenario)
- [ ] Unit tests for mode detection integration

## Coach Validation Commands

```bash
# Verify not a stub
python -c "
from pathlib import Path
content = Path('guardkit/planning/system_plan.py').read_text()
lines = [l for l in content.split('\n') if l.strip() and not l.strip().startswith('#') and not l.strip().startswith('\"')]
assert len(lines) > 50, f'Still a stub: only {len(lines)} non-comment lines'
assert 'upsert_component' in content, 'Missing upsert_component call'
assert 'upsert_adr' in content, 'Missing upsert_adr call'
assert 'detect_mode' in content, 'Missing detect_mode call'
print('Anti-stub validation OK')
"

# Verify tests exist
python -c "
from pathlib import Path
assert Path('tests/unit/planning/test_system_plan.py').exists(), 'Missing test file'
content = Path('tests/unit/planning/test_system_plan.py').read_text()
assert content.count('def test_') >= 3, f'Too few tests: {content.count(\"def test_\")}'
print('Test existence validation OK')
"
```

## Test Execution Log

[Automatically populated by /task-work]
