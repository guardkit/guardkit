richardwoollcott@Mac feature-test % GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-F392 --max-turns 15

INFO:guardkit.cli.autobuild:Starting feature orchestration: FEAT-F392 (max_turns=15, stop_on_failure=True, resume=False, fresh=False, sdk_timeout=None, enable_pre_loop=None)
INFO:guardkit.orchestrator.feature_orchestrator:FeatureOrchestrator initialized: repo=/Users/richardwoollcott/Projects/guardkit_testing/feature-test, max_turns=15, stop_on_failure=True, resume=False, fresh=False, enable_pre_loop=None
INFO:guardkit.orchestrator.feature_orchestrator:Starting feature orchestration for FEAT-F392
INFO:guardkit.orchestrator.feature_orchestrator:Phase 1 (Setup): Loading feature FEAT-F392
╭───────────────────────────────────────────────────── GuardKit AutoBuild ──────────────────────────────────────────────────────╮
│ AutoBuild Feature Orchestration                                                                                               │
│                                                                                                                               │
│ Feature: FEAT-F392                                                                                                            │
│ Max Turns: 15                                                                                                                 │
│ Stop on Failure: True                                                                                                         │
│ Mode: Starting                                                                                                                │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
INFO:guardkit.orchestrator.feature_loader:Loading feature from /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/features/FEAT-F392.yaml
✓ Loaded feature: Comprehensive API Documentation
  Tasks: 6
  Waves: 3
✓ Feature validation passed
INFO:guardkit.cli.display:WaveProgressDisplay initialized: waves=3, verbose=False
✓ Created shared worktree: /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392
INFO:guardkit.orchestrator.feature_orchestrator:Copied task file to worktree: TASK-DOC-001-create-config-metadata.md
INFO:guardkit.orchestrator.feature_orchestrator:Copied task file to worktree: TASK-DOC-002-create-descriptions-module.md
INFO:guardkit.orchestrator.feature_orchestrator:Copied task file to worktree: TASK-DOC-003-update-main-openapi-config.md
INFO:guardkit.orchestrator.feature_orchestrator:Copied task file to worktree: TASK-DOC-004-create-version-middleware.md
INFO:guardkit.orchestrator.feature_orchestrator:Copied task file to worktree: TASK-DOC-005-add-response-examples.md
INFO:guardkit.orchestrator.feature_orchestrator:Copied task file to worktree: TASK-DOC-006-add-documentation-tests.md
✓ Copied 6 task file(s) to worktree
INFO:guardkit.orchestrator.feature_orchestrator:Phase 2 (Waves): Executing 3 waves

