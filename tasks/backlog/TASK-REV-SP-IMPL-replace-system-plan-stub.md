# Review: Replace system_plan.py Stub with Working Orchestrator

## Review Scope

FEAT-SP-001 (`/system-plan` command) has all supporting infrastructure built and working — entity definitions, `graphiti_arch.py` persistence layer (358 lines with `upsert_component()`, `upsert_adr()`, `upsert_system_context()`, `upsert_crosscutting()`), architecture writer, mode detector, question adapter, CLI registration, and full command spec. The **sole gap** is `guardkit/planning/system_plan.py` which is a 70-line stub where `run_system_plan()` does `pass`.

This stub was created by TASK-SP-006 (currently sitting in `in_review/` with 0/15 acceptance criteria checked — see TASK-REV-STUB findings). TASK-FIX-STUB-A and TASK-FIX-STUB-B have since been implemented to prevent this recurring.

## What Needs to Happen

Replace the stub `run_system_plan()` with working orchestration that:

1. **Calls `detect_mode()`** from `guardkit/planning/mode_detector.py` (already built) to determine setup/refine/review
2. **Loads `--context` file** when provided (e.g., `docs/architecture/guardkit-system-spec.md`)
3. **Parses context into entities** — create `SystemContextDef`, `ComponentDef`, `CrosscuttingConcernDef`, `ArchitectureDecision` instances from the structured markdown
4. **Calls `SystemPlanGraphiti.upsert_*()`** methods from `graphiti_arch.py` (already built) for each entity
5. **Calls `ArchitectureWriter`** from `guardkit/planning/architecture_writer.py` (already built) to generate markdown artefacts
6. **Handles `--no-questions`** and `--defaults` flags
7. **Reports results** showing what was persisted to Graphiti and what files were written

## Key Constraint

The existing command spec (`.claude/commands/system-plan.md`) defines a full interactive question flow for setup mode. However, the `--context` path (providing a pre-written spec file) is the immediate priority — this is how architecture gets into Graphiti without manually answering 30+ questions.

**Minimum viable implementation**: Support `--context docs/architecture/guardkit-system-spec.md` which parses the structured spec and upserts all entities. Interactive question flow can remain a follow-up.

## Files to Review/Modify

- `guardkit/planning/system_plan.py` — **Replace stub** with working orchestration
- `guardkit/cli/system_plan.py` — Verify CLI wiring passes all args correctly
- `tests/unit/planning/test_system_plan.py` — Must have tests (zero-test anomaly applies)

## Files That Already Work (DO NOT recreate)

- `guardkit/planning/graphiti_arch.py` — 358 lines, fully implemented persistence layer
- `guardkit/planning/mode_detector.py` — Mode detection with graceful degradation
- `guardkit/planning/architecture_writer.py` — Markdown artefact generation
- `guardkit/knowledge/entities/*.py` — All entity dataclasses built
- `.claude/commands/system-plan.md` — Full command spec (400+ lines)

## Existing Architecture Spec Ready for Ingestion

`docs/architecture/guardkit-system-spec.md` contains the complete GuardKit architecture with:
- 1 system context (name, purpose, methodology, actors, external systems)
- 9 components (COMP-cli-layer through COMP-template-system)
- 7 cross-cutting concerns (XC-error-handling through XC-httpx-cleanup)
- 8 ADRs (ADR-SP-001 through ADR-SP-008)
- Quality gate pipeline phases
- 6 failure patterns

## Success Criteria

- `guardkit system-plan "GuardKit" --context docs/architecture/guardkit-system-spec.md` completes without error
- Graphiti contains properly structured entities (verifiable via `guardkit graphiti search "architecture"`)
- `/system-overview` returns rich structured output (not "no context available")
- Tests exist and pass for `run_system_plan()` orchestration logic
- TASK-SP-006 acceptance criteria are actually checked off

## Pre-Requisite

Clear `project_architecture` and `project_decisions` groups before running, as existing `add-context` derived facts will create noise. The `guardkit graphiti` CLI can be used or `SystemPlanGraphiti` has the group IDs.

## Complexity

Score: 6 (substantial orchestration but all building blocks exist — this is primarily wiring + parsing)

## Related

- FEAT-SP-001 feature spec: `/mnt/project/FEAT-SP-001-system-plan-command.md`
- TASK-REV-STUB review report: `tasks/backlog/stub-quality-gates/` (implemented)
- Architecture spec: `docs/architecture/guardkit-system-spec.md`
- Gap analysis: Previous session's `graphiti-knowledge-gap-analysis.md`
