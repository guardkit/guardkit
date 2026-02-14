---
title: "Replace system_plan.py stub with working orchestrator"
priority: P0
complexity: 6
tags: [system-plan, orchestrator, graphiti, stub-replacement]
feature_id: FEAT-SP-001
implementation_mode: task-work
---

# Replace system_plan.py Stub with Working Orchestrator

## Problem

`guardkit/planning/system_plan.py` is a 70-line stub where `run_system_plan()` does `pass`. This was identified by TASK-REV-STUB as the root cause of `/system-plan` failing to persist architecture to Graphiti. All supporting infrastructure is built and working — entity definitions, persistence layer, architecture writer, mode detector, CLI wiring, command spec — but the orchestrator that connects them is missing.

Running `/system-plan` currently generates markdown files (Claude Code follows the command spec directly) but Graphiti persistence never occurs, which means `/system-overview`, `/impact-analysis`, and `/context-switch` all return "no context available".

## What Exists (DO NOT recreate)

| Module | Lines | Status |
|--------|-------|--------|
| `guardkit/planning/graphiti_arch.py` | 358 | Fully implemented: `upsert_component()`, `upsert_adr()`, `upsert_system_context()`, `upsert_crosscutting()`, `has_architecture_context()`, `get_architecture_summary()`, `get_relevant_context_for_topic()` |
| `guardkit/planning/mode_detector.py` | ~100 | `detect_mode()` with graceful degradation |
| `guardkit/planning/architecture_writer.py` | built | Markdown artefact generation |
| `guardkit/knowledge/entities/component.py` | ~80 | `ComponentDef` dataclass |
| `guardkit/knowledge/entities/system_context.py` | ~60 | `SystemContextDef` dataclass |
| `guardkit/knowledge/entities/crosscutting.py` | ~70 | `CrosscuttingConcernDef` dataclass |
| `guardkit/knowledge/entities/architecture_context.py` | ~90 | `ArchitectureDecision` dataclass |
| `.claude/commands/system-plan.md` | 400+ | Full interactive flow specification |
| `guardkit/cli/system_plan.py` | built | CLI registered in `main.py` |

## What Must Be Implemented

Replace the stub in `guardkit/planning/system_plan.py` with a working `run_system_plan()` that:

### Phase 1: Context file parsing (`--context` flag — immediate priority)

1. Accept `--context path/to/spec.md` parameter
2. Parse the structured markdown spec file into entity instances:
   - Extract system context section -> `SystemContextDef`
   - Extract component sections -> list of `ComponentDef`
   - Extract cross-cutting concerns -> list of `CrosscuttingConcernDef`
   - Extract ADR sections -> list of `ArchitectureDecision`
3. Call `SystemPlanGraphiti.upsert_*()` methods for each entity
4. Call `ArchitectureWriter` to generate/update markdown artefacts
5. Report results: entity counts persisted, files written

### Phase 2: Mode detection and orchestration

1. Call `detect_mode()` to determine setup/refine/review
2. If `--mode` provided, use override instead
3. Display detected mode to user
4. Handle `--no-questions` and `--defaults` flags

### Spec File Format (already exists at `docs/architecture/guardkit-system-spec.md`)

The spec uses markdown sections with consistent patterns:
- `## 1. System Context` — name, purpose, methodology, actors, external systems
- `## 2. Component Catalogue` — `### COMP-xxx: Name` subsections with responsibilities, dependencies, boundaries
- `## 4. Cross-Cutting Concerns` — `### XC-xxx: Name` subsections
- `## 5. Architecture Decisions` — `### ADR-SP-xxx: Title` subsections with context, decision, consequences, status

The parser should use these heading patterns to extract entities. Regex-based extraction matching `### COMP-`, `### XC-`, `### ADR-SP-` prefixes is sufficient.

## Files to Create/Modify

- `guardkit/planning/system_plan.py` — **Replace stub** with ~200-300 line orchestrator
- `guardkit/planning/spec_parser.py` — Check if existing parser handles architecture specs, extend if needed (a spec_parser.py already exists — review it first)
- `tests/unit/planning/test_system_plan.py` — Tests for orchestration logic
- `tests/unit/planning/test_spec_parser_arch.py` — Tests for architecture spec parsing (if parser extended)

## Files NOT to Touch

- `guardkit/planning/graphiti_arch.py` — Already complete
- `guardkit/planning/mode_detector.py` — Already complete
- `guardkit/planning/architecture_writer.py` — Already complete
- `guardkit/knowledge/entities/*.py` — Already complete
- `.claude/commands/system-plan.md` — Already complete
- `guardkit/cli/system_plan.py` — Already wired

## Pre-Requisite

Before first run, clear stale Graphiti groups. The existing add-context derived facts create noise. Clear `project_architecture` and `project_decisions` groups. Keep `product_knowledge` and `project_overview` (different purpose, no conflict).

## Acceptance Criteria

- [ ] `run_system_plan()` function body is not a stub (contains actual orchestration logic, >50 meaningful lines)
- [ ] `guardkit system-plan "GuardKit" --context docs/architecture/guardkit-system-spec.md` completes without error
- [ ] Graphiti `project_architecture` group contains structured entities after run (verifiable via `guardkit graphiti search "component"`)
- [ ] Graphiti `project_decisions` group contains ADR entities after run
- [ ] `run_system_plan()` calls `detect_mode()` when no `--mode` override provided
- [ ] `run_system_plan()` calls `SystemPlanGraphiti.upsert_component()` for each parsed component
- [ ] `run_system_plan()` calls `SystemPlanGraphiti.upsert_adr()` for each parsed ADR
- [ ] `run_system_plan()` calls `SystemPlanGraphiti.upsert_system_context()` for system context
- [ ] `run_system_plan()` calls `SystemPlanGraphiti.upsert_crosscutting()` for each concern
- [ ] Architecture markdown artefacts generated via `ArchitectureWriter`
- [ ] Console output reports: number of entities persisted per type, files written
- [ ] Graceful degradation when Graphiti unavailable (markdown-only mode, warning displayed)
- [ ] Unit tests exist with >80% coverage of `run_system_plan()` logic
- [ ] Unit tests mock Graphiti calls and verify correct entity counts passed to upsert methods

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

## Implementation Notes

- Follow the pattern in `guardkit/cli/review.py` for async wrapping at CLI boundary
- The spec parser should be defensive — missing sections should produce warnings, not errors
- Entity IDs should follow the hash-based ID pattern per `.claude/rules/hash-based-ids.md`
- The `to_episode_body()` method on each entity dataclass returns the JSON for Graphiti — use it
- Check existing `spec_parser.py` first — it may already have infrastructure to build on
