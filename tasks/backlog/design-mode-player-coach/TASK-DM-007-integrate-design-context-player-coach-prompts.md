---
id: TASK-DM-007
title: Integrate design context into Player-Coach prompts
status: in_review
created: 2026-02-07 10:00:00+00:00
updated: 2026-02-07 10:00:00+00:00
priority: high
task_type: feature
parent_review: TASK-REV-D3E0
feature_id: FEAT-D4CE
wave: 4
implementation_mode: task-work
complexity: 6
dependencies:
- TASK-DM-003
- TASK-DM-004
- TASK-DM-005
- TASK-DM-006
tags:
- design-mode
- player
- coach
- prompt-engineering
- integration
test_results:
  status: pending
  coverage: null
  last_run: null
autobuild_state:
  current_turn: 1
  max_turns: 25
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-D4CE
  base_branch: main
  started_at: '2026-02-08T12:12:45.115024'
  last_updated: '2026-02-08T12:26:25.896118'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-08T12:12:45.115024'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Integrate Design Context into Player-Coach Prompts

## Description

Wire the design context (from Phase 0) into the Player and Coach agent prompts via `agent_invoker.py`. The Player receives design elements, tokens, and constraints. The Coach receives visual verification instructions and the prohibition checklist for compliance checking.

## Requirements

1. Extend `_build_player_prompt()` in `agent_invoker.py`:
   - Inject design context section when `DesignContext` is available
   - Include: extracted elements, design tokens, prohibition checklist
   - Player delegates to stack-specific UI specialist (React → react-component-generator, MAUI → maui-ux-specialist)
   - Player applies exact design tokens (no approximation)
   - Player never calls MCP tools directly

2. Extend `_build_coach_prompt()` in `agent_invoker.py`:
   - Add visual verification instructions when design context present
   - Coach renders component via BrowserVerifier, captures screenshot
   - Coach runs SSIM comparison via VisualComparator
   - Coach checks prohibition checklist compliance
   - Coach reports: visual fidelity score, comparison method, constraint violations

3. Design context injection pattern:
   ```python
   # In _build_player_prompt()
   if design_context:
       context_section += f"""
   ## Design Context

   **Source**: {design_context.source}

   ### Elements in Design
   {design_context.summary}

   ### Design Tokens
   {format_tokens(design_context.tokens)}

   ### Design Boundaries (Prohibition Checklist)
   {format_checklist(design_context.constraints)}

   ### Instructions
   - Generate components matching the design EXACTLY
   - Apply design tokens with no approximation
   - Do NOT add anything not shown in the design
   - Delegate to the appropriate UI specialist
   """
   ```

4. Coach visual verification additions:
   ```python
   # In _build_coach_prompt()
   if design_context:
       verification_section += """
   ## Visual Verification (Design Mode)

   In addition to standard code review:
   1. Render the generated component in a browser
   2. Capture a screenshot
   3. Compare against design reference using SSIM
   4. Check prohibition checklist compliance
   5. Report: visual fidelity score + any constraint violations

   Quality Gates:
   - Visual fidelity: >= 95% SSIM match
   - Constraint violations: Zero tolerance
   - Design tokens: 100% applied (exact match)
   """
   ```

5. Non-design tasks must receive identical prompts to today (no regression).

6. Extend `TurnRecord` with optional design verification fields:
   ```python
   visual_verification: Optional[Dict[str, Any]] = None
   design_compliance: Optional[Dict[str, Any]] = None
   ```

## Acceptance Criteria

- [ ] Player prompt includes design context when DesignContext available
- [ ] Player prompt includes prohibition checklist as constraints
- [ ] Coach prompt includes visual verification instructions when design task
- [ ] Coach performs SSIM comparison and reports fidelity score
- [ ] Coach checks prohibition checklist compliance
- [ ] TurnRecord extended with visual_verification and design_compliance fields
- [ ] Non-design task prompts unchanged (backward compatible)
- [ ] Design context adds ~2,700 tokens per turn (within budget)
- [ ] Integration tests with mocked Player/Coach responses

## Technical Notes

- See FEAT-DESIGN-MODE-spec.md §5 (Player) and §6 (Coach)
- Player has write access; Coach is read-only — visual verification fits Coach's role
- Design context is STATIC across turns (extracted once in Phase 0)
- Only visual verification result changes per turn
- Context budget: ~2K design context + ~500 checklist + ~200 verification = ~2,700 tokens
