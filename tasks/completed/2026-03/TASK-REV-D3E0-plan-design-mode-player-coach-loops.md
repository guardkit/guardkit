---
id: TASK-REV-D3E0
title: "Plan: Design mode for Player-Coach loops"
status: completed
created: 2026-02-07T10:00:00Z
updated: 2026-02-07T10:00:00Z
priority: high
task_type: review
tags: [design-mode, player-coach, figma, zeplin, mcp, visual-verification]
complexity: 8
decision_required: true
context_files:
  - docs/features/FEAT-DESIGN-MODE-spec.md
  - docs/features/FEAT-DESIGN-MODE-open-questions-analysis.md
clarification:
  context_a:
    timestamp: 2026-02-07T10:00:00Z
    decisions:
      focus: all
      tradeoff: quality
      concerns: "Player-Coach integration (primary), Token budget risk (secondary)"
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Plan: Design mode for Player-Coach loops

## Description

Review and plan the implementation of design mode for GuardKit's Player-Coach adversarial loops. When a task includes a design URL (Figma or Zeplin), the system should extract design intent via MCP, generate components via the Player agent, and validate visual fidelity via the Coach agent using browser-based verification.

## Feature Specification

See: `docs/features/FEAT-DESIGN-MODE-spec.md`

## Key Areas for Analysis

### Player-Coach Integration (Primary Concern)
- How design mode fits into the existing adversarial loop without breaking non-design tasks
- Design extraction as a pre-loop phase (Phase 0)
- Passing design context to Player and Coach without MCP coupling
- Prohibition checklist as a constraint mechanism for scope creep prevention

### Token Budget Risk (Secondary Concern)
- MCP responses can be enormous (351K tokens observed vs 25K context limit)
- Caching strategy for MCP responses during Player-Coach iterations
- Summarisation of extracted design data before passing to agents

### Technical Architecture
- MCP facade pattern (orchestrator handles MCP; Player/Coach never call MCP directly)
- BrowserVerifier abstraction (agent-browser for web, Playwright+Appium for MAUI)
- SSIM tiered comparison pipeline (deterministic Tier 1 + AI escalation Tier 2)
- Design change detection via extraction hash comparison

### Platform Support
- React/TypeScript via Figma MCP
- .NET MAUI via Zeplin MCP
- Stack-specific UI specialist delegation

## Prior Art

- `tasks/backlog/design-url-integration/figma-react-orchestrator.md` - Figma MCP patterns
- `tasks/backlog/design-url-integration/zeplin-maui-orchestrator.md` - Zeplin MCP patterns
- `tasks/backlog/design-url-integration/TASK-UX-7F1E-add-design-url-parameter.md` - Task-create extension
- `tasks/backlog/design-url-integration/TASK-UX-2A61-refactor-figma-react-orchestrator.md` - Delegation pattern

## Acceptance Criteria

- [ ] Technical options analysis covering all architectural components
- [ ] Risk assessment for MCP integration and token budget
- [ ] Effort estimation for implementation phases
- [ ] Recommended approach with justification
- [ ] Implementation breakdown into subtasks with dependency graph
- [ ] Quality gate definitions for design mode

## Review Mode

Decision mode - produce actionable implementation plan with subtask breakdown.
