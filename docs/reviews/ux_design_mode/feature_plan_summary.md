 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  FEATURE PLANNING COMPLETE
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Feature: FEAT-D4CE — Design mode for Player-Coach loops
  Review: TASK-REV-D3E0 (completed)

  Created: tasks/backlog/design-mode-player-coach/
    ├── README.md
    ├── IMPLEMENTATION-GUIDE.md
    ├── TASK-DM-001-extend-task-frontmatter-design-urls.md
    ├── TASK-DM-002-implement-mcp-facade-design-extraction.md
    ├── TASK-DM-003-implement-phase-0-design-extraction-autobuild.md
    ├── TASK-DM-004-generate-prohibition-checklist.md
    ├── TASK-DM-005-implement-browser-verifier-abstraction.md
    ├── TASK-DM-006-implement-ssim-comparison-pipeline.md
    ├── TASK-DM-007-integrate-design-context-player-coach-prompts.md
    └── TASK-DM-008-add-design-change-detection.md

  Feature file: .guardkit/features/FEAT-D4CE.yaml

  Execution Strategy (5 waves):
    Wave 1: TASK-DM-001 + TASK-DM-002 (parallel — foundation)
    Wave 2: TASK-DM-003 + TASK-DM-004 (parallel — core pipeline)
    Wave 3: TASK-DM-005 + TASK-DM-008 (parallel — browser verifier + change detection)
    Wave 4: TASK-DM-006 (SSIM pipeline)
    Wave 5: TASK-DM-007 (final integration — wires everything together)

  Context A decisions: Focus=all, Trade-off=quality, Concerns=Player-Coach integration + tokens
  Context B decisions: Approach=phased, Execution=auto-detect, Testing=standard

  Next steps:
    1. Review: tasks/backlog/design-mode-player-coach/IMPLEMENTATION-GUIDE.md
    2. Start Wave 1: /feature-build FEAT-D4CE
    3. Or individual tasks: /task-work TASK-DM-001
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
