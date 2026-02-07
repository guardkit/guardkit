# Implementation Guide: Design Mode for Player-Coach Loops

## Feature Overview

Add design mode to GuardKit's Player-Coach adversarial loops. When a task includes a design URL (Figma or Zeplin), the system extracts design intent via MCP, generates components via the Player agent, and validates visual fidelity via the Coach agent using browser-based verification.

**Parent Review**: TASK-REV-D3E0
**Feature ID**: FEAT-DM
**Approach**: Phased delivery (Option 3) — full design mode delivered incrementally
**Testing**: Standard (quality gates enforced)

## Architecture Summary

Design mode is an **enriched context** passed through the existing loop, not a parallel architecture:

```
Standard Task:
  PreLoop → [Player(requirements) ↔ Coach(code review)] → Finalize

Design Task:
  Phase 0 (NEW) → PreLoop → [Player(requirements + design context) ↔ Coach(code review + visual verification)] → Finalize
```

Key principle: **The orchestrator handles all MCP calls. Player and Coach never call MCP directly.**

## Wave Execution Plan

### Wave 1: Foundation (2 tasks, parallel execution)

No dependencies — both tasks can execute simultaneously.

| Task | Title | Complexity | Mode |
|------|-------|-----------|------|
| TASK-DM-001 | Extend task frontmatter for design URLs | 3 | task-work |
| TASK-DM-002 | Implement MCP facade for design extraction | 6 | task-work |

**Value delivered**: Design tasks can be created with URLs; MCP extraction layer is ready.

### Wave 2: Core Pipeline (2 tasks, parallel execution)

Depends on Wave 1 completion. Both Wave 2 tasks can execute in parallel.

| Task | Title | Complexity | Dependencies |
|------|-------|-----------|-------------|
| TASK-DM-003 | Implement Phase 0 design extraction in autobuild | 7 | DM-001, DM-002 |
| TASK-DM-004 | Generate prohibition checklist from design data | 5 | DM-002 |

**Value delivered**: Design data is extracted before the Player-Coach loop; scope creep prevention via prohibition checklist.

### Wave 3: Visual Verification (2 tasks, sequential)

Depends on Wave 2 completion. DM-006 depends on DM-005.

| Task | Title | Complexity | Dependencies |
|------|-------|-----------|-------------|
| TASK-DM-005 | Implement BrowserVerifier abstraction | 6 | DM-003 |
| TASK-DM-006 | Implement SSIM comparison pipeline | 5 | DM-005 |

**Value delivered**: Browser-based visual verification with deterministic SSIM scoring.

### Wave 4: Integration & Change Detection (2 tasks, parallel execution)

Depends on Wave 3 completion. Both tasks can execute in parallel.

| Task | Title | Complexity | Dependencies |
|------|-------|-----------|-------------|
| TASK-DM-007 | Integrate design context into Player-Coach prompts | 6 | DM-003, DM-004, DM-005, DM-006 |
| TASK-DM-008 | Add design change detection and state-aware handling | 5 | DM-003 |

**Value delivered**: Complete end-to-end design mode with change detection.

## Dependency Graph

```
TASK-DM-001 ──┐
              ├──→ TASK-DM-003 ──→ TASK-DM-005 ──→ TASK-DM-006 ──┐
TASK-DM-002 ──┤                                                     ├──→ TASK-DM-007
              └──→ TASK-DM-004 ────────────────────────────────────┘

              TASK-DM-003 ──────────────────────────────────────────→ TASK-DM-008
```

## Key Architecture Decisions

1. **MCP Facade**: Orchestrator owns all MCP calls — agents receive pre-extracted data
2. **BrowserVerifier Abstraction**: agent-browser (primary, 5.7x efficient) + Playwright (MAUI fallback)
3. **SSIM Pipeline**: Deterministic Tier 1 (zero tokens) + AI vision Tier 2 (borderline cases)
4. **Prohibition Checklist**: 12 categories, 4 unconditionally prohibited (5, 8, 11, 12)
5. **Change Detection**: Hash-based, state-aware (no webhook infrastructure)

## Files to Create/Modify

### New Files
- `guardkit/orchestrator/mcp_design_extractor.py` — MCP facade
- `guardkit/orchestrator/prohibition_checklist.py` — Constraint validation
- `guardkit/orchestrator/browser_verifier.py` — Browser abstraction
- `guardkit/orchestrator/visual_comparator.py` — SSIM pipeline

### Modified Files
- `guardkit/orchestrator/autobuild.py` — Phase 0, exit status extension
- `guardkit/orchestrator/agent_invoker.py` — Player/Coach prompt enrichment
- `guardkit/orchestrator/progress.py` — FinalStatus extension
- Task frontmatter schema (task-create command)

## Quality Gates

| Gate | Threshold | Applies To |
|------|-----------|-----------|
| Visual fidelity | >= 95% SSIM | Design tasks only |
| Constraint violations | Zero | Design tasks only |
| Design tokens applied | 100% | Design tasks only |
| Compilation | 100% | All tasks |
| Tests pass | 100% | All tasks |

## Reference Documents

- [FEAT-DESIGN-MODE-spec.md](../../../docs/features/FEAT-DESIGN-MODE-spec.md) — Full specification
- [FEAT-DESIGN-MODE-open-questions-analysis.md](../../../docs/features/FEAT-DESIGN-MODE-open-questions-analysis.md) — Research decisions
- [figma-react-orchestrator.md](../design-url-integration/figma-react-orchestrator.md) — Figma MCP patterns (prior art)
- [zeplin-maui-orchestrator.md](../design-url-integration/zeplin-maui-orchestrator.md) — Zeplin MCP patterns (prior art)
