---
id: TASK-DM-004
title: Generate prohibition checklist from design data
status: in_review
created: 2026-02-07 10:00:00+00:00
updated: 2026-02-07 10:00:00+00:00
priority: high
task_type: feature
parent_review: TASK-REV-D3E0
feature_id: FEAT-D4CE
wave: 2
implementation_mode: task-work
complexity: 5
dependencies:
- TASK-DM-002
tags:
- design-mode
- prohibition-checklist
- constraints
- scope-creep
test_results:
  status: pending
  coverage: null
  last_run: null
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-D4CE
  base_branch: main
  started_at: '2026-02-08T07:51:44.524698'
  last_updated: '2026-02-08T08:05:06.641582'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-08T07:51:44.524698'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Generate Prohibition Checklist from Design Data

## Description

Implement the 12-category prohibition checklist that analyses extracted design data and documents what IS and IS NOT in the design. This checklist is the primary scope creep prevention mechanism — everything not explicitly shown in the design is prohibited by default.

## Requirements

1. Create `guardkit/orchestrator/prohibition_checklist.py`:
   ```python
   class ProhibitionChecker:
       def generate_checklist(self, design_elements: List[Dict]) -> ProhibitionChecklist
       def validate_compliance(self, generated_files: List[str], checklist: ProhibitionChecklist) -> List[Violation]
   ```

2. Implement 12-category analysis:

   | # | Category | Default | Override Condition |
   |---|----------|---------|-------------------|
   | 1 | Loading states | Prohibited | Only if shown in design |
   | 2 | Error states | Prohibited | Only if shown in design |
   | 3 | Additional form validation | Prohibited | Only if shown in design |
   | 4 | Complex state management | Prohibited | Only if shown in design |
   | 5 | API integrations | **ALWAYS prohibited** | Never |
   | 6 | Navigation beyond design | Prohibited | Only if shown in design |
   | 7 | Additional buttons/controls | Prohibited | Only if shown in design |
   | 8 | Sample data beyond design | **ALWAYS prohibited** | Never |
   | 9 | Responsive breakpoints | Prohibited | Only if shown in design |
   | 10 | Animations not specified | Prohibited | Only if shown in design |
   | 11 | Best practice additions | **ALWAYS prohibited** | Never |
   | 12 | Extra props for flexibility | **ALWAYS prohibited** | Never |

3. Categories 5, 8, 11, 12 are **unconditionally prohibited** — no override possible.

4. Categories 1-4, 6-7, 9-10 are prohibited by default but can be overridden if the design explicitly shows them (detected from extracted elements).

5. `validate_compliance()` checks generated code against the checklist:
   - Tier 1: Pattern matching (fast regex scan for prohibited patterns)
   - Tier 2: AST analysis (only if Tier 1 detects possible violations)

6. Output: structured checklist with per-category decision and reasoning.

## Acceptance Criteria

- [ ] 12-category checklist generated from design elements
- [ ] Categories 5, 8, 11, 12 always prohibited regardless of design content
- [ ] Override detection for categories 1-4, 6-7, 9-10 based on design elements
- [ ] `validate_compliance()` detects violations via pattern matching
- [ ] Tier 2 AST analysis activates only when Tier 1 finds possible violations
- [ ] Zero false negatives for unconditionally prohibited categories
- [ ] Checklist serialisable for inclusion in agent context
- [ ] Unit tests for all 12 categories including override scenarios

## Technical Notes

- See FEAT-DESIGN-MODE-spec.md §3 (Prohibition Checklist)
- Checklist is passed to both Player (as constraints) and Coach (for validation)
- ~500 tokens when serialised for agent context
