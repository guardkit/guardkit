# FEAT-AC1A: Seam-First Testing Strategy

## Source

- Analysis: [testing-strategy-seam-first-analysis.md](../../../docs/research/testing-strategy/testing-strategy-seam-first-analysis.md)
- Architecture review: `/system-plan --mode=review` — Accepted, no conflicts

## Wave Execution Plan

### Wave 1: Foundation (parallel)

| Task | Type | Complexity | Description |
|------|------|------------|-------------|
| TASK-SFT-001 | scaffolding | 2 | Create `tests/seam/` directory, conftest, markers |
| TASK-SFT-002 | documentation | 2 | Write ADR-SP-009 (Honeycomb Testing Model) |

### Wave 2: Seam Tests (parallel, requires Wave 1)

| Task | Type | Complexity | Seam | Description |
|------|------|------------|------|-------------|
| TASK-SFT-003 | testing | 5 | S3 | Orchestrator → module wiring |
| TASK-SFT-004 | testing | 6 | S6 | AutoBuild → Coach wiring |
| TASK-SFT-005 | testing | 4 | S8 | Quality gate → state transitions |
| TASK-SFT-006 | testing | 4 | S2 | CLI → Python entry points |
| TASK-SFT-007 | testing | 5 | S4 | Python → Graphiti persistence |
| TASK-SFT-008 | testing | 4 | S7 | Task-work → results writer |

### Wave 3: Integration & Guidance (parallel, requires Wave 2)

| Task | Type | Complexity | Description |
|------|------|------------|-------------|
| TASK-SFT-009 | feature | 4 | Update QualityGateProfile with seam test field |
| TASK-SFT-010 | documentation | 3 | Trophy-model guidance for client app templates |
| TASK-SFT-011 | refactor | 3 | Migrate existing seam tests to `tests/seam/` |

## Seam Coverage Matrix

| Seam | Boundary | Task | Priority |
|------|----------|------|----------|
| S1 | Slash command → CLI | Not directly testable (Claude Code interpretation) | N/A |
| S2 | CLI (Click) → Python | TASK-SFT-006 | Medium |
| S3 | Orchestrator → Modules | TASK-SFT-003 | High |
| S4 | Python → Graphiti | TASK-SFT-007 | Medium |
| S5 | Graphiti → FalkorDB | Covered by S4 tests at protocol level | Low |
| S6 | AutoBuild → Coach | TASK-SFT-004 | High |
| S7 | Task-work → Results | TASK-SFT-008 | Medium |
| S8 | Quality gates → State | TASK-SFT-005 | High |

## Architecture Impact

- **New ADR**: ADR-SP-009 (Honeycomb Testing Model)
- **New cross-cutting concern**: XC-seam-testing
- **Quality gate update**: `seam_tests_recommended` field (soft gate)
- **Template updates**: Trophy-model guidance for 4 client app templates
- **No conflicts** with existing ADRs (reinforces ADR-SP-003, ADR-SP-007, ADR-SP-006)