Starting Wave Execution

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Wave 1/3: TASK-DOC-001, TASK-DOC-002, TASK-DOC-005 (parallel: 3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INFO:guardkit.cli.display:Started wave 1: ['TASK-DOC-001', 'TASK-DOC-002', 'TASK-DOC-005']
  ▶ TASK-DOC-001: Executing: Create core/config.py with API metadata
  ▶ TASK-DOC-002: Executing: Create docs/descriptions.py
  ▶ TASK-DOC-005: Executing: Add response examples to schemas
INFO:guardkit.orchestrator.feature_orchestrator:Task TASK-DOC-001: Pre-loop skipped (enable_pre_loop=False)
INFO:guardkit.orchestrator.feature_orchestrator:Task TASK-DOC-002: Pre-loop skipped (enable_pre_loop=False)
INFO:guardkit.orchestrator.feature_orchestrator:Task TASK-DOC-005: Pre-loop skipped (enable_pre_loop=False)
INFO:guardkit.orchestrator.progress:ProgressDisplay initialized with max_turns=15
INFO:guardkit.orchestrator.autobuild:AutoBuildOrchestrator initialized: repo=/Users/richardwoollcott/Projects/guardkit_testing/feature-test, max_turns=15, resume=False, enable_pre_loop=False, development_mode=tdd, sdk_timeout=900s, skip_arch_review=False, enable_perspective_reset=True, reset_turns=[3, 5], enable_checkpoints=True, rollback_on_pollution=True, ablation_mode=False, existing_worktree=provided
INFO:guardkit.orchestrator.autobuild:Starting orchestration for TASK-DOC-001 (resume=False)
INFO:guardkit.orchestrator.progress:ProgressDisplay initialized with max_turns=15
INFO:guardkit.orchestrator.autobuild:AutoBuildOrchestrator initialized: repo=/Users/richardwoollcott/Projects/guardkit_testing/feature-test, max_turns=15, resume=False, enable_pre_loop=False, development_mode=tdd, sdk_timeout=900s, skip_arch_review=False, enable_perspective_reset=True, reset_turns=[3, 5], enable_checkpoints=True, rollback_on_pollution=True, ablation_mode=False, existing_worktree=provided
INFO:guardkit.orchestrator.autobuild:Starting orchestration for TASK-DOC-005 (resume=False)
INFO:guardkit.orchestrator.progress:ProgressDisplay initialized with max_turns=15
INFO:guardkit.orchestrator.autobuild:AutoBuildOrchestrator initialized: repo=/Users/richardwoollcott/Projects/guardkit_testing/feature-test, max_turns=15, resume=False, enable_pre_loop=False, development_mode=tdd, sdk_timeout=900s, skip_arch_review=False, enable_perspective_reset=True, reset_turns=[3, 5], enable_checkpoints=True, rollback_on_pollution=True, ablation_mode=False, existing_worktree=provided
INFO:guardkit.orchestrator.autobuild:Starting orchestration for TASK-DOC-002 (resume=False)
INFO:guardkit.orchestrator.autobuild:Phase 1 (Setup): Creating worktree for TASK-DOC-005
INFO:guardkit.orchestrator.autobuild:Using existing worktree for TASK-DOC-005: /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392
INFO:guardkit.orchestrator.autobuild:Phase 1 (Setup): Creating worktree for TASK-DOC-001
INFO:guardkit.orchestrator.autobuild:Using existing worktree for TASK-DOC-001: /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392
INFO:guardkit.orchestrator.autobuild:Phase 1 (Setup): Creating worktree for TASK-DOC-002
INFO:guardkit.orchestrator.autobuild:Using existing worktree for TASK-DOC-002: /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392
INFO:guardkit.orchestrator.autobuild:Phase 2 (Loop): Starting adversarial turns for TASK-DOC-005 from turn 1
INFO:guardkit.orchestrator.autobuild:Phase 2 (Loop): Starting adversarial turns for TASK-DOC-001 from turn 1
INFO:guardkit.orchestrator.autobuild:Checkpoint manager initialized for TASK-DOC-005 (rollback_on_pollution=True)
INFO:guardkit.orchestrator.autobuild:Executing turn 1/15
INFO:guardkit.orchestrator.autobuild:Checkpoint manager initialized for TASK-DOC-001 (rollback_on_pollution=True)
INFO:guardkit.orchestrator.autobuild:Executing turn 1/15
INFO:guardkit.orchestrator.autobuild:Phase 2 (Loop): Starting adversarial turns for TASK-DOC-002 from turn 1
INFO:guardkit.orchestrator.autobuild:Checkpoint manager initialized for TASK-DOC-002 (rollback_on_pollution=True)
INFO:guardkit.orchestrator.autobuild:Executing turn 1/15
⠋ Turn 1/15: Player Implementation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   0%INFO:guardkit.orchestrator.progress:Started turn 1: Player Implementation
⠋ Turn 1/15: Player Implementation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   0%INFO:guardkit.orchestrator.progress:Started turn 1: Player Implementation
⠋ Turn 1/15: Player Implementation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   0%INFO:guardkit.orchestrator.progress:Started turn 1: Player Implementation
INFO:guardkit.orchestrator.agent_invoker:Routing to direct Player path for TASK-DOC-001 (implementation_mode=direct)
INFO:guardkit.orchestrator.agent_invoker:Invoking Player via direct SDK for TASK-DOC-001 (turn 1)
INFO:guardkit.orchestrator.agent_invoker:Routing to direct Player path for TASK-DOC-002 (implementation_mode=direct)
INFO:guardkit.orchestrator.agent_invoker:Invoking Player via direct SDK for TASK-DOC-002 (turn 1)
INFO:guardkit.orchestrator.agent_invoker:Routing to direct Player path for TASK-DOC-005 (implementation_mode=direct)
INFO:guardkit.orchestrator.agent_invoker:Invoking Player via direct SDK for TASK-DOC-005 (turn 1)
INFO:claude_agent_sdk._internal.transport.subprocess_cli:Using bundled Claude Code CLI: /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
INFO:claude_agent_sdk._internal.transport.subprocess_cli:Using bundled Claude Code CLI: /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
INFO:claude_agent_sdk._internal.transport.subprocess_cli:Using bundled Claude Code CLI: /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/claude_agent_sdk/_bundled/claude
⠼ Turn 1/15: Player Implementation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   0%INFO:guardkit.orchestrator.agent_invoker:[TASK-DOC-005] Player invocation in progress... (30s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-DOC-002] Player invocation in progress... (30s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-DOC-001] Player invocation in progress... (30s elapsed)
⠴ Turn 1/15: Player Implementation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   0%INFO:guardkit.orchestrator.agent_invoker:Wrote direct mode results to /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392/.guardkit/autobuild/TASK-DOC-001/task_work_results.json
INFO:guardkit.orchestrator.agent_invoker:Wrote direct mode player report to /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392/.guardkit/autobuild/TASK-DOC-001/player_turn_1.json
  ⚠ Player report missing - attempting state recovery
  Turn 1/15: Player Implementation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
INFO:guardkit.orchestrator.progress:Completed turn 1: feedback - Player report missing - attempting state recovery
   Note: Implementation may have succeeded; recovering state from git
INFO:guardkit.orchestrator.autobuild:Attempting state recovery for TASK-DOC-001 turn 1 after Player failure: Player report not found: /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392/.guardkit/autobuild/TASK-DOC-001/player_turn_1.json
INFO:guardkit.orchestrator.state_tracker:Capturing state for TASK-DOC-001 turn 1
INFO:guardkit.orchestrator.state_tracker:Loaded Player report from /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392/.guardkit/autobuild/TASK-DOC-001/player_turn_1.json
INFO:guardkit.orchestrator.state_detection:Git detection: 7 files changed (+0/-0)
⠸ Turn 1/15: Player Implementation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   0%INFO:guardkit.orchestrator.state_detection:Test detection (TASK-DOC-001 turn 1): 0 tests, failed
INFO:guardkit.orchestrator.autobuild:No work detected in /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392
WARNING:guardkit.orchestrator.autobuild:State recovery failed for TASK-DOC-001 turn 1
INFO:guardkit.orchestrator.autobuild:Criteria Progress (Turn 1): 0/5 verified (0%)
INFO:guardkit.orchestrator.autobuild:Criteria: 0 verified, 0 rejected, 5 pending
INFO:guardkit.orchestrator.worktree_checkpoints:Creating checkpoint for TASK-DOC-001 turn 1 (tests: fail, count: 0)
INFO:guardkit.orchestrator.worktree_checkpoints:Created checkpoint: cc7b11d3 for turn 1 (1 total)
INFO:guardkit.orchestrator.autobuild:Checkpoint created: cc7b11d3 for turn 1
ERROR:guardkit.orchestrator.autobuild:Critical error on turn 1
INFO:guardkit.orchestrator.autobuild:Phase 4 (Finalize): Preserving worktree for FEAT-F392

                                        AutoBuild Summary (ERROR)
╭────────┬───────────────────────────┬──────────────┬───────────────────────────────────────────────────╮
│ Turn   │ Phase                     │ Status       │ Summary                                           │
├────────┼───────────────────────────┼──────────────┼───────────────────────────────────────────────────┤
│ 1      │ Player Implementation     │ ⚠ feedback   │ Player report missing - attempting state recovery │
╰────────┴───────────────────────────┴──────────────┴───────────────────────────────────────────────────╯

╭────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Status: ERROR                                                                                                                                  │
│                                                                                                                                                │
│ Critical error on turn 1:                                                                                                                      │
│ Player report not found:                                                                                                                       │
│ /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392/.guardkit/autobuild/TASK-DOC-001/player_turn_1.js │
│ on                                                                                                                                             │
│ Worktree preserved for debugging.                                                                                                              │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
INFO:guardkit.orchestrator.progress:Summary rendered: error after 1 turns
INFO:guardkit.orchestrator.autobuild:Worktree preserved at /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392 for human review. Decision: error
INFO:guardkit.orchestrator.autobuild:Orchestration complete: TASK-DOC-001, decision=error, turns=1
    ✗ TASK-DOC-001: error (1 turns)
⠏ Turn 1/15: Player Implementation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   0%INFO:guardkit.orchestrator.agent_invoker:Wrote direct mode results to /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392/.guardkit/autobuild/TASK-DOC-002/task_work_results.json
INFO:guardkit.orchestrator.agent_invoker:Wrote direct mode player report to /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392/.guardkit/autobuild/TASK-DOC-002/player_turn_1.json
  ⚠ Player report missing - attempting state recovery
  Turn 1/15: Player Implementation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
INFO:guardkit.orchestrator.progress:Completed turn 1: feedback - Player report missing - attempting state recovery
   Note: Implementation may have succeeded; recovering state from git
INFO:guardkit.orchestrator.autobuild:Attempting state recovery for TASK-DOC-002 turn 1 after Player failure: Player report not found: /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392/.guardkit/autobuild/TASK-DOC-002/player_turn_1.json
INFO:guardkit.orchestrator.state_tracker:Capturing state for TASK-DOC-002 turn 1
INFO:guardkit.orchestrator.state_tracker:Loaded Player report from /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392/.guardkit/autobuild/TASK-DOC-002/player_turn_1.json
INFO:guardkit.orchestrator.state_detection:Git detection: 3 files changed (+0/-0)
⠹ Turn 1/15: Player Implementation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   0%INFO:guardkit.orchestrator.state_detection:Test detection (TASK-DOC-002 turn 1): 0 tests, failed
INFO:guardkit.orchestrator.autobuild:No work detected in /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392
WARNING:guardkit.orchestrator.autobuild:State recovery failed for TASK-DOC-002 turn 1
INFO:guardkit.orchestrator.autobuild:Criteria Progress (Turn 1): 0/5 verified (0%)
INFO:guardkit.orchestrator.autobuild:Criteria: 0 verified, 0 rejected, 5 pending
INFO:guardkit.orchestrator.worktree_checkpoints:Creating checkpoint for TASK-DOC-002 turn 1 (tests: fail, count: 0)
⠸ Turn 1/15: Player Implementation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   0%INFO:guardkit.orchestrator.worktree_checkpoints:Created checkpoint: af45f79b for turn 1 (1 total)
INFO:guardkit.orchestrator.autobuild:Checkpoint created: af45f79b for turn 1
ERROR:guardkit.orchestrator.autobuild:Critical error on turn 1
INFO:guardkit.orchestrator.autobuild:Phase 4 (Finalize): Preserving worktree for FEAT-F392

                                        AutoBuild Summary (ERROR)
╭────────┬───────────────────────────┬──────────────┬───────────────────────────────────────────────────╮
│ Turn   │ Phase                     │ Status       │ Summary                                           │
├────────┼───────────────────────────┼──────────────┼───────────────────────────────────────────────────┤
│ 1      │ Player Implementation     │ ⚠ feedback   │ Player report missing - attempting state recovery │
╰────────┴───────────────────────────┴──────────────┴───────────────────────────────────────────────────╯

╭────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Status: ERROR                                                                                                                                  │
│                                                                                                                                                │
│ Critical error on turn 1:                                                                                                                      │
│ Player report not found:                                                                                                                       │
│ /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392/.guardkit/autobuild/TASK-DOC-002/player_turn_1.js │
│ on                                                                                                                                             │
│ Worktree preserved for debugging.                                                                                                              │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
INFO:guardkit.orchestrator.progress:Summary rendered: error after 1 turns
INFO:guardkit.orchestrator.autobuild:Worktree preserved at /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392 for human review. Decision: error
INFO:guardkit.orchestrator.autobuild:Orchestration complete: TASK-DOC-002, decision=error, turns=1
    ✗ TASK-DOC-002: error (1 turns)
⠹ Turn 1/15: Player Implementation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   0%INFO:guardkit.orchestrator.agent_invoker:Wrote direct mode results to /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392/.guardkit/autobuild/TASK-DOC-005/task_work_results.json
INFO:guardkit.orchestrator.agent_invoker:Wrote direct mode player report to /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392/.guardkit/autobuild/TASK-DOC-005/player_turn_1.json
  ⚠ Player report missing - attempting state recovery
  Turn 1/15: Player Implementation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
INFO:guardkit.orchestrator.progress:Completed turn 1: feedback - Player report missing - attempting state recovery
   Note: Implementation may have succeeded; recovering state from git
INFO:guardkit.orchestrator.autobuild:Attempting state recovery for TASK-DOC-005 turn 1 after Player failure: Player report not found: /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392/.guardkit/autobuild/TASK-DOC-005/player_turn_1.json
INFO:guardkit.orchestrator.state_tracker:Capturing state for TASK-DOC-005 turn 1
INFO:guardkit.orchestrator.state_tracker:Loaded Player report from /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392/.guardkit/autobuild/TASK-DOC-005/player_turn_1.json
INFO:guardkit.orchestrator.state_detection:Git detection: 3 files changed (+0/-0)
INFO:guardkit.orchestrator.state_detection:Test detection (TASK-DOC-005 turn 1): 0 tests, failed
INFO:guardkit.orchestrator.autobuild:No work detected in /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392
WARNING:guardkit.orchestrator.autobuild:State recovery failed for TASK-DOC-005 turn 1
INFO:guardkit.orchestrator.autobuild:Criteria Progress (Turn 1): 0/7 verified (0%)
INFO:guardkit.orchestrator.autobuild:Criteria: 0 verified, 0 rejected, 7 pending
INFO:guardkit.orchestrator.worktree_checkpoints:Creating checkpoint for TASK-DOC-005 turn 1 (tests: fail, count: 0)
INFO:guardkit.orchestrator.worktree_checkpoints:Created checkpoint: ff12aaf4 for turn 1 (1 total)
INFO:guardkit.orchestrator.autobuild:Checkpoint created: ff12aaf4 for turn 1
ERROR:guardkit.orchestrator.autobuild:Critical error on turn 1
INFO:guardkit.orchestrator.autobuild:Phase 4 (Finalize): Preserving worktree for FEAT-F392

                                        AutoBuild Summary (ERROR)
╭────────┬───────────────────────────┬──────────────┬───────────────────────────────────────────────────╮
│ Turn   │ Phase                     │ Status       │ Summary                                           │
├────────┼───────────────────────────┼──────────────┼───────────────────────────────────────────────────┤
│ 1      │ Player Implementation     │ ⚠ feedback   │ Player report missing - attempting state recovery │
╰────────┴───────────────────────────┴──────────────┴───────────────────────────────────────────────────╯

╭────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Status: ERROR                                                                                                                                  │
│                                                                                                                                                │
│ Critical error on turn 1:                                                                                                                      │
│ Player report not found:                                                                                                                       │
│ /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392/.guardkit/autobuild/TASK-DOC-005/player_turn_1.js │
│ on                                                                                                                                             │
│ Worktree preserved for debugging.                                                                                                              │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
INFO:guardkit.orchestrator.progress:Summary rendered: error after 1 turns
INFO:guardkit.orchestrator.autobuild:Worktree preserved at /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392 for human review. Decision: error
INFO:guardkit.orchestrator.autobuild:Orchestration complete: TASK-DOC-005, decision=error, turns=1
    ✗ TASK-DOC-005: error (1 turns)
  ✗ TASK-DOC-001: FAILED (1 turn) error
  ✗ TASK-DOC-002: FAILED (1 turn) error
  ✗ TASK-DOC-005: FAILED (1 turn) error

  Wave 1 ✗ FAILED: 0 passed, 3 failed
INFO:guardkit.cli.display:Wave 1 complete: passed=0, failed=3
⚠ Stopping execution (stop_on_failure=True)
INFO:guardkit.orchestrator.feature_orchestrator:Phase 3 (Finalize): Updating feature FEAT-F392

════════════════════════════════════════════════════════════
FEATURE RESULT: FAILED
════════════════════════════════════════════════════════════

Feature: FEAT-F392 - Comprehensive API Documentation
Status: FAILED
Tasks: 0/6 completed (3 failed)
Total Turns: 3
Duration: 54s

                                  Wave Summary
╭────────┬──────────┬────────────┬──────────┬──────────┬──────────┬─────────────╮
│  Wave  │  Tasks   │   Status   │  Passed  │  Failed  │  Turns   │  Recovered  │
├────────┼──────────┼────────────┼──────────┼──────────┼──────────┼─────────────┤
│   1    │    3     │   ✗ FAIL   │    0     │    3     │    3     │      3      │
╰────────┴──────────┴────────────┴──────────┴──────────┴──────────┴─────────────╯

Execution Quality:
  Clean executions: 0/3 (0%)
  State recoveries: 3/3 (100%)

Worktree: /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392
Branch: autobuild/FEAT-F392

Next Steps:
  1. Review failed tasks: cd /Users/richardwoollcott/Projects/guardkit_testing/feature-test/.guardkit/worktrees/FEAT-F392
  2. Check status: guardkit autobuild status FEAT-F392
  3. Resume: guardkit autobuild feature FEAT-F392 --resume
INFO:guardkit.cli.display:Final summary rendered: FEAT-F392 - failed
INFO:guardkit.orchestrator.feature_orchestrator:Feature orchestration complete: FEAT-F392, status=failed, completed=0/6
richardwoollcott@Mac feature-test %