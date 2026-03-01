---
id: TASK-SAD-006
title: "Write /system-arch command specification"
task_type: feature
parent_review: TASK-REV-AEE1
feature_id: FEAT-SAD
wave: 3
implementation_mode: task-work
complexity: 8
dependencies:
  - TASK-SAD-002
  - TASK-SAD-004
---

# Task: Write /system-arch command specification

## Description

Write the complete command specification for `/system-arch` as a markdown file at `installer/core/commands/system-arch.md`. This is the first command in the upstream pipeline and establishes system-level architecture decisions before any feature work begins.

## Acceptance Criteria

- [ ] Command spec follows the pattern established by `system-plan.md` and `feature-plan.md`
- [ ] 6-category interactive question flow with `[C]ontinue / [R]evise / [S]kip / [A]DR?` checkpoints:
  1. Domain & Structural Pattern (with trade-offs surfaced)
  2. Bounded Contexts / Module Structure
  3. Technology & Infrastructure
  4. Multi-Consumer API Strategy (web clients, agents, internal flows)
  5. Cross-Cutting Concerns
  6. Constraints & NFRs
- [ ] Setup mode auto-detection: if no architecture context in Graphiti, enters setup mode
- [ ] Mandatory C4 diagram output with review gates:
  - C4 Level 1 (System Context) using existing `system-context.md.j2`
  - C4 Level 2 (Container) using new `container.md.j2`
  - Both diagrams require explicit user approval before proceeding to output
- [ ] Mandatory output artefacts:
  - Domain model document
  - ADRs (using `ADR-ARCH-NNN` prefix) for each decision made
  - Assumptions manifest (YAML)
  - Architecture summary for `/system-plan` consumption
  - C4 Context and Container diagrams (Mermaid)
- [ ] Graphiti seeding: all artefacts seeded into `project_architecture` and `project_decisions` groups
- [ ] Graceful degradation: if Graphiti unavailable, warn and generate markdown artefacts only
- [ ] Partial session handling: if user skips categories, persist completed categories, inform which were skipped
- [ ] Empty answer handling: use placeholder, warn, continue
- [ ] ADR numbering: scan `docs/architecture/decisions/` for next available number
- [ ] Diagram splitting: warn if >30 nodes, suggest manual split at review gate
- [ ] Security: sanitise ADR rationale text before Graphiti seeding
- [ ] Execution protocol section with step-by-step Claude instructions
- [ ] Error handling section (no description, invalid pattern choice, etc.)

## Implementation Notes

- File: `installer/core/commands/system-arch.md`
- Follow `/system-plan.md` as structural template (question flow, checkpoint pattern, Graphiti pseudo-code)
- The command instructs Claude directly (Pattern A: command-spec-only)
- Output directory: `docs/architecture/` (established convention)
- ADR directory: `docs/architecture/decisions/` (match existing code, override ASSUM-005)
- Reference BDD scenarios from `features/system-arch-design-commands/system-arch-design-commands.feature`
- Must cover all 8 key-example scenarios and relevant boundary/negative cases from the BDD spec
