richardwoollcott@Mac feature-test % GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-4C22 --max-turns 15

INFO:guardkit.cli.autobuild:Starting feature orchestration: FEAT-4C22 (max_turns=15, stop_on_failure=True, resume=False, fresh=False, sdk_timeout=None, enable_pre_loop=None)
INFO:guardkit.orchestrator.feature_orchestrator:FeatureOrchestrator initialized: repo=/Users/richardwoollcott/Projects/guardkit_testing/feature-test, max_turns=15, stop_on_failure=True, resume=False, fresh=False, enable_pre_loop=None
INFO:guardkit.orchestrator.feature_orchestrator:Starting feature orchestration for FEAT-4C22
INFO:guardkit.orchestrator.feature_orchestrator:Phase 1 (Setup): Loading feature FEAT-4C22
╭───────────────────────────── GuardKit AutoBuild ─────────────────────────────╮
│ AutoBuild Feature Orchestration                                              │
│                                                                              │
│ Feature: FEAT-4C22                                                           │
│ Max Turns: 15                                                                │
│ Stop on Failure: True                                                        │
│ Mode: Starting                                                               │
╰──────────────────────────────────────────────────────────────────────────────╯
INFO:guardkit.orchestrator.feature_loader:Loading feature from /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/features/FEAT-4C22.yaml
✓ Loaded feature: Structured JSON Logging
  Tasks: 6
  Waves: 5
Feature validation failed:
Feature validation failed for FEAT-4C22:
  - Task TASK-LOG-003 has unknown dependency: TASK-DOC-001
ERROR:guardkit.cli.autobuild:Feature validation failed: Feature validation failed for FEAT-4C22:
  - Task TASK-LOG-003 has unknown dependency: TASK-DOC-001
richardwoollcott@Mac feature-test %
