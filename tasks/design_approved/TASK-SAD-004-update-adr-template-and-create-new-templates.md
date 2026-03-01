---
complexity: 5
dependencies:
- TASK-SAD-002
- TASK-SAD-003
feature_id: FEAT-SAD
id: TASK-SAD-004
implementation_mode: task-work
parent_review: TASK-REV-AEE1
status: design_approved
task_type: feature
title: Update ADR template and create container, component-l3, api-contract, DDR templates
wave: 2
---

# Task: Update ADR template and create container, component-l3, api-contract, DDR templates

## Description

Update the existing `adr.md.j2` template to include an "Alternatives Considered" section, and create four new Jinja2 templates for C4 diagrams and design artefacts.

## Acceptance Criteria

- [ ] Update `guardkit/templates/adr.md.j2`:
  - Add "Alternatives Considered" section (conditional: only rendered if `alternatives_considered` is non-empty)
  - Backwards compatible with existing ADRs that don't have this field
- [ ] Create `guardkit/templates/container.md.j2`:
  - C4 Level 2 Container diagram using native C4 Mermaid syntax (`C4Container`, `Container`, `ContainerDb`, `System_Ext`, `Rel`)
  - Shows containers (services, datastores, frontends) and their runtime communication
  - Inputs: containers list, external systems, relationships
- [ ] Create `guardkit/templates/component-l3.md.j2`:
  - C4 Level 3 Component diagram using native `C4Component` Mermaid syntax
  - Per-container component breakdown
  - Triggered when container has >3 internal components OR explicitly requested (ASSUM-012)
  - Inputs: container name, components list, internal relationships
- [ ] Create `guardkit/templates/api-contract.md.j2`:
  - Per-bounded-context API contract document
  - Sections: consumer types, endpoints table, request/response schemas, authentication, error codes
  - Multi-protocol support (REST, GraphQL, MCP tool definitions, A2A task schemas)
- [ ] Create `guardkit/templates/ddr.md.j2`:
  - Design Decision Record template (parallel to ADR template)
  - Sections: Status, Date, Context, Decision, Rationale, Alternatives Considered, Consequences, Related API Contracts
- [ ] All templates render correctly with sample data
- [ ] Unit tests for template rendering (each template tested with sample context)

## Implementation Notes

- Templates go in `guardkit/templates/`
- Use native C4 Mermaid syntax for diagram templates (not generic `graph TB`)
- Don't modify existing `system-context.md.j2` — keep it working for `/system-plan`
- The `adr.md.j2` update must be conditional to not break existing ADR rendering
- Diagram templates should include `style` directives for colour coding per C4 conventions