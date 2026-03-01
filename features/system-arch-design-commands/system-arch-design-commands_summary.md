# Feature Spec Summary: System Architecture & Design Commands

**Stack**: python
**Generated**: 2026-03-01T00:00:00Z
**Scenarios**: 33 total (3 smoke, 0 regression)
**Assumptions**: 12 total (1 high / 5 medium / 6 low confidence)
**Review required**: Yes

## Scope

This specification covers the behaviour of four new GuardKit commands — `/system-arch`, `/system-design`, `/arch-refine`, and `/design-refine` — that sit upstream of `/system-plan` in the command pipeline. These commands establish and evolve system-level architecture and design decisions, seed them into the Graphiti knowledge graph, and produce mandatory C4 diagrams as verification gates. The specification validates the full pipeline from architecture decisions through to grounded feature specifications.

## Scenario Counts by Category

| Category | Count |
|----------|-------|
| Key examples (@key-example) | 8 |
| Boundary conditions (@boundary) | 6 |
| Negative cases (@negative) | 6 |
| Edge cases (@edge-case) | 13 |

## Deferred Items

None — all groups accepted.

## Open Assumptions (low confidence)

The following assumptions need verification against actual implementation constraints:

- **ASSUM-004**: Output directory for /system-design artefacts is `docs/design/`
- **ASSUM-008**: Agent protocol support scope includes MCP, Google A2A, and ACP
- **ASSUM-009**: /arch-refine and /design-refine are two separate commands
- **ASSUM-010**: Graphiti temporal superseding mechanism (query prior node by ID, create "supersedes" relationship)
- **ASSUM-012**: C4 Level 3 trigger threshold (>3 internal components per container)
- **ASSUM-004**: Output directory for /system-design is `docs/design/` (not yet established by convention)

## Integration with /feature-plan

This summary can be passed to `/feature-plan` as a context file:

    /feature-plan "System Architecture & Design Commands" --context features/system-arch-design-commands/system-arch-design-commands_summary.md
