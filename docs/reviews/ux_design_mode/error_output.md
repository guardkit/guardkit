richardwoollcott@Mac guardkit % GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-D4CE --max-turns 15
INFO:guardkit.cli.autobuild:Starting feature orchestration: FEAT-D4CE (max_turns=15, stop_on_failure=True, resume=False, fresh=False, sdk_timeout=None, enable_pre_loop=None)
INFO:guardkit.orchestrator.feature_orchestrator:FeatureOrchestrator initialized: repo=/Users/richardwoollcott/Projects/appmilla_github/guardkit, max_turns=15, stop_on_failure=True, resume=False, fresh=False, enable_pre_loop=None
INFO:guardkit.orchestrator.feature_orchestrator:Starting feature orchestration for FEAT-D4CE
INFO:guardkit.orchestrator.feature_orchestrator:Phase 1 (Setup): Loading feature FEAT-D4CE
╭──────────────────────────────────────────────────────────────── GuardKit AutoBuild ─────────────────────────────────────────────────────────────────╮
│ AutoBuild Feature Orchestration                                                                                                                     │
│                                                                                                                                                     │
│ Feature: FEAT-D4CE                                                                                                                                  │
│ Max Turns: 15                                                                                                                                       │
│ Stop on Failure: True                                                                                                                               │
│ Mode: Starting                                                                                                                                      │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
INFO:guardkit.orchestrator.feature_loader:Loading feature from /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/features/FEAT-D4CE.yaml
✓ Loaded feature: Design mode for Player-Coach loops
  Tasks: 8
  Waves: 5
Feature validation failed:
Feature validation failed for FEAT-D4CE:
  - Task file not found: TASK-DM-001 at
tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-001-extend-task-frontmatter-for-design-urls.md
  - Task file not found: TASK-DM-002 at
tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-002-implement-mcp-facade-for-design-extraction.md
  - Task file not found: TASK-DM-003 at
tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-003-implement-phase-0-design-extraction-in-autobuild.md
  - Task file not found: TASK-DM-004 at
tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-004-generate-prohibition-checklist-from-design-data.md
  - Task file not found: TASK-DM-005 at
tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-005-implement-browserverifier-abstraction.md
  - Task file not found: TASK-DM-006 at
tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-006-implement-ssim-comparison-pipeline.md
  - Task file not found: TASK-DM-007 at
tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-007-integrate-design-context-into-player-coach-prompts.md
  - Task file not found: TASK-DM-008 at
tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-008-add-design-change-detection-and-state-aware-handling.md
ERROR:guardkit.cli.autobuild:Feature validation failed: Feature validation failed for FEAT-D4CE:
  - Task file not found: TASK-DM-001 at tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-001-extend-task-frontmatter-for-design-urls.md
  - Task file not found: TASK-DM-002 at tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-002-implement-mcp-facade-for-design-extraction.md
  - Task file not found: TASK-DM-003 at tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-003-implement-phase-0-design-extraction-in-autobuild.md
  - Task file not found: TASK-DM-004 at tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-004-generate-prohibition-checklist-from-design-data.md
  - Task file not found: TASK-DM-005 at tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-005-implement-browserverifier-abstraction.md
  - Task file not found: TASK-DM-006 at tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-006-implement-ssim-comparison-pipeline.md
  - Task file not found: TASK-DM-007 at tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-007-integrate-design-context-into-player-coach-prompts.md
  - Task file not found: TASK-DM-008 at tasks/backlog/design-mode-player-coach/design-mode-player-coach/TASK-DM-008-add-design-change-detection-and-state-aware-handling.md
richardwoollcott@Mac guardkit %