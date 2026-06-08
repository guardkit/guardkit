richardwoollcott@Mac guardkit % GUARDKIT_HARNESS=langgraph \
  OPENAI_BASE_URL=http://promaxgb10-41b1:9000/v1 \
  OPENAI_API_KEY=llama-swap-local-key \
  guardkit autobuild feature FEAT-AOF \
    --fresh --model qwen36-workhorse --coach-model gemma4:26b --sdk-timeout 3600 \
    2>&1 | tee .guardkit/autobuild/TASK-REV-HMIG-feature-run/run-14-stdout.log
INFO:guardkit.cli.autobuild:Starting feature orchestration: FEAT-AOF (max_turns=5, stop_on_failure=True, resume=False, fresh=True, refresh=False, sdk_timeout=3600, enable_pre_loop=None, timeout_multiplier=None, max_parallel=None, max_parallel_strategy=static, bootstrap_failure_mode=None)
INFO:guardkit.orchestrator.feature_orchestrator:Raised file descriptor limit: 256 → 4096
INFO:guardkit.orchestrator.feature_orchestrator:FeatureOrchestrator initialized: repo=/Users/richardwoollcott/Projects/appmilla_github/guardkit, max_turns=5, stop_on_failure=True, resume=False, fresh=True, refresh=False, enable_pre_loop=None, enable_context=True, task_timeout=3000s
INFO:guardkit.cli.autobuild:Base branch for feature worktree: main
INFO:guardkit.orchestrator.feature_orchestrator:Starting feature orchestration for FEAT-AOF
INFO:guardkit.orchestrator.feature_orchestrator:Phase 1 (Setup): Loading feature FEAT-AOF
╭──────────────────────────────────────────────────────────────────────────────────────────────────── GuardKit AutoBuild ────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ AutoBuild Feature Orchestration                                                                                                                                                                                            │
│                                                                                                                                                                                                                            │
│ Feature: FEAT-AOF                                                                                                                                                                                                          │
│ Max Turns: 5                                                                                                                                                                                                               │
│ Stop on Failure: True                                                                                                                                                                                                      │
│ Mode: Fresh Start                                                                                                                                                                                                          │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
INFO:guardkit.orchestrator.feature_loader:Loading feature from /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/features/FEAT-AOF.yaml
✓ Loaded feature: AutoBuild Observability Fixes
  Tasks: 3
  Waves: 2
✓ Feature validation passed
✓ Pre-flight validation passed
INFO:guardkit.cli.display:WaveProgressDisplay initialized: waves=2, verbose=False
⚠ Clearing previous incomplete state
✓ Cleaned up previous worktree: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF
✓ Reset feature state
✓ Created shared worktree: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF
INFO:guardkit.orchestrator.feature_orchestrator:Copied task file to worktree: TASK-FIX-IA03-exclude-internal-artifacts-from-doc-constraint.md
INFO:guardkit.orchestrator.feature_orchestrator:Copied task file to worktree: TASK-FIX-GD02-shared-worktree-git-detection-baseline.md
INFO:guardkit.orchestrator.feature_orchestrator:Copied task file to worktree: TASK-FIX-TP05-add-test-execution-for-testing-task-type.md
✓ Copied 3 task file(s) to worktree
⚙ Bootstrapping environment: dotnet, node, python
INFO:guardkit.orchestrator.feature_orchestrator:Bootstrap failure-mode smart default = 'block' (manifests declaring requires-python: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/pyproject.toml)
INFO:guardkit.orchestrator.environment_bootstrap:FFC6: creating worktree-local venv via uv (seeded) at /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.venv
INFO:guardkit.orchestrator.environment_bootstrap:Running dep-install: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.venv/bin/python -m pip install click>=8.0.0
INFO:guardkit.orchestrator.environment_bootstrap:Running dep-install: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.venv/bin/python -m pip install rich>=13.0.0
INFO:guardkit.orchestrator.environment_bootstrap:Running dep-install: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.venv/bin/python -m pip install pyyaml>=6.0.0
INFO:guardkit.orchestrator.environment_bootstrap:Running dep-install: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.venv/bin/python -m pip install python-frontmatter>=1.0.0
INFO:guardkit.orchestrator.environment_bootstrap:Running dep-install: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.venv/bin/python -m pip install pydantic>=2.0.0
INFO:guardkit.orchestrator.environment_bootstrap:Running dep-install: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.venv/bin/python -m pip install Jinja2>=3.1.0
INFO:guardkit.orchestrator.environment_bootstrap:Running dep-install: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.venv/bin/python -m pip install python-dotenv>=1.0.0
INFO:guardkit.orchestrator.environment_bootstrap:Running dep-install: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.venv/bin/python -m pip install httpx>=0.25.0
INFO:guardkit.orchestrator.environment_bootstrap:Running dep-install: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.venv/bin/python -m pip install graphiti-core @ git+https://github.com/guardkit/graphiti.git@v0.29.5-guardkit.1
INFO:guardkit.orchestrator.environment_bootstrap:Running dep-install: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.venv/bin/python -m pip install gherkin-official>=29.0.0
INFO:guardkit.orchestrator.environment_bootstrap:Running install for node (package-lock.json): npm ci
INFO:guardkit.orchestrator.environment_bootstrap:Install succeeded for node (package-lock.json)
INFO:guardkit.orchestrator.environment_bootstrap:Running install for dotnet (guardkit.sln): dotnet restore
INFO:guardkit.orchestrator.environment_bootstrap:Install succeeded for dotnet (guardkit.sln)
INFO:guardkit.orchestrator.environment_bootstrap:Running install for python (requirements.txt): /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.venv/bin/python -m pip install -r requirements.txt
INFO:guardkit.orchestrator.environment_bootstrap:Install succeeded for python (requirements.txt)
✓ Environment bootstrapped: dotnet, node, python
⚙ Coach will verify using interpreter: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.venv/bin/python
INFO:guardkit.orchestrator.feature_orchestrator:Coach pytest interpreter set from bootstrap venv: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.venv/bin/python
INFO:guardkit.orchestrator.feature_orchestrator:Phase 2 (Waves): Executing 2 waves (task_timeout=3000s)
INFO:guardkit.knowledge.graphiti_client:Graphiti factory: thread client created (pending init — will initialize lazily on consumer's event loop)
INFO:guardkit.orchestrator.feature_orchestrator:FalkorDB pre-flight TCP check passed
✓ FalkorDB pre-flight check passed
INFO:guardkit.orchestrator.feature_orchestrator:Pre-initialized Graphiti factory for parallel execution

Starting Wave Execution (task timeout: 50 min)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [2026-06-08T13:36:23.091Z] Wave 1/2: TASK-FIX-IA03
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INFO:guardkit.cli.display:[2026-06-08T13:36:23.091Z] Started wave 1: ['TASK-FIX-IA03']
  ▶ TASK-FIX-IA03: Executing: Exclude internal artifacts from documentation constraint count
INFO:guardkit.orchestrator.feature_orchestrator:[TASK-FIX-IA03] Per-task task_timeout override active: frontmatter=4800s × multiplier=1.0 = 4800s, floored at 3000s → 4800s (feature default was 3000s)
INFO:guardkit.orchestrator.feature_orchestrator:Starting parallel gather for wave 1: tasks=['TASK-FIX-IA03'], task_timeout=3000s (per-task=[TASK-FIX-IA03=4800s])
INFO:guardkit.orchestrator.feature_orchestrator:Task TASK-FIX-IA03: Pre-loop skipped (enable_pre_loop=False)
INFO:guardkit.orchestrator.autobuild:Stored Graphiti factory for per-thread context loading
INFO:guardkit.orchestrator.autobuild:claude-agent-sdk version: 0.1.66
INFO:guardkit.orchestrator.progress:ProgressDisplay initialized with max_turns=5
INFO:guardkit.orchestrator.autobuild:AutoBuildOrchestrator initialized: repo=/Users/richardwoollcott/Projects/appmilla_github/guardkit, max_turns=5, resume=False, enable_pre_loop=False, development_mode=tdd, sdk_timeout=3600s, skip_arch_review=False, enable_perspective_reset=True, reset_turns=[3, 5], enable_checkpoints=True, rollback_on_pollution=True, ablation_mode=False, existing_worktree=provided, enable_context=True, context_loader=None, factory=available, verbose=False
INFO:guardkit.orchestrator.autobuild:Starting orchestration for TASK-FIX-IA03 (resume=False)
INFO:guardkit.orchestrator.autobuild:Phase 1 (Setup): Creating worktree for TASK-FIX-IA03
INFO:guardkit.orchestrator.autobuild:Using existing worktree for TASK-FIX-IA03: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF
INFO:guardkit.orchestrator.autobuild:Phase 2 (Loop): Starting adversarial turns for TASK-FIX-IA03 from turn 1
INFO:guardkit.orchestrator.autobuild:Checkpoint manager initialized for TASK-FIX-IA03 (rollback_on_pollution=True)
INFO:guardkit.orchestrator.autobuild:Executing turn 1/5
INFO:guardkit.orchestrator.progress:[2026-06-08T13:36:23.109Z] Started turn 1: Player Implementation
INFO:guardkit.knowledge.graphiti_client:Graphiti factory: thread client created (pending init — will initialize lazily on consumer's event loop)
WARNING:guardkit.knowledge.falkordb_workaround:[Graphiti] FalkorDB decorator source changed unexpectedly, skipping workaround (manual review needed)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
INFO:guardkit.orchestrator.autobuild:Created per-thread context loader for thread 6153531392
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Loading Player context (turn 1)...
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Similar outcomes found: 4 matches
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Context loaded in 1.2s
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Player context: 7 categories, 3336/5200 tokens
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] preflight_ignore_gate: skipped (no implementation plan and no frontmatter files_to_create / files_to_modify list)
INFO:guardkit.orchestrator.agent_invoker:Recorded baseline commit: fea2e5e2
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] SDK timeout: 3600s (CLI override, skipping dynamic calculation)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Mode: task-work (explicit frontmatter override)
INFO:guardkit.orchestrator.agent_invoker:Invoking Player via task-work delegation for TASK-FIX-IA03 (turn 1)
INFO:guardkit.orchestrator.agent_invoker:Ensuring task TASK-FIX-IA03 is in design_approved state
INFO:guardkit.tasks.state_bridge.TASK-FIX-IA03:Ensuring task TASK-FIX-IA03 is in design_approved state
INFO:guardkit.tasks.state_bridge.TASK-FIX-IA03:Transitioning task TASK-FIX-IA03 from backlog to design_approved
INFO:guardkit.tasks.state_bridge.TASK-FIX-IA03:Moved task file: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tasks/backlog/TASK-FIX-IA03-exclude-internal-artifacts-from-doc-constraint.md -> /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tasks/design_approved/TASK-FIX-IA03-exclude-internal-artifacts-from-doc-constraint.md
INFO:guardkit.tasks.state_bridge.TASK-FIX-IA03:Task file moved to: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tasks/design_approved/TASK-FIX-IA03-exclude-internal-artifacts-from-doc-constraint.md
INFO:guardkit.tasks.state_bridge.TASK-FIX-IA03:Task TASK-FIX-IA03 transitioned to design_approved at /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tasks/design_approved/TASK-FIX-IA03-exclude-internal-artifacts-from-doc-constraint.md
INFO:guardkit.tasks.state_bridge.TASK-FIX-IA03:Created stub implementation plan: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.claude/task-plans/TASK-FIX-IA03-implementation-plan.md
INFO:guardkit.tasks.state_bridge.TASK-FIX-IA03:Created stub implementation plan at: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.claude/task-plans/TASK-FIX-IA03-implementation-plan.md
INFO:guardkit.orchestrator.agent_invoker:Task TASK-FIX-IA03 state verified: design_approved
INFO:guardkit.orchestrator.agent_invoker:Executing inline implement protocol for TASK-FIX-IA03 (mode=tdd)
INFO:guardkit.orchestrator.agent_invoker:Working directory: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF
INFO:guardkit.orchestrator.agent_invoker:Inline protocol size: 19110 bytes (variant=full, multiplier=1.0x)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Max turns: 150 (base=100, complexity=3 x1.3, floored from 130 to 150)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Harness invocation starting
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Working directory: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Allowed tools: ['Read', 'Write', 'Edit', 'Bash', 'Grep', 'Glob', 'Task']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Permission mode: acceptEdits
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Max turns: 150
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] SDK timeout: 3600s
/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/langchain_core/_api/deprecation.py:25: UserWarning: Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.
  from pydantic.v1.fields import FieldInfo as FieldInfoV1
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] task-work implementation in progress... (30s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] task-work implementation in progress... (60s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] task-work implementation in progress... (90s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] task-work implementation in progress... (120s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] task-work implementation in progress... (150s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] task-work implementation in progress... (180s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] task-work implementation in progress... (210s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] task-work implementation in progress... (240s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] task-work implementation in progress... (270s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] task-work implementation in progress... (300s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] task-work implementation in progress... (330s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] task-work implementation in progress... (360s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] task-work implementation in progress... (390s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] task-work implementation in progress... (420s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] SDK completed: turns=None
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Message summary: total=50, assistant=1, tools=0, results=1
INFO:guardkit.orchestrator.agent_invoker:BDD oracle invoking run_bdd_for_task for TASK-FIX-IA03 with python_executable=/Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.venv/bin/python3
INFO:guardkit.orchestrator.agent_invoker:Wrote task_work_results.json to /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/task_work_results.json
INFO:guardkit.orchestrator.agent_invoker:task-work completed successfully for TASK-FIX-IA03
INFO:guardkit.orchestrator.agent_invoker:Created Player report from task_work_results.json for TASK-FIX-IA03 turn 1
INFO:guardkit.orchestrator.agent_invoker:Git detection added: 3 modified, 32 created files for TASK-FIX-IA03
INFO:guardkit.orchestrator.agent_invoker:Recovered 5 completion_promises from agent-written player report for TASK-FIX-IA03
INFO:guardkit.orchestrator.agent_invoker:Recovered 5 requirements_addressed from agent-written player report for TASK-FIX-IA03
INFO:guardkit.orchestrator.agent_invoker:Filtered 4 orchestrator-induced ghost path(s) for TASK-FIX-IA03: ['.guardkit/bootstrap_state.json', 'tasks/backlog/TASK-FIX-GD02-shared-worktree-git-detection-baseline.md', 'tasks/backlog/TASK-FIX-TP05-add-test-execution-for-testing-task-type.md', 'tasks/design_approved/TASK-FIX-IA03-exclude-internal-artifacts-from-doc-constraint.md']
INFO:guardkit.orchestrator.agent_invoker:Written Player report to /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/player_turn_1.json
INFO:guardkit.orchestrator.agent_invoker:Updated task_work_results.json with enriched data for TASK-FIX-IA03
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] SDK invocation complete: 445.5s, 0 SDK turns (445.5s/turn avg)
  ✓ [2026-06-08T13:43:52.401Z] 29 files created, 2 modified, 0 tests (failing)
  [2026-06-08T13:36:23.109Z] Turn 1/5: Player Implementation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
INFO:guardkit.orchestrator.progress:[2026-06-08T13:43:52.401Z] Completed turn 1: success - 29 files created, 2 modified, 0 tests (failing)
   Context: retrieved (7 categories, 3336/5200 tokens)
INFO:guardkit.orchestrator.autobuild:Cumulative requirements_addressed: 5 criteria (current turn: 5, carried: 0)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Mode: task-work (explicit frontmatter override)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] SDK timeout: 3600s (CLI override, skipping dynamic calculation)
INFO:guardkit.orchestrator.specialist_invocations:[TASK-FIX-IA03] test-orchestrator sdk_timeout capped from 3299s to 600s (TASK-FIX-SPECHANG)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] specialist:test-orchestrator invocation in progress... (30s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] specialist:test-orchestrator invocation in progress... (60s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] specialist:test-orchestrator invocation in progress... (90s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] specialist:test-orchestrator invocation in progress... (120s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
WARNING:guardkit.orchestrator.specialist_invocations:[TASK-FIX-IA03] run_specialist(test-orchestrator): hang detected (no model activity for 150s) — terminating before the 600s duration cap
INFO:guardkit.orchestrator.agent_invoker:Extracted partial data from 0 events: 0 text blocks, 0 tool calls, 0 file mods
WARNING:guardkit.orchestrator.specialist_invocations:run_specialist(test-orchestrator) failed for TASK-FIX-IA03: hang detected (no model activity for 150s)
INFO:guardkit.orchestrator.agent_invoker:Injected orchestrator specialist records into /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/task_work_results.json (merged=2, validation=violation)
INFO:guardkit.orchestrator.progress:[2026-06-08T13:46:22.460Z] Started turn 1: Coach Validation
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Loading Coach context (turn 1)...
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Coach context categories: ['similar_outcomes', 'relevant_patterns', 'architecture_context', 'warnings', 'role_constraints', 'turn_states', 'implementation_modes']
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Context loaded in 1.1s
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Coach context: 7 categories, 3210/5200 tokens
INFO:guardkit.orchestrator.autobuild:Using LLM Coach (primary) for TASK-FIX-IA03 turn 1
INFO:guardkit.orchestrator.autobuild:[Graphiti] Coach context provided: 698 chars
INFO:guardkit.orchestrator.quality_gates.coach_validator:CoachValidator pinning independent-test interpreter to /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.venv/bin/python
INFO:guardkit.orchestrator.quality_gates.coach_validator:Quality gate evaluation complete: tests=True (required=True), coverage=True (required=True), arch=True (required=False), audit=True (required=True), ALL_PASSED=True
INFO:guardkit.orchestrator.quality_gates.coach_validator:Test execution environment: sys.executable=/usr/local/bin/python3, which pytest=/Library/Frameworks/Python.framework/Versions/3.14/bin/pytest, coach_test_execution=sdk, resolved_interpreter=/Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.venv/bin/python
INFO:guardkit.orchestrator.quality_gates.coach_validator:Task-specific tests detected via task_work_results: 2 file(s)
INFO:guardkit.orchestrator.quality_gates.coach_validator:Running independent tests via SDK (environment parity): pytest tests/unit/test_agent_invoker.py tests/unit/test_doc_level_constraint.py -v --tb=short
INFO:guardkit.orchestrator.quality_gates.coach_validator:Coach SDK test command pinned to bootstrap interpreter: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.venv/bin/python -m pytest tests/unit/test_agent_invoker.py tests/unit/test_doc_level_constraint.py -v --tb=short
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.quality_gates.coach_validator:SDK independent tests failed in 154.4s
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] SDK timeout: 3600s (CLI override, skipping dynamic calculation)
INFO:openai._base_client:Retrying request to /responses in 0.443062 seconds
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (30s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (60s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (90s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (120s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (150s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (180s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (210s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (240s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (270s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (300s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (330s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (360s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (390s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (420s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (450s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (480s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (510s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (540s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (570s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (600s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (630s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (660s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (690s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (720s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (750s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (780s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (810s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (840s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (870s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (900s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (930s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (960s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (990s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1020s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1050s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1080s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1110s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1140s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1170s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1200s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1230s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1260s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1290s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1320s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1350s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1380s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1410s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1440s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1470s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1500s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1530s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1560s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1590s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1620s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1650s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1680s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1710s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1740s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1770s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1800s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1830s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1860s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1890s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1920s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1950s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (1980s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (2010s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (2040s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (2070s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (2100s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (2130s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (2160s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (2190s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (2220s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (2250s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (2280s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (2310s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (2340s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (2370s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
WARNING:guardkit.orchestrator.autobuild:Coach verdict-emission failed in primary path for TASK-FIX-IA03 turn 1: Coach decision not found: no fenced ```json block in Coach response for TASK-FIX-IA03 turn 1 (328 chars content + 49720 chars reasoning_content). Emitting synthetic feedback decision (substrate F2 at Coach level — Player will retry on turn 2 with this feedback).
INFO:guardkit.orchestrator.autobuild:Wrote synthetic feedback decision to /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/coach_turn_1.json (rationale: Coach verdict-emission failed: Coach decision not found: no fenced ```json block in Coach response for TASK-FIX-IA03 turn 1 (328 chars content + 49720 chars reasoning_content). Likely substrate limitation (qwen36-workhorse F2 at Coach level). Player should retry on turn 2 with this feedback.)
  ⚠ [2026-06-08T14:28:39.791Z] Feedback: Coach verdict-emission failed: Coach decision not found: no fenced ```json block...
  [2026-06-08T13:46:22.460Z] Turn 1/5: Coach Validation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
INFO:guardkit.orchestrator.progress:[2026-06-08T14:28:39.791Z] Completed turn 1: feedback - Feedback: Coach verdict-emission failed: Coach decision not found: no fenced ```json block...
   Context: retrieved (7 categories, 3210/5200 tokens)
INFO:guardkit.orchestrator.autobuild:Turn state saved to local file: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/turn_state_turn_1.json
INFO:guardkit.orchestrator.autobuild:Criteria Progress (Turn 1): 0/5 verified (0%)
INFO:guardkit.orchestrator.autobuild:Criteria: 0 verified, 0 rejected, 5 pending
INFO:guardkit.orchestrator.worktree_checkpoints:Creating checkpoint for TASK-FIX-IA03 turn 1 (tests: fail, count: 0)
INFO:guardkit.orchestrator.worktree_checkpoints:Created checkpoint: a6978cc4 for turn 1 (1 total)
INFO:guardkit.orchestrator.autobuild:Checkpoint created: a6978cc4 for turn 1
INFO:guardkit.orchestrator.autobuild:Coach provided feedback on turn 1
INFO:guardkit.orchestrator.autobuild:Executing turn 2/5
INFO:guardkit.orchestrator.progress:[2026-06-08T14:28:40.178Z] Started turn 2: Player Implementation
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Loading Player context (turn 2)...
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Task <Task pending name='Task-2231' coro=<semaphore_gather.<locals>._wrap_coroutine() running at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/helpers.py:131> cb=[gather.<locals>._done_callback() at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/tasks.py:810]> got Future <Future pending> attached to a different loop
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    WITH rel AS e, score, startNode(rel) AS n, endNode(rel) AS m

            WITH e, score, n, m
            RETURN

        e.uuid AS uuid,
        n.uuid AS source_node_uuid,
        m.uuid AS target_node_uuid,
        e.group_id AS group_id,
        e.created_at AS created_at,
        e.name AS name,
        e.fact AS fact,
        e.episodes AS episodes,
        e.expired_at AS expired_at,
        e.valid_at AS valid_at,
        e.invalid_at AS invalid_at,
    properties(e) AS attributes
            ORDER BY score DESC
            LIMIT $limit

{'query': ' (Task | Exclude | internal | artifacts | from | documentation | constraint | count)', 'limit': 20, 'routing_': 'r'}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Task <Task pending name='Task-2232' coro=<semaphore_gather.<locals>._wrap_coroutine() running at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/helpers.py:131> cb=[gather.<locals>._done_callback() at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/tasks.py:810]> got Future <Future pending> attached to a different loop

        MATCH (n:Entity)-[e:RELATES_TO]->(m:Entity)

            WITH DISTINCT e, n, m, (2 - vec.cosineDistance(e.fact_embedding, vecf32($search_vector)))/2 AS score
            WHERE score > $min_score
            RETURN

        e.uuid AS uuid,
        n.uuid AS source_node_uuid,
        m.uuid AS target_node_uuid,
        e.group_id AS group_id,
        e.created_at AS created_at,
        e.name AS name,
        e.fact AS fact,
        e.episodes AS episodes,
        e.expired_at AS expired_at,
        e.valid_at AS valid_at,
        e.invalid_at AS invalid_at,
    properties(e) AS attributes
            ORDER BY score DESC
            LIMIT $limit

{'search_vector': [0.030854303389787674, 0.044420111924409866, -0.15249265730381012, -0.10637671500444412, 0.012100446037948132, -0.04243450611829758, 0.06303342431783676, 0.05075465887784958, -0.047419700771570206, 0.0009705084376037121, 0.009739557281136513, 0.04131072014570236, 0.08332853764295578, -0.005968444515019655, 0.01620110496878624, -0.011293135583400726, -0.023377785459160805, -0.040890589356422424, -0.014678672887384892, 0.01408441923558712, 0.021125677973031998, 0.014033679850399494, 0.008591284044086933, 0.003143634181469679, 0.05504145100712776, 0.06179807707667351, 0.06027386337518692, 0.023254888132214546, -0.07322773337364197, -0.0015845297602936625, 0.01256964635103941, 0.02799363248050213, -0.010015960782766342, -0.02794552408158779, -0.010754699818789959, -0.05704345181584358, 0.06929459422826767, 0.013339617289602757, -0.026477301493287086, 0.1007043793797493, 0.011091486550867558, -0.022794658318161964, -0.043136175721883774, -0.035925161093473434, -0.021653834730386734, 0.05920710787177086, 0.04779873415827751, 0.023044103756546974, 0.08490107208490372, -0.03656909987330437, 0.019860370084643364, -0.028341177850961685, -0.002615087665617466, -0.020844578742980957, 0.03786735609173775, 0.013601577840745449, -0.0690835490822792, 0.002306619891896844, 0.014626855961978436, -0.05860478803515434, 0.05304853990674019, 0.0210631862282753, -0.03381204232573509, 0.08490485697984695, -0.021656999364495277, -0.026230907067656517, -0.013023956678807735, 0.026644958183169365, -0.006920541170984507, 0.0022428191732615232, 0.010287022218108177, 0.005865653045475483, 0.054995182901620865, -0.0004908764385618269, -0.049247149378061295, 0.0036455276422202587, -0.06764188408851624, -0.018114738166332245, 0.0019920601043850183, 0.05261099711060524, 0.015266765840351582, 0.02861945517361164, 0.06591132283210754, 0.018922867253422737, 0.0808321088552475, 0.022713014855980873, -0.04787297546863556, -0.021220700815320015, -0.015257363207638264, 0.0631396546959877, 0.022089799866080284, -0.045135218650102615, 0.0016985991969704628, -0.0017307768575847149, -0.013725039549171925, 0.02300383895635605, 0.02858244627714157, 0.027713574469089508, -0.04497513547539711, -0.010807839222252369, -0.0005689088138751686, -0.02208631858229637, 0.010738998651504517, -0.020457973703742027, 0.0062552327290177345, -0.008118418976664543, -0.010401858948171139, 0.02946615405380726, -0.022565709426999092, -0.021249422803521156, -0.002396004507318139, 0.03271045535802841, -0.03326736390590668, -0.04666890203952789, 0.006411004811525345, -0.021300725638866425, 0.07643263787031174, -0.008594678714871407, -0.03858562931418419, -0.004771820735186338, -0.05669908598065376, -0.03527238219976425, 0.034821417182683945, 0.015394859947264194, 0.008935380727052689, 0.003926821518689394, -0.07924550026655197, 0.024671422317624092, 0.03546642139554024, -0.060819003731012344, 0.0009726603166200221, -0.006069427356123924, -0.0038421167992055416, 0.0001724377943901345, -0.0020962082780897617, 0.013231690041720867, -0.024662524461746216, -0.010383550077676773, 0.0033337066415697336, -0.006201694719493389, 0.0038142516277730465, 0.032491639256477356, -0.028349796310067177, -0.006959280930459499, 0.019415810704231262, -0.07051411271095276, 0.07964842766523361, -0.01962967962026596, -0.018353372812271118, -0.02979769930243492, 0.005925977602601051, 0.021830657497048378, -0.00649291044101119, 0.00039740066858939826, 0.03224555030465126, -0.062428221106529236, 0.008772051893174648, -0.02437880076467991, -0.06016026437282562, 0.018655987456440926, 0.019988814368844032, 0.020625432953238487, -0.04049528390169144, 0.06219000369310379, -0.008940177969634533, -0.032510481774806976, -0.020898744463920593, 0.06542886793613434, 0.008219041861593723, 0.006392613518983126, -0.021587945520877838, -0.059104468673467636, -0.031420961022377014, 0.03684833273291588, 0.03224372863769531, 0.020564617589116096, 0.043242231011390686, -0.019283603876829147, 0.042374178767204285, -0.021024450659751892, 0.008654273115098476, -0.032648131251335144, 0.021188003942370415, 0.05635427311062813, -0.06458787620067596, -0.04846027493476868, 0.00910431332886219, 0.01107641588896513, 0.0037845447659492493, 0.034955985844135284, 0.017448285594582558, 0.011762850917875767, -0.02987404726445675, -0.06040117144584656, -0.06594642996788025, -0.0631508156657219, 0.055318839848041534, -0.030537614598870277, 0.03246859833598137, -0.07413487881422043, -0.030114291235804558, -0.0014587757177650928, -0.050498105585575104, 0.012630513869225979, -0.040876977145671844, -0.003998949658125639, -0.015539627522230148, 0.012419530190527439, -0.020841114223003387, 0.024615377187728882, 0.060920827090740204, -0.0021354290656745434, -0.009589679539203644, 0.03668854758143425, 0.015315311960875988, -0.03200007975101471, 0.01947806216776371, 0.015535399317741394, 0.020832939073443413, 0.0009696008637547493, 0.005744085181504488, 0.016746096312999725, 0.014648695476353168, -0.02947499230504036, 0.04059843346476555, -0.004542586859315634, -0.007973958738148212, 0.003135488834232092, -0.02053406462073326, -0.017218248918652534, -0.05251000449061394, -0.07307291030883789, 0.022258274257183075, -0.009196942672133446, 0.027808845043182373, 0.02904067188501358, -0.004367210902273655, 0.04121246561408043, 0.005061573814600706, -0.006116786971688271, -0.03674761578440666, 0.05556017532944679, -0.024896636605262756, -0.05013922601938248, -0.030814172700047493, -0.044162649661302567, -0.062292709946632385, -0.00476666959002614, 0.036525826901197433, 0.07863802462816238, -0.04127079248428345, 0.006779748480767012, 0.011375892907381058, 0.0451117604970932, 0.011544778011739254, -0.013557630591094494, 0.005790486000478268, -0.002336176810786128, 0.020907722413539886, -0.016921933740377426, 0.031004132702946663, -0.04633437469601631, 0.04534037411212921, -0.03389233350753784, 0.010420849546790123, -0.0890313908457756, -0.04273815453052521, -0.01057367492467165, 0.05078711360692978, 0.03159687668085098, 0.01779579184949398, 0.04049094393849373, -0.025351176038384438, 0.024667920544743538, 0.043645527213811874, 0.012137873098254204, 0.01148583646863699, -0.009936831891536713, -0.08014784753322601, 0.05653044581413269, -0.022937113419175148, -0.03800298646092415, -0.019486207515001297, 0.03335690498352051, -0.036296501755714417, -0.00939237605780363, -0.009519068524241447, -0.014362206682562828, 0.02882012352347374, -0.0030117493588477373, 0.011293298564851284, 0.04440426826477051, -0.04244352877140045, 0.04045085608959198, -0.009608084335923195, -0.0014369775308296084, -0.011853301897644997, 0.02250063233077526, 0.02013247087597847, -0.03055228479206562, 0.01267393957823515, 0.036434441804885864, 0.024539291858673096, 0.050041742622852325, -0.0454033724963665, -0.07346516102552414, 0.028372399508953094, -0.057826071977615356, 0.015335231088101864, 0.012711949646472931, -0.0006121371989138424, -0.026560060679912567, 0.0012799426913261414, 0.03885176032781601, 0.026761408895254135, 0.05877883732318878, 0.04543119668960571, 0.00772586464881897, 0.009745956398546696, 0.023411206901073456, 0.04102284088730812, -0.0332082137465477, -0.009814807213842869, -0.033480823040008545, -2.577722079877276e-05, 0.030126843601465225, -0.045105114579200745, 0.041004374623298645, 0.0007842665654607117, -0.005297037307173014, 0.04166249930858612, 0.013740862719714642, 0.031283389776945114, -0.047054190188646317, -0.02877264842391014, 0.014451572671532631, -0.008330912329256535, 0.01575607620179653, 0.03836655616760254, 0.028585998341441154, 0.06022465229034424, 0.014461432583630085, -0.03179130330681801, -0.06466642022132874, 0.0034272712655365467, 0.007016490679234266, -0.039520036429166794, 0.01176874153316021, 0.055041804909706116, 0.033385615795850754, -0.027390390634536743, -0.0014993591466918588, -0.008779149502515793, -0.014434798620641232, 0.061815883964300156, -0.004920365288853645, 0.027369704097509384, 0.04413000866770744, 0.013179410248994827, -0.011484737507998943, 0.039524201303720474, 0.0029732936527580023, -0.007710814476013184, -0.037705957889556885, 0.031537484377622604, -0.03127321973443031, 0.06780079752206802, 0.02633778750896454, 0.017419500276446342, 0.0197469349950552, 0.01951937936246395, -0.0045591192319989204, -0.04099363088607788, 0.023796187713742256, 0.006555421743541956, 0.011366328224539757, -0.014717042446136475, 0.02203069068491459, 0.001036526169627905, 0.03396951034665108, 0.04762829467654228, -0.01835354045033455, 0.0145875234156847, -0.030947545543313026, -0.009025374427437782, 0.01380422804504633, 0.00512863602489233, -0.016163822263479233, -0.008085471577942371, 0.012907581403851509, -0.034962475299835205, -0.03494299575686455, -0.08717834204435349, -0.04466240108013153, -0.04784223809838295, -0.06964295357465744, 0.007275538984686136, 0.02197417803108692, 0.016688084229826927, 0.006269244477152824, 0.011667494662106037, -0.030290938913822174, 0.02479977160692215, 0.052434783428907394, -0.0038801429327577353, -0.0033761279191821814, -0.022816507145762444, 0.01698196493089199, 0.03448723256587982, -0.007017314899712801, -0.014474830590188503, 0.013092100620269775, -0.03375625982880592, -0.04335114359855652, 0.0083944546058774, -0.050631266087293625, 0.037903398275375366, 0.03784511238336563, -0.004824098665267229, -0.03681499883532524, 0.02633029595017433, 0.02761826477944851, -0.041753675788640976, 0.044726572930812836, -0.025942586362361908, 0.004498520400375128, -0.016526924446225166, 0.022614790126681328, -0.008134102448821068, -0.05933374911546707, -0.0170682892203331, 0.01950790546834469, 0.021993154659867287, 0.009258713573217392, 0.03577309474349022, -0.006040777079761028, -0.01689918525516987, 0.06474629044532776, -0.02051452361047268, -0.00036078979610465467, -0.03116770274937153, -0.05411141738295555, -0.000868296017870307, -0.021237049251794815, -0.02066796086728573, 0.1410542130470276, 0.013606356456875801, -0.07145093381404877, -0.04837123304605484, 0.08660349249839783, -0.002405100269243121, -0.019075384363532066, -0.019365357235074043, 0.01851011998951435, 0.09412426501512527, -0.04911787062883377, -0.0128995506092906, -0.012053918093442917, 0.018046263605356216, 0.009170940145850182, -0.002959242556244135, 0.017280634492635727, -0.08543619513511658, 0.026256514713168144, 0.011546459048986435, -0.060465261340141296, -0.010382202453911304, -0.025028161704540253, 0.014011220075190067, 0.06226490065455437, 0.009866099804639816, 0.00215950608253479, 0.044206373393535614, -0.025937983766198158, -0.04592662304639816, 0.0696454867720604, -0.04790687933564186, 0.033494751900434494, -0.0342155396938324, 0.018412841483950615, 0.006006625946611166, -0.008958608843386173, -0.039286091923713684, -0.02734021097421646, 0.022405074909329414, 0.0077576590701937675, 0.0069428700953722, -0.009068222716450691, -0.015969447791576385, -0.003446749644353986, 0.018665464594960213, 0.024162519723176956, -0.0059588816948235035, 0.008749212138354778, 0.009875757619738579, -0.03014211170375347, 0.025601701810956, 0.01869679056107998, 0.0246793981641531, 0.019739555194973946, 0.06411167979240417, 0.05066834017634392, -0.014157998375594616, -0.005476726684719324, -0.01567935384809971, -0.02035285159945488, 0.02749427780508995, 0.0036189230158925056, -0.0247687716037035, 0.030312618240714073, 0.0089853061363101, 0.0016174375778064132, 0.056089311838150024, -0.022030271589756012, 0.006874339189380407, -0.00895246583968401, 0.032182205468416214, -0.03530276566743851, -0.019067786633968353, -0.00041821703780442476, 0.01952420547604561, -0.023877020925283432, -0.004116514232009649, -0.017472196370363235, -0.04512961208820343, -0.000665262050461024, -0.014393500983715057, -0.03532331436872482, 0.029158594086766243, 0.002970918081700802, 0.014826922677457333, -0.018131354823708534, -0.025618651881814003, -0.023017656058073044, 0.006374831777065992, -0.034000277519226074, -0.011428195051848888, 0.017366480082273483, 0.011100251227617264, 0.044000230729579926, 0.044098109006881714, 0.016931546851992607, 0.010904215276241302, -0.018336711451411247, 0.02236248552799225, -0.010801452212035656, -0.020552759990096092, -0.015648270025849342, 0.00944614503532648, -0.056049101054668427, 0.06992045789957047, -0.04755287989974022, 0.022811388596892357, -0.01905207894742489, -0.0005521976854652166, -0.0551159493625164, 0.05771920084953308, 0.003313681110739708, -0.012554156593978405, -0.03491245582699776, -0.0004493989108595997, -0.014836834743618965, 0.04550186172127724, 0.020224926993250847, -0.05434810370206833, -0.04117658734321594, 0.04879456013441086, 0.0044229221530258656, 0.00014753938012290746, -0.004815257154405117, 0.026253147050738335, -0.055342838168144226, 0.03325096517801285, -0.032094795256853104, -0.026725497096776962, 0.023136254400014877, 0.011950789950788021, -0.0103463688865304, -0.05655030533671379, -0.046430908143520355, -0.0267023965716362, 0.0395653173327446, 0.05470247194170952, -0.013899288140237331, -0.01553690992295742, -0.0022124205715954304, -0.04116209223866463, 0.008374559693038464, 0.00025515008019283414, -0.03426636382937431, 0.018935082480311394, -0.03281891345977783, 0.008798615075647831, -0.003970039077103138, 0.023412812501192093, 0.01249433308839798, 0.005455314181745052, -0.03127866983413696, -0.014486162923276424, -0.02090301364660263, 0.042937275022268295, 0.01781703159213066, 0.07737474888563156, -0.038432423025369644, 0.04660644009709358, 0.03936861827969551, -0.036005668342113495, -0.007055961061269045, -0.03164416924118996, -0.07419944554567337, 0.0163675956428051, -0.019986335188150406, 0.005489252973347902, -0.012046100571751595, 0.07889817655086517, 0.003632165491580963, 0.03799762949347496, 0.01776469498872757, -0.05217905715107918, -0.016886189579963684, -0.005470234900712967, -0.014474772848188877, 0.028447190299630165, -0.009267609566450119, 0.02553260140120983, 0.00029502619872801006, -0.04289427772164345, -0.07489494979381561, 0.0339854434132576, 0.0716659426689148, -0.048315130174160004, 0.03441132977604866, -0.04454869031906128, -0.054023511707782745, -0.055228911340236664, 0.0653805285692215, -0.06105642765760422, 0.02747117541730404, 0.022343460470438004, 0.054343778640031815, 0.054604314267635345, -0.05817830562591553, -0.01679248735308647, -0.0010837821755558252, 0.014680511318147182, -0.001355848740786314, 0.04336355999112129, -0.023284299299120903, 0.03481322154402733, -0.04792078211903572, 0.10271584987640381, 0.08732537180185318, 0.054378923028707504, -0.01721859723329544, -0.03389263153076172, -0.014271000400185585, 0.04410644993185997, -0.0589648000895977, -0.10395977646112442, -0.00496978173032403, -0.06351707130670547, -0.004880223888903856, -0.01944292150437832, -0.005041536875069141, 0.009868779219686985, -0.021076470613479614, 0.01312626339495182, 0.026089007034897804, -0.03957432508468628, -0.03165239095687866, -0.007891243323683739, 0.03477873653173447, -0.02714000642299652, 0.015237584710121155, 0.02066756784915924, 0.04407768324017525, 0.0550769567489624, 0.030107609927654266, 0.011853663250803947, -0.024173792451620102, 0.014376195147633553, 0.039699945598840714, 0.029913295060396194, -0.08497583121061325, -0.00600552000105381, -0.058703407645225525, 0.006733874324709177, -0.05282263830304146, 0.07921307533979416, -0.019159402698278427, -0.015873195603489876, -0.015008191578090191, 0.022100985050201416, -0.01039169542491436, 0.0033424696885049343, 0.008858509361743927, -0.0025448312517255545, -0.027001190930604935, -0.010651796124875546, 0.052164994180202484, 0.01010804995894432, 0.04327412322163582, 0.03155792877078056, 0.04873507469892502, -0.05584387108683586, -0.01144381333142519, 0.016647186130285263, -0.0056302244774997234, 0.028161536902189255, 0.003070868318900466, -0.06414170563220978, -0.0006059580482542515, -0.0428224615752697, -0.04291451722383499, 0.07868633419275284, 0.04224000126123428, -0.041797857731580734, -0.00715819513425231, 0.013175282627344131, -0.03949834778904915, 0.03971945121884346, 0.038237158209085464, -0.08042848855257034, 0.00833877269178629, -0.005447081755846739, 0.001438029925338924, 0.05658696964383125, -0.031710442155599594, 0.012549635954201221, -0.04449569806456566, -0.013632243499159813, -0.027496619150042534, -0.05011378601193428, 0.07866339385509491, -0.009958427399396896, 0.02002735435962677, -0.004567462485283613, -0.02472861297428608, -0.04544831067323685, -0.006320023909211159, -0.052056245505809784, 0.03617715835571289, -0.036273665726184845, -0.006447257474064827, -0.015921685844659805, -0.012914253398776054, -0.061711035668849945, 0.010351206175982952, 0.06757895648479462, -0.01615845412015915, -0.0064978646114468575, -0.054074425250291824, -0.00034396920818835497, -0.01857716031372547, 0.006079723127186298, -0.012334990315139294, 0.012357001192867756, -0.026382653042674065, 0.11951392143964767, 0.05628421530127525, 0.03174267336726189, 0.03577876463532448, 0.012030803598463535, 0.03710776939988136, -0.01720442809164524, -0.036914411932229996, 0.007174555212259293, -0.062310632318258286], 'limit': 20, 'min_score': 0.6, 'routing_': 'r'}
WARNING:guardkit.knowledge.graphiti_client:Search request failed: Task <Task pending name='Task-2231' coro=<semaphore_gather.<locals>._wrap_coroutine() running at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/helpers.py:131> cb=[gather.<locals>._done_callback() at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/tasks.py:810]> got Future <Future pending> attached to a different loop
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    WITH rel AS e, score, startNode(rel) AS n, endNode(rel) AS m
     WHERE e.group_id IN $group_ids
            WITH e, score, n, m
            RETURN

        e.uuid AS uuid,
        n.uuid AS source_node_uuid,
        m.uuid AS target_node_uuid,
        e.group_id AS group_id,
        e.created_at AS created_at,
        e.name AS name,
        e.fact AS fact,
        e.episodes AS episodes,
        e.expired_at AS expired_at,
        e.valid_at AS valid_at,
        e.invalid_at AS invalid_at,
    properties(e) AS attributes
            ORDER BY score DESC
            LIMIT $limit

{'query': ' (Task | Exclude | internal | artifacts | from | documentation | constraint | count)', 'limit': 20, 'routing_': 'r', 'group_ids': ['guardkit__feature_specs']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop

        MATCH (n:Entity)-[e:RELATES_TO]->(m:Entity)
     WHERE e.group_id IN $group_ids
            WITH DISTINCT e, n, m, (2 - vec.cosineDistance(e.fact_embedding, vecf32($search_vector)))/2 AS score
            WHERE score > $min_score
            RETURN

        e.uuid AS uuid,
        n.uuid AS source_node_uuid,
        m.uuid AS target_node_uuid,
        e.group_id AS group_id,
        e.created_at AS created_at,
        e.name AS name,
        e.fact AS fact,
        e.episodes AS episodes,
        e.expired_at AS expired_at,
        e.valid_at AS valid_at,
        e.invalid_at AS invalid_at,
    properties(e) AS attributes
            ORDER BY score DESC
            LIMIT $limit

{'search_vector': [0.030854303389787674, 0.044420111924409866, -0.15249265730381012, -0.10637671500444412, 0.012100446037948132, -0.04243450611829758, 0.06303342431783676, 0.05075465887784958, -0.047419700771570206, 0.0009705084376037121, 0.009739557281136513, 0.04131072014570236, 0.08332853764295578, -0.005968444515019655, 0.01620110496878624, -0.011293135583400726, -0.023377785459160805, -0.040890589356422424, -0.014678672887384892, 0.01408441923558712, 0.021125677973031998, 0.014033679850399494, 0.008591284044086933, 0.003143634181469679, 0.05504145100712776, 0.06179807707667351, 0.06027386337518692, 0.023254888132214546, -0.07322773337364197, -0.0015845297602936625, 0.01256964635103941, 0.02799363248050213, -0.010015960782766342, -0.02794552408158779, -0.010754699818789959, -0.05704345181584358, 0.06929459422826767, 0.013339617289602757, -0.026477301493287086, 0.1007043793797493, 0.011091486550867558, -0.022794658318161964, -0.043136175721883774, -0.035925161093473434, -0.021653834730386734, 0.05920710787177086, 0.04779873415827751, 0.023044103756546974, 0.08490107208490372, -0.03656909987330437, 0.019860370084643364, -0.028341177850961685, -0.002615087665617466, -0.020844578742980957, 0.03786735609173775, 0.013601577840745449, -0.0690835490822792, 0.002306619891896844, 0.014626855961978436, -0.05860478803515434, 0.05304853990674019, 0.0210631862282753, -0.03381204232573509, 0.08490485697984695, -0.021656999364495277, -0.026230907067656517, -0.013023956678807735, 0.026644958183169365, -0.006920541170984507, 0.0022428191732615232, 0.010287022218108177, 0.005865653045475483, 0.054995182901620865, -0.0004908764385618269, -0.049247149378061295, 0.0036455276422202587, -0.06764188408851624, -0.018114738166332245, 0.0019920601043850183, 0.05261099711060524, 0.015266765840351582, 0.02861945517361164, 0.06591132283210754, 0.018922867253422737, 0.0808321088552475, 0.022713014855980873, -0.04787297546863556, -0.021220700815320015, -0.015257363207638264, 0.0631396546959877, 0.022089799866080284, -0.045135218650102615, 0.0016985991969704628, -0.0017307768575847149, -0.013725039549171925, 0.02300383895635605, 0.02858244627714157, 0.027713574469089508, -0.04497513547539711, -0.010807839222252369, -0.0005689088138751686, -0.02208631858229637, 0.010738998651504517, -0.020457973703742027, 0.0062552327290177345, -0.008118418976664543, -0.010401858948171139, 0.02946615405380726, -0.022565709426999092, -0.021249422803521156, -0.002396004507318139, 0.03271045535802841, -0.03326736390590668, -0.04666890203952789, 0.006411004811525345, -0.021300725638866425, 0.07643263787031174, -0.008594678714871407, -0.03858562931418419, -0.004771820735186338, -0.05669908598065376, -0.03527238219976425, 0.034821417182683945, 0.015394859947264194, 0.008935380727052689, 0.003926821518689394, -0.07924550026655197, 0.024671422317624092, 0.03546642139554024, -0.060819003731012344, 0.0009726603166200221, -0.006069427356123924, -0.0038421167992055416, 0.0001724377943901345, -0.0020962082780897617, 0.013231690041720867, -0.024662524461746216, -0.010383550077676773, 0.0033337066415697336, -0.006201694719493389, 0.0038142516277730465, 0.032491639256477356, -0.028349796310067177, -0.006959280930459499, 0.019415810704231262, -0.07051411271095276, 0.07964842766523361, -0.01962967962026596, -0.018353372812271118, -0.02979769930243492, 0.005925977602601051, 0.021830657497048378, -0.00649291044101119, 0.00039740066858939826, 0.03224555030465126, -0.062428221106529236, 0.008772051893174648, -0.02437880076467991, -0.06016026437282562, 0.018655987456440926, 0.019988814368844032, 0.020625432953238487, -0.04049528390169144, 0.06219000369310379, -0.008940177969634533, -0.032510481774806976, -0.020898744463920593, 0.06542886793613434, 0.008219041861593723, 0.006392613518983126, -0.021587945520877838, -0.059104468673467636, -0.031420961022377014, 0.03684833273291588, 0.03224372863769531, 0.020564617589116096, 0.043242231011390686, -0.019283603876829147, 0.042374178767204285, -0.021024450659751892, 0.008654273115098476, -0.032648131251335144, 0.021188003942370415, 0.05635427311062813, -0.06458787620067596, -0.04846027493476868, 0.00910431332886219, 0.01107641588896513, 0.0037845447659492493, 0.034955985844135284, 0.017448285594582558, 0.011762850917875767, -0.02987404726445675, -0.06040117144584656, -0.06594642996788025, -0.0631508156657219, 0.055318839848041534, -0.030537614598870277, 0.03246859833598137, -0.07413487881422043, -0.030114291235804558, -0.0014587757177650928, -0.050498105585575104, 0.012630513869225979, -0.040876977145671844, -0.003998949658125639, -0.015539627522230148, 0.012419530190527439, -0.020841114223003387, 0.024615377187728882, 0.060920827090740204, -0.0021354290656745434, -0.009589679539203644, 0.03668854758143425, 0.015315311960875988, -0.03200007975101471, 0.01947806216776371, 0.015535399317741394, 0.020832939073443413, 0.0009696008637547493, 0.005744085181504488, 0.016746096312999725, 0.014648695476353168, -0.02947499230504036, 0.04059843346476555, -0.004542586859315634, -0.007973958738148212, 0.003135488834232092, -0.02053406462073326, -0.017218248918652534, -0.05251000449061394, -0.07307291030883789, 0.022258274257183075, -0.009196942672133446, 0.027808845043182373, 0.02904067188501358, -0.004367210902273655, 0.04121246561408043, 0.005061573814600706, -0.006116786971688271, -0.03674761578440666, 0.05556017532944679, -0.024896636605262756, -0.05013922601938248, -0.030814172700047493, -0.044162649661302567, -0.062292709946632385, -0.00476666959002614, 0.036525826901197433, 0.07863802462816238, -0.04127079248428345, 0.006779748480767012, 0.011375892907381058, 0.0451117604970932, 0.011544778011739254, -0.013557630591094494, 0.005790486000478268, -0.002336176810786128, 0.020907722413539886, -0.016921933740377426, 0.031004132702946663, -0.04633437469601631, 0.04534037411212921, -0.03389233350753784, 0.010420849546790123, -0.0890313908457756, -0.04273815453052521, -0.01057367492467165, 0.05078711360692978, 0.03159687668085098, 0.01779579184949398, 0.04049094393849373, -0.025351176038384438, 0.024667920544743538, 0.043645527213811874, 0.012137873098254204, 0.01148583646863699, -0.009936831891536713, -0.08014784753322601, 0.05653044581413269, -0.022937113419175148, -0.03800298646092415, -0.019486207515001297, 0.03335690498352051, -0.036296501755714417, -0.00939237605780363, -0.009519068524241447, -0.014362206682562828, 0.02882012352347374, -0.0030117493588477373, 0.011293298564851284, 0.04440426826477051, -0.04244352877140045, 0.04045085608959198, -0.009608084335923195, -0.0014369775308296084, -0.011853301897644997, 0.02250063233077526, 0.02013247087597847, -0.03055228479206562, 0.01267393957823515, 0.036434441804885864, 0.024539291858673096, 0.050041742622852325, -0.0454033724963665, -0.07346516102552414, 0.028372399508953094, -0.057826071977615356, 0.015335231088101864, 0.012711949646472931, -0.0006121371989138424, -0.026560060679912567, 0.0012799426913261414, 0.03885176032781601, 0.026761408895254135, 0.05877883732318878, 0.04543119668960571, 0.00772586464881897, 0.009745956398546696, 0.023411206901073456, 0.04102284088730812, -0.0332082137465477, -0.009814807213842869, -0.033480823040008545, -2.577722079877276e-05, 0.030126843601465225, -0.045105114579200745, 0.041004374623298645, 0.0007842665654607117, -0.005297037307173014, 0.04166249930858612, 0.013740862719714642, 0.031283389776945114, -0.047054190188646317, -0.02877264842391014, 0.014451572671532631, -0.008330912329256535, 0.01575607620179653, 0.03836655616760254, 0.028585998341441154, 0.06022465229034424, 0.014461432583630085, -0.03179130330681801, -0.06466642022132874, 0.0034272712655365467, 0.007016490679234266, -0.039520036429166794, 0.01176874153316021, 0.055041804909706116, 0.033385615795850754, -0.027390390634536743, -0.0014993591466918588, -0.008779149502515793, -0.014434798620641232, 0.061815883964300156, -0.004920365288853645, 0.027369704097509384, 0.04413000866770744, 0.013179410248994827, -0.011484737507998943, 0.039524201303720474, 0.0029732936527580023, -0.007710814476013184, -0.037705957889556885, 0.031537484377622604, -0.03127321973443031, 0.06780079752206802, 0.02633778750896454, 0.017419500276446342, 0.0197469349950552, 0.01951937936246395, -0.0045591192319989204, -0.04099363088607788, 0.023796187713742256, 0.006555421743541956, 0.011366328224539757, -0.014717042446136475, 0.02203069068491459, 0.001036526169627905, 0.03396951034665108, 0.04762829467654228, -0.01835354045033455, 0.0145875234156847, -0.030947545543313026, -0.009025374427437782, 0.01380422804504633, 0.00512863602489233, -0.016163822263479233, -0.008085471577942371, 0.012907581403851509, -0.034962475299835205, -0.03494299575686455, -0.08717834204435349, -0.04466240108013153, -0.04784223809838295, -0.06964295357465744, 0.007275538984686136, 0.02197417803108692, 0.016688084229826927, 0.006269244477152824, 0.011667494662106037, -0.030290938913822174, 0.02479977160692215, 0.052434783428907394, -0.0038801429327577353, -0.0033761279191821814, -0.022816507145762444, 0.01698196493089199, 0.03448723256587982, -0.007017314899712801, -0.014474830590188503, 0.013092100620269775, -0.03375625982880592, -0.04335114359855652, 0.0083944546058774, -0.050631266087293625, 0.037903398275375366, 0.03784511238336563, -0.004824098665267229, -0.03681499883532524, 0.02633029595017433, 0.02761826477944851, -0.041753675788640976, 0.044726572930812836, -0.025942586362361908, 0.004498520400375128, -0.016526924446225166, 0.022614790126681328, -0.008134102448821068, -0.05933374911546707, -0.0170682892203331, 0.01950790546834469, 0.021993154659867287, 0.009258713573217392, 0.03577309474349022, -0.006040777079761028, -0.01689918525516987, 0.06474629044532776, -0.02051452361047268, -0.00036078979610465467, -0.03116770274937153, -0.05411141738295555, -0.000868296017870307, -0.021237049251794815, -0.02066796086728573, 0.1410542130470276, 0.013606356456875801, -0.07145093381404877, -0.04837123304605484, 0.08660349249839783, -0.002405100269243121, -0.019075384363532066, -0.019365357235074043, 0.01851011998951435, 0.09412426501512527, -0.04911787062883377, -0.0128995506092906, -0.012053918093442917, 0.018046263605356216, 0.009170940145850182, -0.002959242556244135, 0.017280634492635727, -0.08543619513511658, 0.026256514713168144, 0.011546459048986435, -0.060465261340141296, -0.010382202453911304, -0.025028161704540253, 0.014011220075190067, 0.06226490065455437, 0.009866099804639816, 0.00215950608253479, 0.044206373393535614, -0.025937983766198158, -0.04592662304639816, 0.0696454867720604, -0.04790687933564186, 0.033494751900434494, -0.0342155396938324, 0.018412841483950615, 0.006006625946611166, -0.008958608843386173, -0.039286091923713684, -0.02734021097421646, 0.022405074909329414, 0.0077576590701937675, 0.0069428700953722, -0.009068222716450691, -0.015969447791576385, -0.003446749644353986, 0.018665464594960213, 0.024162519723176956, -0.0059588816948235035, 0.008749212138354778, 0.009875757619738579, -0.03014211170375347, 0.025601701810956, 0.01869679056107998, 0.0246793981641531, 0.019739555194973946, 0.06411167979240417, 0.05066834017634392, -0.014157998375594616, -0.005476726684719324, -0.01567935384809971, -0.02035285159945488, 0.02749427780508995, 0.0036189230158925056, -0.0247687716037035, 0.030312618240714073, 0.0089853061363101, 0.0016174375778064132, 0.056089311838150024, -0.022030271589756012, 0.006874339189380407, -0.00895246583968401, 0.032182205468416214, -0.03530276566743851, -0.019067786633968353, -0.00041821703780442476, 0.01952420547604561, -0.023877020925283432, -0.004116514232009649, -0.017472196370363235, -0.04512961208820343, -0.000665262050461024, -0.014393500983715057, -0.03532331436872482, 0.029158594086766243, 0.002970918081700802, 0.014826922677457333, -0.018131354823708534, -0.025618651881814003, -0.023017656058073044, 0.006374831777065992, -0.034000277519226074, -0.011428195051848888, 0.017366480082273483, 0.011100251227617264, 0.044000230729579926, 0.044098109006881714, 0.016931546851992607, 0.010904215276241302, -0.018336711451411247, 0.02236248552799225, -0.010801452212035656, -0.020552759990096092, -0.015648270025849342, 0.00944614503532648, -0.056049101054668427, 0.06992045789957047, -0.04755287989974022, 0.022811388596892357, -0.01905207894742489, -0.0005521976854652166, -0.0551159493625164, 0.05771920084953308, 0.003313681110739708, -0.012554156593978405, -0.03491245582699776, -0.0004493989108595997, -0.014836834743618965, 0.04550186172127724, 0.020224926993250847, -0.05434810370206833, -0.04117658734321594, 0.04879456013441086, 0.0044229221530258656, 0.00014753938012290746, -0.004815257154405117, 0.026253147050738335, -0.055342838168144226, 0.03325096517801285, -0.032094795256853104, -0.026725497096776962, 0.023136254400014877, 0.011950789950788021, -0.0103463688865304, -0.05655030533671379, -0.046430908143520355, -0.0267023965716362, 0.0395653173327446, 0.05470247194170952, -0.013899288140237331, -0.01553690992295742, -0.0022124205715954304, -0.04116209223866463, 0.008374559693038464, 0.00025515008019283414, -0.03426636382937431, 0.018935082480311394, -0.03281891345977783, 0.008798615075647831, -0.003970039077103138, 0.023412812501192093, 0.01249433308839798, 0.005455314181745052, -0.03127866983413696, -0.014486162923276424, -0.02090301364660263, 0.042937275022268295, 0.01781703159213066, 0.07737474888563156, -0.038432423025369644, 0.04660644009709358, 0.03936861827969551, -0.036005668342113495, -0.007055961061269045, -0.03164416924118996, -0.07419944554567337, 0.0163675956428051, -0.019986335188150406, 0.005489252973347902, -0.012046100571751595, 0.07889817655086517, 0.003632165491580963, 0.03799762949347496, 0.01776469498872757, -0.05217905715107918, -0.016886189579963684, -0.005470234900712967, -0.014474772848188877, 0.028447190299630165, -0.009267609566450119, 0.02553260140120983, 0.00029502619872801006, -0.04289427772164345, -0.07489494979381561, 0.0339854434132576, 0.0716659426689148, -0.048315130174160004, 0.03441132977604866, -0.04454869031906128, -0.054023511707782745, -0.055228911340236664, 0.0653805285692215, -0.06105642765760422, 0.02747117541730404, 0.022343460470438004, 0.054343778640031815, 0.054604314267635345, -0.05817830562591553, -0.01679248735308647, -0.0010837821755558252, 0.014680511318147182, -0.001355848740786314, 0.04336355999112129, -0.023284299299120903, 0.03481322154402733, -0.04792078211903572, 0.10271584987640381, 0.08732537180185318, 0.054378923028707504, -0.01721859723329544, -0.03389263153076172, -0.014271000400185585, 0.04410644993185997, -0.0589648000895977, -0.10395977646112442, -0.00496978173032403, -0.06351707130670547, -0.004880223888903856, -0.01944292150437832, -0.005041536875069141, 0.009868779219686985, -0.021076470613479614, 0.01312626339495182, 0.026089007034897804, -0.03957432508468628, -0.03165239095687866, -0.007891243323683739, 0.03477873653173447, -0.02714000642299652, 0.015237584710121155, 0.02066756784915924, 0.04407768324017525, 0.0550769567489624, 0.030107609927654266, 0.011853663250803947, -0.024173792451620102, 0.014376195147633553, 0.039699945598840714, 0.029913295060396194, -0.08497583121061325, -0.00600552000105381, -0.058703407645225525, 0.006733874324709177, -0.05282263830304146, 0.07921307533979416, -0.019159402698278427, -0.015873195603489876, -0.015008191578090191, 0.022100985050201416, -0.01039169542491436, 0.0033424696885049343, 0.008858509361743927, -0.0025448312517255545, -0.027001190930604935, -0.010651796124875546, 0.052164994180202484, 0.01010804995894432, 0.04327412322163582, 0.03155792877078056, 0.04873507469892502, -0.05584387108683586, -0.01144381333142519, 0.016647186130285263, -0.0056302244774997234, 0.028161536902189255, 0.003070868318900466, -0.06414170563220978, -0.0006059580482542515, -0.0428224615752697, -0.04291451722383499, 0.07868633419275284, 0.04224000126123428, -0.041797857731580734, -0.00715819513425231, 0.013175282627344131, -0.03949834778904915, 0.03971945121884346, 0.038237158209085464, -0.08042848855257034, 0.00833877269178629, -0.005447081755846739, 0.001438029925338924, 0.05658696964383125, -0.031710442155599594, 0.012549635954201221, -0.04449569806456566, -0.013632243499159813, -0.027496619150042534, -0.05011378601193428, 0.07866339385509491, -0.009958427399396896, 0.02002735435962677, -0.004567462485283613, -0.02472861297428608, -0.04544831067323685, -0.006320023909211159, -0.052056245505809784, 0.03617715835571289, -0.036273665726184845, -0.006447257474064827, -0.015921685844659805, -0.012914253398776054, -0.061711035668849945, 0.010351206175982952, 0.06757895648479462, -0.01615845412015915, -0.0064978646114468575, -0.054074425250291824, -0.00034396920818835497, -0.01857716031372547, 0.006079723127186298, -0.012334990315139294, 0.012357001192867756, -0.026382653042674065, 0.11951392143964767, 0.05628421530127525, 0.03174267336726189, 0.03577876463532448, 0.012030803598463535, 0.03710776939988136, -0.01720442809164524, -0.036914411932229996, 0.007174555212259293, -0.062310632318258286], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'group_ids': ['guardkit__feature_specs']}
WARNING:guardkit.knowledge.graphiti_client:Search request failed: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop
CREATE INDEX FOR (n:Entity) ON (n.uuid, n.group_id, n.name, n.created_at)
{}
ERROR:asyncio:Task exception was never retrieved
future: <Task finished name='Task-2242' coro=<FalkorDriver.build_indices_and_constraints() done, defined at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py:300> exception=RuntimeError('<asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop')>
Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 305, in build_indices_and_constraints
    await self.execute_query(query)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 230, in execute_query
    result = await graph.query(cypher_query_, params)  # type: ignore[reportUnknownArgumentType]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 105, in query
    return await self._query(q, params=params, timeout=timeout, read_only=False)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 79, in _query
    response = await self.execute_command(*command)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/client.py", line 720, in execute_command
    conn = self.connection or await pool.get_connection()
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/connection.py", line 1194, in get_connection
    async with self._lock:
               ^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 14, in __aenter__
    await self.acquire()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 105, in acquire
    fut = self._get_loop().create_future()
          ~~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/mixins.py", line 20, in _get_loop
    raise RuntimeError(f'{self!r} is bound to a different event loop')
RuntimeError: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop

        MATCH (n:Entity)-[e:RELATES_TO]->(m:Entity)
     WHERE e.group_id IN $group_ids
            WITH DISTINCT e, n, m, (2 - vec.cosineDistance(e.fact_embedding, vecf32($search_vector)))/2 AS score
            WHERE score > $min_score
            RETURN

        e.uuid AS uuid,
        n.uuid AS source_node_uuid,
        m.uuid AS target_node_uuid,
        e.group_id AS group_id,
        e.created_at AS created_at,
        e.name AS name,
        e.fact AS fact,
        e.episodes AS episodes,
        e.expired_at AS expired_at,
        e.valid_at AS valid_at,
        e.invalid_at AS invalid_at,
    properties(e) AS attributes
            ORDER BY score DESC
            LIMIT $limit

{'search_vector': [0.030854303389787674, 0.044420111924409866, -0.15249265730381012, -0.10637671500444412, 0.012100446037948132, -0.04243450611829758, 0.06303342431783676, 0.05075465887784958, -0.047419700771570206, 0.0009705084376037121, 0.009739557281136513, 0.04131072014570236, 0.08332853764295578, -0.005968444515019655, 0.01620110496878624, -0.011293135583400726, -0.023377785459160805, -0.040890589356422424, -0.014678672887384892, 0.01408441923558712, 0.021125677973031998, 0.014033679850399494, 0.008591284044086933, 0.003143634181469679, 0.05504145100712776, 0.06179807707667351, 0.06027386337518692, 0.023254888132214546, -0.07322773337364197, -0.0015845297602936625, 0.01256964635103941, 0.02799363248050213, -0.010015960782766342, -0.02794552408158779, -0.010754699818789959, -0.05704345181584358, 0.06929459422826767, 0.013339617289602757, -0.026477301493287086, 0.1007043793797493, 0.011091486550867558, -0.022794658318161964, -0.043136175721883774, -0.035925161093473434, -0.021653834730386734, 0.05920710787177086, 0.04779873415827751, 0.023044103756546974, 0.08490107208490372, -0.03656909987330437, 0.019860370084643364, -0.028341177850961685, -0.002615087665617466, -0.020844578742980957, 0.03786735609173775, 0.013601577840745449, -0.0690835490822792, 0.002306619891896844, 0.014626855961978436, -0.05860478803515434, 0.05304853990674019, 0.0210631862282753, -0.03381204232573509, 0.08490485697984695, -0.021656999364495277, -0.026230907067656517, -0.013023956678807735, 0.026644958183169365, -0.006920541170984507, 0.0022428191732615232, 0.010287022218108177, 0.005865653045475483, 0.054995182901620865, -0.0004908764385618269, -0.049247149378061295, 0.0036455276422202587, -0.06764188408851624, -0.018114738166332245, 0.0019920601043850183, 0.05261099711060524, 0.015266765840351582, 0.02861945517361164, 0.06591132283210754, 0.018922867253422737, 0.0808321088552475, 0.022713014855980873, -0.04787297546863556, -0.021220700815320015, -0.015257363207638264, 0.0631396546959877, 0.022089799866080284, -0.045135218650102615, 0.0016985991969704628, -0.0017307768575847149, -0.013725039549171925, 0.02300383895635605, 0.02858244627714157, 0.027713574469089508, -0.04497513547539711, -0.010807839222252369, -0.0005689088138751686, -0.02208631858229637, 0.010738998651504517, -0.020457973703742027, 0.0062552327290177345, -0.008118418976664543, -0.010401858948171139, 0.02946615405380726, -0.022565709426999092, -0.021249422803521156, -0.002396004507318139, 0.03271045535802841, -0.03326736390590668, -0.04666890203952789, 0.006411004811525345, -0.021300725638866425, 0.07643263787031174, -0.008594678714871407, -0.03858562931418419, -0.004771820735186338, -0.05669908598065376, -0.03527238219976425, 0.034821417182683945, 0.015394859947264194, 0.008935380727052689, 0.003926821518689394, -0.07924550026655197, 0.024671422317624092, 0.03546642139554024, -0.060819003731012344, 0.0009726603166200221, -0.006069427356123924, -0.0038421167992055416, 0.0001724377943901345, -0.0020962082780897617, 0.013231690041720867, -0.024662524461746216, -0.010383550077676773, 0.0033337066415697336, -0.006201694719493389, 0.0038142516277730465, 0.032491639256477356, -0.028349796310067177, -0.006959280930459499, 0.019415810704231262, -0.07051411271095276, 0.07964842766523361, -0.01962967962026596, -0.018353372812271118, -0.02979769930243492, 0.005925977602601051, 0.021830657497048378, -0.00649291044101119, 0.00039740066858939826, 0.03224555030465126, -0.062428221106529236, 0.008772051893174648, -0.02437880076467991, -0.06016026437282562, 0.018655987456440926, 0.019988814368844032, 0.020625432953238487, -0.04049528390169144, 0.06219000369310379, -0.008940177969634533, -0.032510481774806976, -0.020898744463920593, 0.06542886793613434, 0.008219041861593723, 0.006392613518983126, -0.021587945520877838, -0.059104468673467636, -0.031420961022377014, 0.03684833273291588, 0.03224372863769531, 0.020564617589116096, 0.043242231011390686, -0.019283603876829147, 0.042374178767204285, -0.021024450659751892, 0.008654273115098476, -0.032648131251335144, 0.021188003942370415, 0.05635427311062813, -0.06458787620067596, -0.04846027493476868, 0.00910431332886219, 0.01107641588896513, 0.0037845447659492493, 0.034955985844135284, 0.017448285594582558, 0.011762850917875767, -0.02987404726445675, -0.06040117144584656, -0.06594642996788025, -0.0631508156657219, 0.055318839848041534, -0.030537614598870277, 0.03246859833598137, -0.07413487881422043, -0.030114291235804558, -0.0014587757177650928, -0.050498105585575104, 0.012630513869225979, -0.040876977145671844, -0.003998949658125639, -0.015539627522230148, 0.012419530190527439, -0.020841114223003387, 0.024615377187728882, 0.060920827090740204, -0.0021354290656745434, -0.009589679539203644, 0.03668854758143425, 0.015315311960875988, -0.03200007975101471, 0.01947806216776371, 0.015535399317741394, 0.020832939073443413, 0.0009696008637547493, 0.005744085181504488, 0.016746096312999725, 0.014648695476353168, -0.02947499230504036, 0.04059843346476555, -0.004542586859315634, -0.007973958738148212, 0.003135488834232092, -0.02053406462073326, -0.017218248918652534, -0.05251000449061394, -0.07307291030883789, 0.022258274257183075, -0.009196942672133446, 0.027808845043182373, 0.02904067188501358, -0.004367210902273655, 0.04121246561408043, 0.005061573814600706, -0.006116786971688271, -0.03674761578440666, 0.05556017532944679, -0.024896636605262756, -0.05013922601938248, -0.030814172700047493, -0.044162649661302567, -0.062292709946632385, -0.00476666959002614, 0.036525826901197433, 0.07863802462816238, -0.04127079248428345, 0.006779748480767012, 0.011375892907381058, 0.0451117604970932, 0.011544778011739254, -0.013557630591094494, 0.005790486000478268, -0.002336176810786128, 0.020907722413539886, -0.016921933740377426, 0.031004132702946663, -0.04633437469601631, 0.04534037411212921, -0.03389233350753784, 0.010420849546790123, -0.0890313908457756, -0.04273815453052521, -0.01057367492467165, 0.05078711360692978, 0.03159687668085098, 0.01779579184949398, 0.04049094393849373, -0.025351176038384438, 0.024667920544743538, 0.043645527213811874, 0.012137873098254204, 0.01148583646863699, -0.009936831891536713, -0.08014784753322601, 0.05653044581413269, -0.022937113419175148, -0.03800298646092415, -0.019486207515001297, 0.03335690498352051, -0.036296501755714417, -0.00939237605780363, -0.009519068524241447, -0.014362206682562828, 0.02882012352347374, -0.0030117493588477373, 0.011293298564851284, 0.04440426826477051, -0.04244352877140045, 0.04045085608959198, -0.009608084335923195, -0.0014369775308296084, -0.011853301897644997, 0.02250063233077526, 0.02013247087597847, -0.03055228479206562, 0.01267393957823515, 0.036434441804885864, 0.024539291858673096, 0.050041742622852325, -0.0454033724963665, -0.07346516102552414, 0.028372399508953094, -0.057826071977615356, 0.015335231088101864, 0.012711949646472931, -0.0006121371989138424, -0.026560060679912567, 0.0012799426913261414, 0.03885176032781601, 0.026761408895254135, 0.05877883732318878, 0.04543119668960571, 0.00772586464881897, 0.009745956398546696, 0.023411206901073456, 0.04102284088730812, -0.0332082137465477, -0.009814807213842869, -0.033480823040008545, -2.577722079877276e-05, 0.030126843601465225, -0.045105114579200745, 0.041004374623298645, 0.0007842665654607117, -0.005297037307173014, 0.04166249930858612, 0.013740862719714642, 0.031283389776945114, -0.047054190188646317, -0.02877264842391014, 0.014451572671532631, -0.008330912329256535, 0.01575607620179653, 0.03836655616760254, 0.028585998341441154, 0.06022465229034424, 0.014461432583630085, -0.03179130330681801, -0.06466642022132874, 0.0034272712655365467, 0.007016490679234266, -0.039520036429166794, 0.01176874153316021, 0.055041804909706116, 0.033385615795850754, -0.027390390634536743, -0.0014993591466918588, -0.008779149502515793, -0.014434798620641232, 0.061815883964300156, -0.004920365288853645, 0.027369704097509384, 0.04413000866770744, 0.013179410248994827, -0.011484737507998943, 0.039524201303720474, 0.0029732936527580023, -0.007710814476013184, -0.037705957889556885, 0.031537484377622604, -0.03127321973443031, 0.06780079752206802, 0.02633778750896454, 0.017419500276446342, 0.0197469349950552, 0.01951937936246395, -0.0045591192319989204, -0.04099363088607788, 0.023796187713742256, 0.006555421743541956, 0.011366328224539757, -0.014717042446136475, 0.02203069068491459, 0.001036526169627905, 0.03396951034665108, 0.04762829467654228, -0.01835354045033455, 0.0145875234156847, -0.030947545543313026, -0.009025374427437782, 0.01380422804504633, 0.00512863602489233, -0.016163822263479233, -0.008085471577942371, 0.012907581403851509, -0.034962475299835205, -0.03494299575686455, -0.08717834204435349, -0.04466240108013153, -0.04784223809838295, -0.06964295357465744, 0.007275538984686136, 0.02197417803108692, 0.016688084229826927, 0.006269244477152824, 0.011667494662106037, -0.030290938913822174, 0.02479977160692215, 0.052434783428907394, -0.0038801429327577353, -0.0033761279191821814, -0.022816507145762444, 0.01698196493089199, 0.03448723256587982, -0.007017314899712801, -0.014474830590188503, 0.013092100620269775, -0.03375625982880592, -0.04335114359855652, 0.0083944546058774, -0.050631266087293625, 0.037903398275375366, 0.03784511238336563, -0.004824098665267229, -0.03681499883532524, 0.02633029595017433, 0.02761826477944851, -0.041753675788640976, 0.044726572930812836, -0.025942586362361908, 0.004498520400375128, -0.016526924446225166, 0.022614790126681328, -0.008134102448821068, -0.05933374911546707, -0.0170682892203331, 0.01950790546834469, 0.021993154659867287, 0.009258713573217392, 0.03577309474349022, -0.006040777079761028, -0.01689918525516987, 0.06474629044532776, -0.02051452361047268, -0.00036078979610465467, -0.03116770274937153, -0.05411141738295555, -0.000868296017870307, -0.021237049251794815, -0.02066796086728573, 0.1410542130470276, 0.013606356456875801, -0.07145093381404877, -0.04837123304605484, 0.08660349249839783, -0.002405100269243121, -0.019075384363532066, -0.019365357235074043, 0.01851011998951435, 0.09412426501512527, -0.04911787062883377, -0.0128995506092906, -0.012053918093442917, 0.018046263605356216, 0.009170940145850182, -0.002959242556244135, 0.017280634492635727, -0.08543619513511658, 0.026256514713168144, 0.011546459048986435, -0.060465261340141296, -0.010382202453911304, -0.025028161704540253, 0.014011220075190067, 0.06226490065455437, 0.009866099804639816, 0.00215950608253479, 0.044206373393535614, -0.025937983766198158, -0.04592662304639816, 0.0696454867720604, -0.04790687933564186, 0.033494751900434494, -0.0342155396938324, 0.018412841483950615, 0.006006625946611166, -0.008958608843386173, -0.039286091923713684, -0.02734021097421646, 0.022405074909329414, 0.0077576590701937675, 0.0069428700953722, -0.009068222716450691, -0.015969447791576385, -0.003446749644353986, 0.018665464594960213, 0.024162519723176956, -0.0059588816948235035, 0.008749212138354778, 0.009875757619738579, -0.03014211170375347, 0.025601701810956, 0.01869679056107998, 0.0246793981641531, 0.019739555194973946, 0.06411167979240417, 0.05066834017634392, -0.014157998375594616, -0.005476726684719324, -0.01567935384809971, -0.02035285159945488, 0.02749427780508995, 0.0036189230158925056, -0.0247687716037035, 0.030312618240714073, 0.0089853061363101, 0.0016174375778064132, 0.056089311838150024, -0.022030271589756012, 0.006874339189380407, -0.00895246583968401, 0.032182205468416214, -0.03530276566743851, -0.019067786633968353, -0.00041821703780442476, 0.01952420547604561, -0.023877020925283432, -0.004116514232009649, -0.017472196370363235, -0.04512961208820343, -0.000665262050461024, -0.014393500983715057, -0.03532331436872482, 0.029158594086766243, 0.002970918081700802, 0.014826922677457333, -0.018131354823708534, -0.025618651881814003, -0.023017656058073044, 0.006374831777065992, -0.034000277519226074, -0.011428195051848888, 0.017366480082273483, 0.011100251227617264, 0.044000230729579926, 0.044098109006881714, 0.016931546851992607, 0.010904215276241302, -0.018336711451411247, 0.02236248552799225, -0.010801452212035656, -0.020552759990096092, -0.015648270025849342, 0.00944614503532648, -0.056049101054668427, 0.06992045789957047, -0.04755287989974022, 0.022811388596892357, -0.01905207894742489, -0.0005521976854652166, -0.0551159493625164, 0.05771920084953308, 0.003313681110739708, -0.012554156593978405, -0.03491245582699776, -0.0004493989108595997, -0.014836834743618965, 0.04550186172127724, 0.020224926993250847, -0.05434810370206833, -0.04117658734321594, 0.04879456013441086, 0.0044229221530258656, 0.00014753938012290746, -0.004815257154405117, 0.026253147050738335, -0.055342838168144226, 0.03325096517801285, -0.032094795256853104, -0.026725497096776962, 0.023136254400014877, 0.011950789950788021, -0.0103463688865304, -0.05655030533671379, -0.046430908143520355, -0.0267023965716362, 0.0395653173327446, 0.05470247194170952, -0.013899288140237331, -0.01553690992295742, -0.0022124205715954304, -0.04116209223866463, 0.008374559693038464, 0.00025515008019283414, -0.03426636382937431, 0.018935082480311394, -0.03281891345977783, 0.008798615075647831, -0.003970039077103138, 0.023412812501192093, 0.01249433308839798, 0.005455314181745052, -0.03127866983413696, -0.014486162923276424, -0.02090301364660263, 0.042937275022268295, 0.01781703159213066, 0.07737474888563156, -0.038432423025369644, 0.04660644009709358, 0.03936861827969551, -0.036005668342113495, -0.007055961061269045, -0.03164416924118996, -0.07419944554567337, 0.0163675956428051, -0.019986335188150406, 0.005489252973347902, -0.012046100571751595, 0.07889817655086517, 0.003632165491580963, 0.03799762949347496, 0.01776469498872757, -0.05217905715107918, -0.016886189579963684, -0.005470234900712967, -0.014474772848188877, 0.028447190299630165, -0.009267609566450119, 0.02553260140120983, 0.00029502619872801006, -0.04289427772164345, -0.07489494979381561, 0.0339854434132576, 0.0716659426689148, -0.048315130174160004, 0.03441132977604866, -0.04454869031906128, -0.054023511707782745, -0.055228911340236664, 0.0653805285692215, -0.06105642765760422, 0.02747117541730404, 0.022343460470438004, 0.054343778640031815, 0.054604314267635345, -0.05817830562591553, -0.01679248735308647, -0.0010837821755558252, 0.014680511318147182, -0.001355848740786314, 0.04336355999112129, -0.023284299299120903, 0.03481322154402733, -0.04792078211903572, 0.10271584987640381, 0.08732537180185318, 0.054378923028707504, -0.01721859723329544, -0.03389263153076172, -0.014271000400185585, 0.04410644993185997, -0.0589648000895977, -0.10395977646112442, -0.00496978173032403, -0.06351707130670547, -0.004880223888903856, -0.01944292150437832, -0.005041536875069141, 0.009868779219686985, -0.021076470613479614, 0.01312626339495182, 0.026089007034897804, -0.03957432508468628, -0.03165239095687866, -0.007891243323683739, 0.03477873653173447, -0.02714000642299652, 0.015237584710121155, 0.02066756784915924, 0.04407768324017525, 0.0550769567489624, 0.030107609927654266, 0.011853663250803947, -0.024173792451620102, 0.014376195147633553, 0.039699945598840714, 0.029913295060396194, -0.08497583121061325, -0.00600552000105381, -0.058703407645225525, 0.006733874324709177, -0.05282263830304146, 0.07921307533979416, -0.019159402698278427, -0.015873195603489876, -0.015008191578090191, 0.022100985050201416, -0.01039169542491436, 0.0033424696885049343, 0.008858509361743927, -0.0025448312517255545, -0.027001190930604935, -0.010651796124875546, 0.052164994180202484, 0.01010804995894432, 0.04327412322163582, 0.03155792877078056, 0.04873507469892502, -0.05584387108683586, -0.01144381333142519, 0.016647186130285263, -0.0056302244774997234, 0.028161536902189255, 0.003070868318900466, -0.06414170563220978, -0.0006059580482542515, -0.0428224615752697, -0.04291451722383499, 0.07868633419275284, 0.04224000126123428, -0.041797857731580734, -0.00715819513425231, 0.013175282627344131, -0.03949834778904915, 0.03971945121884346, 0.038237158209085464, -0.08042848855257034, 0.00833877269178629, -0.005447081755846739, 0.001438029925338924, 0.05658696964383125, -0.031710442155599594, 0.012549635954201221, -0.04449569806456566, -0.013632243499159813, -0.027496619150042534, -0.05011378601193428, 0.07866339385509491, -0.009958427399396896, 0.02002735435962677, -0.004567462485283613, -0.02472861297428608, -0.04544831067323685, -0.006320023909211159, -0.052056245505809784, 0.03617715835571289, -0.036273665726184845, -0.006447257474064827, -0.015921685844659805, -0.012914253398776054, -0.061711035668849945, 0.010351206175982952, 0.06757895648479462, -0.01615845412015915, -0.0064978646114468575, -0.054074425250291824, -0.00034396920818835497, -0.01857716031372547, 0.006079723127186298, -0.012334990315139294, 0.012357001192867756, -0.026382653042674065, 0.11951392143964767, 0.05628421530127525, 0.03174267336726189, 0.03577876463532448, 0.012030803598463535, 0.03710776939988136, -0.01720442809164524, -0.036914411932229996, 0.007174555212259293, -0.062310632318258286], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'group_ids': ['guardkit__task_outcomes']}
WARNING:guardkit.knowledge.graphiti_client:Search request failed: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop
CREATE INDEX FOR (n:Entity) ON (n.uuid, n.group_id, n.name, n.created_at)
{}
ERROR:asyncio:Task exception was never retrieved
future: <Task finished name='Task-2250' coro=<FalkorDriver.build_indices_and_constraints() done, defined at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py:300> exception=RuntimeError('<asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop')>
Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 305, in build_indices_and_constraints
    await self.execute_query(query)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 230, in execute_query
    result = await graph.query(cypher_query_, params)  # type: ignore[reportUnknownArgumentType]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 105, in query
    return await self._query(q, params=params, timeout=timeout, read_only=False)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 79, in _query
    response = await self.execute_command(*command)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/client.py", line 720, in execute_command
    conn = self.connection or await pool.get_connection()
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/connection.py", line 1194, in get_connection
    async with self._lock:
               ^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 14, in __aenter__
    await self.acquire()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 105, in acquire
    fut = self._get_loop().create_future()
          ~~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/mixins.py", line 20, in _get_loop
    raise RuntimeError(f'{self!r} is bound to a different event loop')
RuntimeError: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop
CREATE INDEX FOR (n:Saga) ON (n.uuid, n.group_id, n.name)
{}
ERROR:asyncio:Task exception was never retrieved
future: <Task finished name='Task-2234' coro=<FalkorDriver.build_indices_and_constraints() done, defined at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py:300> exception=RuntimeError('<asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop')>
Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 305, in build_indices_and_constraints
    await self.execute_query(query)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 230, in execute_query
    result = await graph.query(cypher_query_, params)  # type: ignore[reportUnknownArgumentType]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 105, in query
    return await self._query(q, params=params, timeout=timeout, read_only=False)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 79, in _query
    response = await self.execute_command(*command)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/client.py", line 720, in execute_command
    conn = self.connection or await pool.get_connection()
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/connection.py", line 1194, in get_connection
    async with self._lock:
               ^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 14, in __aenter__
    await self.acquire()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 105, in acquire
    fut = self._get_loop().create_future()
          ~~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/mixins.py", line 20, in _get_loop
    raise RuntimeError(f'{self!r} is bound to a different event loop')
RuntimeError: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    WITH rel AS e, score, startNode(rel) AS n, endNode(rel) AS m
     WHERE e.group_id IN $group_ids
            WITH e, score, n, m
            RETURN

        e.uuid AS uuid,
        n.uuid AS source_node_uuid,
        m.uuid AS target_node_uuid,
        e.group_id AS group_id,
        e.created_at AS created_at,
        e.name AS name,
        e.fact AS fact,
        e.episodes AS episodes,
        e.expired_at AS expired_at,
        e.valid_at AS valid_at,
        e.invalid_at AS invalid_at,
    properties(e) AS attributes
            ORDER BY score DESC
            LIMIT $limit

{'query': ' (Task | Exclude | internal | artifacts | from | documentation | constraint | count)', 'limit': 20, 'routing_': 'r', 'group_ids': ['patterns']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop

        MATCH (n:Entity)-[e:RELATES_TO]->(m:Entity)
     WHERE e.group_id IN $group_ids
            WITH DISTINCT e, n, m, (2 - vec.cosineDistance(e.fact_embedding, vecf32($search_vector)))/2 AS score
            WHERE score > $min_score
            RETURN

        e.uuid AS uuid,
        n.uuid AS source_node_uuid,
        m.uuid AS target_node_uuid,
        e.group_id AS group_id,
        e.created_at AS created_at,
        e.name AS name,
        e.fact AS fact,
        e.episodes AS episodes,
        e.expired_at AS expired_at,
        e.valid_at AS valid_at,
        e.invalid_at AS invalid_at,
    properties(e) AS attributes
            ORDER BY score DESC
            LIMIT $limit

{'search_vector': [0.030854303389787674, 0.044420111924409866, -0.15249265730381012, -0.10637671500444412, 0.012100446037948132, -0.04243450611829758, 0.06303342431783676, 0.05075465887784958, -0.047419700771570206, 0.0009705084376037121, 0.009739557281136513, 0.04131072014570236, 0.08332853764295578, -0.005968444515019655, 0.01620110496878624, -0.011293135583400726, -0.023377785459160805, -0.040890589356422424, -0.014678672887384892, 0.01408441923558712, 0.021125677973031998, 0.014033679850399494, 0.008591284044086933, 0.003143634181469679, 0.05504145100712776, 0.06179807707667351, 0.06027386337518692, 0.023254888132214546, -0.07322773337364197, -0.0015845297602936625, 0.01256964635103941, 0.02799363248050213, -0.010015960782766342, -0.02794552408158779, -0.010754699818789959, -0.05704345181584358, 0.06929459422826767, 0.013339617289602757, -0.026477301493287086, 0.1007043793797493, 0.011091486550867558, -0.022794658318161964, -0.043136175721883774, -0.035925161093473434, -0.021653834730386734, 0.05920710787177086, 0.04779873415827751, 0.023044103756546974, 0.08490107208490372, -0.03656909987330437, 0.019860370084643364, -0.028341177850961685, -0.002615087665617466, -0.020844578742980957, 0.03786735609173775, 0.013601577840745449, -0.0690835490822792, 0.002306619891896844, 0.014626855961978436, -0.05860478803515434, 0.05304853990674019, 0.0210631862282753, -0.03381204232573509, 0.08490485697984695, -0.021656999364495277, -0.026230907067656517, -0.013023956678807735, 0.026644958183169365, -0.006920541170984507, 0.0022428191732615232, 0.010287022218108177, 0.005865653045475483, 0.054995182901620865, -0.0004908764385618269, -0.049247149378061295, 0.0036455276422202587, -0.06764188408851624, -0.018114738166332245, 0.0019920601043850183, 0.05261099711060524, 0.015266765840351582, 0.02861945517361164, 0.06591132283210754, 0.018922867253422737, 0.0808321088552475, 0.022713014855980873, -0.04787297546863556, -0.021220700815320015, -0.015257363207638264, 0.0631396546959877, 0.022089799866080284, -0.045135218650102615, 0.0016985991969704628, -0.0017307768575847149, -0.013725039549171925, 0.02300383895635605, 0.02858244627714157, 0.027713574469089508, -0.04497513547539711, -0.010807839222252369, -0.0005689088138751686, -0.02208631858229637, 0.010738998651504517, -0.020457973703742027, 0.0062552327290177345, -0.008118418976664543, -0.010401858948171139, 0.02946615405380726, -0.022565709426999092, -0.021249422803521156, -0.002396004507318139, 0.03271045535802841, -0.03326736390590668, -0.04666890203952789, 0.006411004811525345, -0.021300725638866425, 0.07643263787031174, -0.008594678714871407, -0.03858562931418419, -0.004771820735186338, -0.05669908598065376, -0.03527238219976425, 0.034821417182683945, 0.015394859947264194, 0.008935380727052689, 0.003926821518689394, -0.07924550026655197, 0.024671422317624092, 0.03546642139554024, -0.060819003731012344, 0.0009726603166200221, -0.006069427356123924, -0.0038421167992055416, 0.0001724377943901345, -0.0020962082780897617, 0.013231690041720867, -0.024662524461746216, -0.010383550077676773, 0.0033337066415697336, -0.006201694719493389, 0.0038142516277730465, 0.032491639256477356, -0.028349796310067177, -0.006959280930459499, 0.019415810704231262, -0.07051411271095276, 0.07964842766523361, -0.01962967962026596, -0.018353372812271118, -0.02979769930243492, 0.005925977602601051, 0.021830657497048378, -0.00649291044101119, 0.00039740066858939826, 0.03224555030465126, -0.062428221106529236, 0.008772051893174648, -0.02437880076467991, -0.06016026437282562, 0.018655987456440926, 0.019988814368844032, 0.020625432953238487, -0.04049528390169144, 0.06219000369310379, -0.008940177969634533, -0.032510481774806976, -0.020898744463920593, 0.06542886793613434, 0.008219041861593723, 0.006392613518983126, -0.021587945520877838, -0.059104468673467636, -0.031420961022377014, 0.03684833273291588, 0.03224372863769531, 0.020564617589116096, 0.043242231011390686, -0.019283603876829147, 0.042374178767204285, -0.021024450659751892, 0.008654273115098476, -0.032648131251335144, 0.021188003942370415, 0.05635427311062813, -0.06458787620067596, -0.04846027493476868, 0.00910431332886219, 0.01107641588896513, 0.0037845447659492493, 0.034955985844135284, 0.017448285594582558, 0.011762850917875767, -0.02987404726445675, -0.06040117144584656, -0.06594642996788025, -0.0631508156657219, 0.055318839848041534, -0.030537614598870277, 0.03246859833598137, -0.07413487881422043, -0.030114291235804558, -0.0014587757177650928, -0.050498105585575104, 0.012630513869225979, -0.040876977145671844, -0.003998949658125639, -0.015539627522230148, 0.012419530190527439, -0.020841114223003387, 0.024615377187728882, 0.060920827090740204, -0.0021354290656745434, -0.009589679539203644, 0.03668854758143425, 0.015315311960875988, -0.03200007975101471, 0.01947806216776371, 0.015535399317741394, 0.020832939073443413, 0.0009696008637547493, 0.005744085181504488, 0.016746096312999725, 0.014648695476353168, -0.02947499230504036, 0.04059843346476555, -0.004542586859315634, -0.007973958738148212, 0.003135488834232092, -0.02053406462073326, -0.017218248918652534, -0.05251000449061394, -0.07307291030883789, 0.022258274257183075, -0.009196942672133446, 0.027808845043182373, 0.02904067188501358, -0.004367210902273655, 0.04121246561408043, 0.005061573814600706, -0.006116786971688271, -0.03674761578440666, 0.05556017532944679, -0.024896636605262756, -0.05013922601938248, -0.030814172700047493, -0.044162649661302567, -0.062292709946632385, -0.00476666959002614, 0.036525826901197433, 0.07863802462816238, -0.04127079248428345, 0.006779748480767012, 0.011375892907381058, 0.0451117604970932, 0.011544778011739254, -0.013557630591094494, 0.005790486000478268, -0.002336176810786128, 0.020907722413539886, -0.016921933740377426, 0.031004132702946663, -0.04633437469601631, 0.04534037411212921, -0.03389233350753784, 0.010420849546790123, -0.0890313908457756, -0.04273815453052521, -0.01057367492467165, 0.05078711360692978, 0.03159687668085098, 0.01779579184949398, 0.04049094393849373, -0.025351176038384438, 0.024667920544743538, 0.043645527213811874, 0.012137873098254204, 0.01148583646863699, -0.009936831891536713, -0.08014784753322601, 0.05653044581413269, -0.022937113419175148, -0.03800298646092415, -0.019486207515001297, 0.03335690498352051, -0.036296501755714417, -0.00939237605780363, -0.009519068524241447, -0.014362206682562828, 0.02882012352347374, -0.0030117493588477373, 0.011293298564851284, 0.04440426826477051, -0.04244352877140045, 0.04045085608959198, -0.009608084335923195, -0.0014369775308296084, -0.011853301897644997, 0.02250063233077526, 0.02013247087597847, -0.03055228479206562, 0.01267393957823515, 0.036434441804885864, 0.024539291858673096, 0.050041742622852325, -0.0454033724963665, -0.07346516102552414, 0.028372399508953094, -0.057826071977615356, 0.015335231088101864, 0.012711949646472931, -0.0006121371989138424, -0.026560060679912567, 0.0012799426913261414, 0.03885176032781601, 0.026761408895254135, 0.05877883732318878, 0.04543119668960571, 0.00772586464881897, 0.009745956398546696, 0.023411206901073456, 0.04102284088730812, -0.0332082137465477, -0.009814807213842869, -0.033480823040008545, -2.577722079877276e-05, 0.030126843601465225, -0.045105114579200745, 0.041004374623298645, 0.0007842665654607117, -0.005297037307173014, 0.04166249930858612, 0.013740862719714642, 0.031283389776945114, -0.047054190188646317, -0.02877264842391014, 0.014451572671532631, -0.008330912329256535, 0.01575607620179653, 0.03836655616760254, 0.028585998341441154, 0.06022465229034424, 0.014461432583630085, -0.03179130330681801, -0.06466642022132874, 0.0034272712655365467, 0.007016490679234266, -0.039520036429166794, 0.01176874153316021, 0.055041804909706116, 0.033385615795850754, -0.027390390634536743, -0.0014993591466918588, -0.008779149502515793, -0.014434798620641232, 0.061815883964300156, -0.004920365288853645, 0.027369704097509384, 0.04413000866770744, 0.013179410248994827, -0.011484737507998943, 0.039524201303720474, 0.0029732936527580023, -0.007710814476013184, -0.037705957889556885, 0.031537484377622604, -0.03127321973443031, 0.06780079752206802, 0.02633778750896454, 0.017419500276446342, 0.0197469349950552, 0.01951937936246395, -0.0045591192319989204, -0.04099363088607788, 0.023796187713742256, 0.006555421743541956, 0.011366328224539757, -0.014717042446136475, 0.02203069068491459, 0.001036526169627905, 0.03396951034665108, 0.04762829467654228, -0.01835354045033455, 0.0145875234156847, -0.030947545543313026, -0.009025374427437782, 0.01380422804504633, 0.00512863602489233, -0.016163822263479233, -0.008085471577942371, 0.012907581403851509, -0.034962475299835205, -0.03494299575686455, -0.08717834204435349, -0.04466240108013153, -0.04784223809838295, -0.06964295357465744, 0.007275538984686136, 0.02197417803108692, 0.016688084229826927, 0.006269244477152824, 0.011667494662106037, -0.030290938913822174, 0.02479977160692215, 0.052434783428907394, -0.0038801429327577353, -0.0033761279191821814, -0.022816507145762444, 0.01698196493089199, 0.03448723256587982, -0.007017314899712801, -0.014474830590188503, 0.013092100620269775, -0.03375625982880592, -0.04335114359855652, 0.0083944546058774, -0.050631266087293625, 0.037903398275375366, 0.03784511238336563, -0.004824098665267229, -0.03681499883532524, 0.02633029595017433, 0.02761826477944851, -0.041753675788640976, 0.044726572930812836, -0.025942586362361908, 0.004498520400375128, -0.016526924446225166, 0.022614790126681328, -0.008134102448821068, -0.05933374911546707, -0.0170682892203331, 0.01950790546834469, 0.021993154659867287, 0.009258713573217392, 0.03577309474349022, -0.006040777079761028, -0.01689918525516987, 0.06474629044532776, -0.02051452361047268, -0.00036078979610465467, -0.03116770274937153, -0.05411141738295555, -0.000868296017870307, -0.021237049251794815, -0.02066796086728573, 0.1410542130470276, 0.013606356456875801, -0.07145093381404877, -0.04837123304605484, 0.08660349249839783, -0.002405100269243121, -0.019075384363532066, -0.019365357235074043, 0.01851011998951435, 0.09412426501512527, -0.04911787062883377, -0.0128995506092906, -0.012053918093442917, 0.018046263605356216, 0.009170940145850182, -0.002959242556244135, 0.017280634492635727, -0.08543619513511658, 0.026256514713168144, 0.011546459048986435, -0.060465261340141296, -0.010382202453911304, -0.025028161704540253, 0.014011220075190067, 0.06226490065455437, 0.009866099804639816, 0.00215950608253479, 0.044206373393535614, -0.025937983766198158, -0.04592662304639816, 0.0696454867720604, -0.04790687933564186, 0.033494751900434494, -0.0342155396938324, 0.018412841483950615, 0.006006625946611166, -0.008958608843386173, -0.039286091923713684, -0.02734021097421646, 0.022405074909329414, 0.0077576590701937675, 0.0069428700953722, -0.009068222716450691, -0.015969447791576385, -0.003446749644353986, 0.018665464594960213, 0.024162519723176956, -0.0059588816948235035, 0.008749212138354778, 0.009875757619738579, -0.03014211170375347, 0.025601701810956, 0.01869679056107998, 0.0246793981641531, 0.019739555194973946, 0.06411167979240417, 0.05066834017634392, -0.014157998375594616, -0.005476726684719324, -0.01567935384809971, -0.02035285159945488, 0.02749427780508995, 0.0036189230158925056, -0.0247687716037035, 0.030312618240714073, 0.0089853061363101, 0.0016174375778064132, 0.056089311838150024, -0.022030271589756012, 0.006874339189380407, -0.00895246583968401, 0.032182205468416214, -0.03530276566743851, -0.019067786633968353, -0.00041821703780442476, 0.01952420547604561, -0.023877020925283432, -0.004116514232009649, -0.017472196370363235, -0.04512961208820343, -0.000665262050461024, -0.014393500983715057, -0.03532331436872482, 0.029158594086766243, 0.002970918081700802, 0.014826922677457333, -0.018131354823708534, -0.025618651881814003, -0.023017656058073044, 0.006374831777065992, -0.034000277519226074, -0.011428195051848888, 0.017366480082273483, 0.011100251227617264, 0.044000230729579926, 0.044098109006881714, 0.016931546851992607, 0.010904215276241302, -0.018336711451411247, 0.02236248552799225, -0.010801452212035656, -0.020552759990096092, -0.015648270025849342, 0.00944614503532648, -0.056049101054668427, 0.06992045789957047, -0.04755287989974022, 0.022811388596892357, -0.01905207894742489, -0.0005521976854652166, -0.0551159493625164, 0.05771920084953308, 0.003313681110739708, -0.012554156593978405, -0.03491245582699776, -0.0004493989108595997, -0.014836834743618965, 0.04550186172127724, 0.020224926993250847, -0.05434810370206833, -0.04117658734321594, 0.04879456013441086, 0.0044229221530258656, 0.00014753938012290746, -0.004815257154405117, 0.026253147050738335, -0.055342838168144226, 0.03325096517801285, -0.032094795256853104, -0.026725497096776962, 0.023136254400014877, 0.011950789950788021, -0.0103463688865304, -0.05655030533671379, -0.046430908143520355, -0.0267023965716362, 0.0395653173327446, 0.05470247194170952, -0.013899288140237331, -0.01553690992295742, -0.0022124205715954304, -0.04116209223866463, 0.008374559693038464, 0.00025515008019283414, -0.03426636382937431, 0.018935082480311394, -0.03281891345977783, 0.008798615075647831, -0.003970039077103138, 0.023412812501192093, 0.01249433308839798, 0.005455314181745052, -0.03127866983413696, -0.014486162923276424, -0.02090301364660263, 0.042937275022268295, 0.01781703159213066, 0.07737474888563156, -0.038432423025369644, 0.04660644009709358, 0.03936861827969551, -0.036005668342113495, -0.007055961061269045, -0.03164416924118996, -0.07419944554567337, 0.0163675956428051, -0.019986335188150406, 0.005489252973347902, -0.012046100571751595, 0.07889817655086517, 0.003632165491580963, 0.03799762949347496, 0.01776469498872757, -0.05217905715107918, -0.016886189579963684, -0.005470234900712967, -0.014474772848188877, 0.028447190299630165, -0.009267609566450119, 0.02553260140120983, 0.00029502619872801006, -0.04289427772164345, -0.07489494979381561, 0.0339854434132576, 0.0716659426689148, -0.048315130174160004, 0.03441132977604866, -0.04454869031906128, -0.054023511707782745, -0.055228911340236664, 0.0653805285692215, -0.06105642765760422, 0.02747117541730404, 0.022343460470438004, 0.054343778640031815, 0.054604314267635345, -0.05817830562591553, -0.01679248735308647, -0.0010837821755558252, 0.014680511318147182, -0.001355848740786314, 0.04336355999112129, -0.023284299299120903, 0.03481322154402733, -0.04792078211903572, 0.10271584987640381, 0.08732537180185318, 0.054378923028707504, -0.01721859723329544, -0.03389263153076172, -0.014271000400185585, 0.04410644993185997, -0.0589648000895977, -0.10395977646112442, -0.00496978173032403, -0.06351707130670547, -0.004880223888903856, -0.01944292150437832, -0.005041536875069141, 0.009868779219686985, -0.021076470613479614, 0.01312626339495182, 0.026089007034897804, -0.03957432508468628, -0.03165239095687866, -0.007891243323683739, 0.03477873653173447, -0.02714000642299652, 0.015237584710121155, 0.02066756784915924, 0.04407768324017525, 0.0550769567489624, 0.030107609927654266, 0.011853663250803947, -0.024173792451620102, 0.014376195147633553, 0.039699945598840714, 0.029913295060396194, -0.08497583121061325, -0.00600552000105381, -0.058703407645225525, 0.006733874324709177, -0.05282263830304146, 0.07921307533979416, -0.019159402698278427, -0.015873195603489876, -0.015008191578090191, 0.022100985050201416, -0.01039169542491436, 0.0033424696885049343, 0.008858509361743927, -0.0025448312517255545, -0.027001190930604935, -0.010651796124875546, 0.052164994180202484, 0.01010804995894432, 0.04327412322163582, 0.03155792877078056, 0.04873507469892502, -0.05584387108683586, -0.01144381333142519, 0.016647186130285263, -0.0056302244774997234, 0.028161536902189255, 0.003070868318900466, -0.06414170563220978, -0.0006059580482542515, -0.0428224615752697, -0.04291451722383499, 0.07868633419275284, 0.04224000126123428, -0.041797857731580734, -0.00715819513425231, 0.013175282627344131, -0.03949834778904915, 0.03971945121884346, 0.038237158209085464, -0.08042848855257034, 0.00833877269178629, -0.005447081755846739, 0.001438029925338924, 0.05658696964383125, -0.031710442155599594, 0.012549635954201221, -0.04449569806456566, -0.013632243499159813, -0.027496619150042534, -0.05011378601193428, 0.07866339385509491, -0.009958427399396896, 0.02002735435962677, -0.004567462485283613, -0.02472861297428608, -0.04544831067323685, -0.006320023909211159, -0.052056245505809784, 0.03617715835571289, -0.036273665726184845, -0.006447257474064827, -0.015921685844659805, -0.012914253398776054, -0.061711035668849945, 0.010351206175982952, 0.06757895648479462, -0.01615845412015915, -0.0064978646114468575, -0.054074425250291824, -0.00034396920818835497, -0.01857716031372547, 0.006079723127186298, -0.012334990315139294, 0.012357001192867756, -0.026382653042674065, 0.11951392143964767, 0.05628421530127525, 0.03174267336726189, 0.03577876463532448, 0.012030803598463535, 0.03710776939988136, -0.01720442809164524, -0.036914411932229996, 0.007174555212259293, -0.062310632318258286], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'group_ids': ['patterns']}
WARNING:guardkit.knowledge.graphiti_client:Search request failed: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop
WARNING:guardkit.knowledge.graphiti_client:Graphiti disabled after 3 consecutive failures -- continuing without knowledge graph context
INFO:guardkit.knowledge.turn_state_operations:[TurnState] Loaded from local file: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/turn_state_turn_1.json (454 chars)
INFO:guardkit.knowledge.autobuild_context_loader:[TurnState] Turn continuation loaded: 454 chars for turn 2
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Context loaded in 0.1s
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Player context: 0 categories, 0/7892 tokens
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] SDK timeout: 3600s (CLI override, skipping dynamic calculation)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Mode: task-work (explicit frontmatter override)
INFO:guardkit.orchestrator.agent_invoker:Invoking Player via task-work delegation for TASK-FIX-IA03 (turn 2)
INFO:guardkit.orchestrator.agent_invoker:Ensuring task TASK-FIX-IA03 is in design_approved state
INFO:guardkit.tasks.state_bridge.TASK-FIX-IA03:Ensuring task TASK-FIX-IA03 is in design_approved state
INFO:guardkit.tasks.state_bridge.TASK-FIX-IA03:Transitioning task TASK-FIX-IA03 from backlog to design_approved
INFO:guardkit.tasks.state_bridge.TASK-FIX-IA03:Moved task file: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tasks/backlog/autobuild-observability-fixes/TASK-FIX-IA03-exclude-internal-artifacts-from-doc-constraint.md -> /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tasks/design_approved/TASK-FIX-IA03-exclude-internal-artifacts-from-doc-constraint.md
INFO:guardkit.tasks.state_bridge.TASK-FIX-IA03:Task file moved to: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tasks/design_approved/TASK-FIX-IA03-exclude-internal-artifacts-from-doc-constraint.md
INFO:guardkit.tasks.state_bridge.TASK-FIX-IA03:Task TASK-FIX-IA03 transitioned to design_approved at /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tasks/design_approved/TASK-FIX-IA03-exclude-internal-artifacts-from-doc-constraint.md
INFO:guardkit.orchestrator.agent_invoker:Task TASK-FIX-IA03 state verified: design_approved
INFO:guardkit.orchestrator.agent_invoker:Executing inline implement protocol for TASK-FIX-IA03 (mode=tdd)
INFO:guardkit.orchestrator.agent_invoker:Working directory: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF
INFO:guardkit.orchestrator.agent_invoker:Inline protocol size: 19269 bytes (variant=full, multiplier=1.0x)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Max turns: 150 (base=100, complexity=3 x1.3, floored from 130 to 150)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Harness invocation starting
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Working directory: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Allowed tools: ['Read', 'Write', 'Edit', 'Bash', 'Grep', 'Glob', 'Task']
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Permission mode: acceptEdits
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Max turns: 150
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] SDK timeout: 3600s
INFO:openai._base_client:Retrying request to /responses in 0.410216 seconds
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] task-work implementation in progress... (30s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] task-work implementation in progress... (60s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] task-work implementation in progress... (90s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] task-work implementation in progress... (120s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] task-work implementation in progress... (150s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] task-work implementation in progress... (180s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] task-work implementation in progress... (210s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] SDK completed: turns=None
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Message summary: total=25, assistant=1, tools=0, results=1
INFO:guardkit.orchestrator.agent_invoker:BDD oracle invoking run_bdd_for_task for TASK-FIX-IA03 with python_executable=/Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.venv/bin/python3
INFO:guardkit.orchestrator.agent_invoker:Wrote task_work_results.json to /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/task_work_results.json
INFO:guardkit.orchestrator.agent_invoker:task-work completed successfully for TASK-FIX-IA03
INFO:guardkit.orchestrator.agent_invoker:Created Player report from task_work_results.json for TASK-FIX-IA03 turn 2
INFO:guardkit.orchestrator.agent_invoker:Git detection added: 71 modified, 0 created files for TASK-FIX-IA03
INFO:guardkit.orchestrator.agent_invoker:Recovered 5 completion_promises from agent-written player report for TASK-FIX-IA03
INFO:guardkit.orchestrator.agent_invoker:Recovered 5 requirements_addressed from agent-written player report for TASK-FIX-IA03
INFO:guardkit.orchestrator.agent_invoker:Filtered 4 orchestrator-induced ghost path(s) for TASK-FIX-IA03: ['.guardkit/bootstrap_state.json', 'tasks/backlog/TASK-FIX-GD02-shared-worktree-git-detection-baseline.md', 'tasks/backlog/TASK-FIX-TP05-add-test-execution-for-testing-task-type.md', 'tasks/design_approved/TASK-FIX-IA03-exclude-internal-artifacts-from-doc-constraint.md']
INFO:guardkit.orchestrator.agent_invoker:Written Player report to /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/player_turn_2.json
INFO:guardkit.orchestrator.agent_invoker:Updated task_work_results.json with enriched data for TASK-FIX-IA03
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] SDK invocation complete: 212.1s, 0 SDK turns (212.1s/turn avg)
  ✓ [2026-06-08T14:32:12.561Z] 0 files created, 67 modified, 0 tests (failing)
  [2026-06-08T14:28:40.178Z] Turn 2/5: Player Implementation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
INFO:guardkit.orchestrator.progress:[2026-06-08T14:32:12.561Z] Completed turn 2: success - 0 files created, 67 modified, 0 tests (failing)
   Context: retrieved (0 categories, 0/7892 tokens)
INFO:guardkit.orchestrator.autobuild:Carried forward 5 requirements from previous turns
INFO:guardkit.orchestrator.autobuild:Cumulative requirements_addressed: 10 criteria (current turn: 5, carried: 5)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Mode: task-work (explicit frontmatter override)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] SDK timeout: 3600s (CLI override, skipping dynamic calculation)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] specialist:test-orchestrator invocation in progress... (30s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] specialist:test-orchestrator invocation in progress... (60s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] specialist:test-orchestrator invocation in progress... (90s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] specialist:test-orchestrator invocation in progress... (120s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] specialist:test-orchestrator invocation in progress... (150s elapsed)
WARNING:guardkit.orchestrator.specialist_invocations:[TASK-FIX-IA03] run_specialist(test-orchestrator): hang detected (no model activity for 150s) — terminating before the 600s duration cap
INFO:guardkit.orchestrator.agent_invoker:Extracted partial data from 0 events: 0 text blocks, 0 tool calls, 0 file mods
WARNING:guardkit.orchestrator.specialist_invocations:run_specialist(test-orchestrator) failed for TASK-FIX-IA03: hang detected (no model activity for 150s)
INFO:guardkit.orchestrator.agent_invoker:Injected orchestrator specialist records into /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/task_work_results.json (merged=2, validation=violation)
INFO:guardkit.orchestrator.progress:[2026-06-08T14:34:42.646Z] Started turn 2: Coach Validation
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Loading Coach context (turn 2)...
INFO:guardkit.knowledge.graphiti_client:Circuit breaker reset after 362s (half-open)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Task <Task pending name='Task-2609' coro=<semaphore_gather.<locals>._wrap_coroutine() running at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/helpers.py:131> cb=[gather.<locals>._done_callback() at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/tasks.py:810]> got Future <Future pending> attached to a different loop

        MATCH (n:Entity)-[e:RELATES_TO]->(m:Entity)
     WHERE e.group_id IN $group_ids
            WITH DISTINCT e, n, m, (2 - vec.cosineDistance(e.fact_embedding, vecf32($search_vector)))/2 AS score
            WHERE score > $min_score
            RETURN

        e.uuid AS uuid,
        n.uuid AS source_node_uuid,
        m.uuid AS target_node_uuid,
        e.group_id AS group_id,
        e.created_at AS created_at,
        e.name AS name,
        e.fact AS fact,
        e.episodes AS episodes,
        e.expired_at AS expired_at,
        e.valid_at AS valid_at,
        e.invalid_at AS invalid_at,
    properties(e) AS attributes
            ORDER BY score DESC
            LIMIT $limit

{'search_vector': [0.030854303389787674, 0.044420111924409866, -0.15249265730381012, -0.10637671500444412, 0.012100446037948132, -0.04243450611829758, 0.06303342431783676, 0.05075465887784958, -0.047419700771570206, 0.0009705084376037121, 0.009739557281136513, 0.04131072014570236, 0.08332853764295578, -0.005968444515019655, 0.01620110496878624, -0.011293135583400726, -0.023377785459160805, -0.040890589356422424, -0.014678672887384892, 0.01408441923558712, 0.021125677973031998, 0.014033679850399494, 0.008591284044086933, 0.003143634181469679, 0.05504145100712776, 0.06179807707667351, 0.06027386337518692, 0.023254888132214546, -0.07322773337364197, -0.0015845297602936625, 0.01256964635103941, 0.02799363248050213, -0.010015960782766342, -0.02794552408158779, -0.010754699818789959, -0.05704345181584358, 0.06929459422826767, 0.013339617289602757, -0.026477301493287086, 0.1007043793797493, 0.011091486550867558, -0.022794658318161964, -0.043136175721883774, -0.035925161093473434, -0.021653834730386734, 0.05920710787177086, 0.04779873415827751, 0.023044103756546974, 0.08490107208490372, -0.03656909987330437, 0.019860370084643364, -0.028341177850961685, -0.002615087665617466, -0.020844578742980957, 0.03786735609173775, 0.013601577840745449, -0.0690835490822792, 0.002306619891896844, 0.014626855961978436, -0.05860478803515434, 0.05304853990674019, 0.0210631862282753, -0.03381204232573509, 0.08490485697984695, -0.021656999364495277, -0.026230907067656517, -0.013023956678807735, 0.026644958183169365, -0.006920541170984507, 0.0022428191732615232, 0.010287022218108177, 0.005865653045475483, 0.054995182901620865, -0.0004908764385618269, -0.049247149378061295, 0.0036455276422202587, -0.06764188408851624, -0.018114738166332245, 0.0019920601043850183, 0.05261099711060524, 0.015266765840351582, 0.02861945517361164, 0.06591132283210754, 0.018922867253422737, 0.0808321088552475, 0.022713014855980873, -0.04787297546863556, -0.021220700815320015, -0.015257363207638264, 0.0631396546959877, 0.022089799866080284, -0.045135218650102615, 0.0016985991969704628, -0.0017307768575847149, -0.013725039549171925, 0.02300383895635605, 0.02858244627714157, 0.027713574469089508, -0.04497513547539711, -0.010807839222252369, -0.0005689088138751686, -0.02208631858229637, 0.010738998651504517, -0.020457973703742027, 0.0062552327290177345, -0.008118418976664543, -0.010401858948171139, 0.02946615405380726, -0.022565709426999092, -0.021249422803521156, -0.002396004507318139, 0.03271045535802841, -0.03326736390590668, -0.04666890203952789, 0.006411004811525345, -0.021300725638866425, 0.07643263787031174, -0.008594678714871407, -0.03858562931418419, -0.004771820735186338, -0.05669908598065376, -0.03527238219976425, 0.034821417182683945, 0.015394859947264194, 0.008935380727052689, 0.003926821518689394, -0.07924550026655197, 0.024671422317624092, 0.03546642139554024, -0.060819003731012344, 0.0009726603166200221, -0.006069427356123924, -0.0038421167992055416, 0.0001724377943901345, -0.0020962082780897617, 0.013231690041720867, -0.024662524461746216, -0.010383550077676773, 0.0033337066415697336, -0.006201694719493389, 0.0038142516277730465, 0.032491639256477356, -0.028349796310067177, -0.006959280930459499, 0.019415810704231262, -0.07051411271095276, 0.07964842766523361, -0.01962967962026596, -0.018353372812271118, -0.02979769930243492, 0.005925977602601051, 0.021830657497048378, -0.00649291044101119, 0.00039740066858939826, 0.03224555030465126, -0.062428221106529236, 0.008772051893174648, -0.02437880076467991, -0.06016026437282562, 0.018655987456440926, 0.019988814368844032, 0.020625432953238487, -0.04049528390169144, 0.06219000369310379, -0.008940177969634533, -0.032510481774806976, -0.020898744463920593, 0.06542886793613434, 0.008219041861593723, 0.006392613518983126, -0.021587945520877838, -0.059104468673467636, -0.031420961022377014, 0.03684833273291588, 0.03224372863769531, 0.020564617589116096, 0.043242231011390686, -0.019283603876829147, 0.042374178767204285, -0.021024450659751892, 0.008654273115098476, -0.032648131251335144, 0.021188003942370415, 0.05635427311062813, -0.06458787620067596, -0.04846027493476868, 0.00910431332886219, 0.01107641588896513, 0.0037845447659492493, 0.034955985844135284, 0.017448285594582558, 0.011762850917875767, -0.02987404726445675, -0.06040117144584656, -0.06594642996788025, -0.0631508156657219, 0.055318839848041534, -0.030537614598870277, 0.03246859833598137, -0.07413487881422043, -0.030114291235804558, -0.0014587757177650928, -0.050498105585575104, 0.012630513869225979, -0.040876977145671844, -0.003998949658125639, -0.015539627522230148, 0.012419530190527439, -0.020841114223003387, 0.024615377187728882, 0.060920827090740204, -0.0021354290656745434, -0.009589679539203644, 0.03668854758143425, 0.015315311960875988, -0.03200007975101471, 0.01947806216776371, 0.015535399317741394, 0.020832939073443413, 0.0009696008637547493, 0.005744085181504488, 0.016746096312999725, 0.014648695476353168, -0.02947499230504036, 0.04059843346476555, -0.004542586859315634, -0.007973958738148212, 0.003135488834232092, -0.02053406462073326, -0.017218248918652534, -0.05251000449061394, -0.07307291030883789, 0.022258274257183075, -0.009196942672133446, 0.027808845043182373, 0.02904067188501358, -0.004367210902273655, 0.04121246561408043, 0.005061573814600706, -0.006116786971688271, -0.03674761578440666, 0.05556017532944679, -0.024896636605262756, -0.05013922601938248, -0.030814172700047493, -0.044162649661302567, -0.062292709946632385, -0.00476666959002614, 0.036525826901197433, 0.07863802462816238, -0.04127079248428345, 0.006779748480767012, 0.011375892907381058, 0.0451117604970932, 0.011544778011739254, -0.013557630591094494, 0.005790486000478268, -0.002336176810786128, 0.020907722413539886, -0.016921933740377426, 0.031004132702946663, -0.04633437469601631, 0.04534037411212921, -0.03389233350753784, 0.010420849546790123, -0.0890313908457756, -0.04273815453052521, -0.01057367492467165, 0.05078711360692978, 0.03159687668085098, 0.01779579184949398, 0.04049094393849373, -0.025351176038384438, 0.024667920544743538, 0.043645527213811874, 0.012137873098254204, 0.01148583646863699, -0.009936831891536713, -0.08014784753322601, 0.05653044581413269, -0.022937113419175148, -0.03800298646092415, -0.019486207515001297, 0.03335690498352051, -0.036296501755714417, -0.00939237605780363, -0.009519068524241447, -0.014362206682562828, 0.02882012352347374, -0.0030117493588477373, 0.011293298564851284, 0.04440426826477051, -0.04244352877140045, 0.04045085608959198, -0.009608084335923195, -0.0014369775308296084, -0.011853301897644997, 0.02250063233077526, 0.02013247087597847, -0.03055228479206562, 0.01267393957823515, 0.036434441804885864, 0.024539291858673096, 0.050041742622852325, -0.0454033724963665, -0.07346516102552414, 0.028372399508953094, -0.057826071977615356, 0.015335231088101864, 0.012711949646472931, -0.0006121371989138424, -0.026560060679912567, 0.0012799426913261414, 0.03885176032781601, 0.026761408895254135, 0.05877883732318878, 0.04543119668960571, 0.00772586464881897, 0.009745956398546696, 0.023411206901073456, 0.04102284088730812, -0.0332082137465477, -0.009814807213842869, -0.033480823040008545, -2.577722079877276e-05, 0.030126843601465225, -0.045105114579200745, 0.041004374623298645, 0.0007842665654607117, -0.005297037307173014, 0.04166249930858612, 0.013740862719714642, 0.031283389776945114, -0.047054190188646317, -0.02877264842391014, 0.014451572671532631, -0.008330912329256535, 0.01575607620179653, 0.03836655616760254, 0.028585998341441154, 0.06022465229034424, 0.014461432583630085, -0.03179130330681801, -0.06466642022132874, 0.0034272712655365467, 0.007016490679234266, -0.039520036429166794, 0.01176874153316021, 0.055041804909706116, 0.033385615795850754, -0.027390390634536743, -0.0014993591466918588, -0.008779149502515793, -0.014434798620641232, 0.061815883964300156, -0.004920365288853645, 0.027369704097509384, 0.04413000866770744, 0.013179410248994827, -0.011484737507998943, 0.039524201303720474, 0.0029732936527580023, -0.007710814476013184, -0.037705957889556885, 0.031537484377622604, -0.03127321973443031, 0.06780079752206802, 0.02633778750896454, 0.017419500276446342, 0.0197469349950552, 0.01951937936246395, -0.0045591192319989204, -0.04099363088607788, 0.023796187713742256, 0.006555421743541956, 0.011366328224539757, -0.014717042446136475, 0.02203069068491459, 0.001036526169627905, 0.03396951034665108, 0.04762829467654228, -0.01835354045033455, 0.0145875234156847, -0.030947545543313026, -0.009025374427437782, 0.01380422804504633, 0.00512863602489233, -0.016163822263479233, -0.008085471577942371, 0.012907581403851509, -0.034962475299835205, -0.03494299575686455, -0.08717834204435349, -0.04466240108013153, -0.04784223809838295, -0.06964295357465744, 0.007275538984686136, 0.02197417803108692, 0.016688084229826927, 0.006269244477152824, 0.011667494662106037, -0.030290938913822174, 0.02479977160692215, 0.052434783428907394, -0.0038801429327577353, -0.0033761279191821814, -0.022816507145762444, 0.01698196493089199, 0.03448723256587982, -0.007017314899712801, -0.014474830590188503, 0.013092100620269775, -0.03375625982880592, -0.04335114359855652, 0.0083944546058774, -0.050631266087293625, 0.037903398275375366, 0.03784511238336563, -0.004824098665267229, -0.03681499883532524, 0.02633029595017433, 0.02761826477944851, -0.041753675788640976, 0.044726572930812836, -0.025942586362361908, 0.004498520400375128, -0.016526924446225166, 0.022614790126681328, -0.008134102448821068, -0.05933374911546707, -0.0170682892203331, 0.01950790546834469, 0.021993154659867287, 0.009258713573217392, 0.03577309474349022, -0.006040777079761028, -0.01689918525516987, 0.06474629044532776, -0.02051452361047268, -0.00036078979610465467, -0.03116770274937153, -0.05411141738295555, -0.000868296017870307, -0.021237049251794815, -0.02066796086728573, 0.1410542130470276, 0.013606356456875801, -0.07145093381404877, -0.04837123304605484, 0.08660349249839783, -0.002405100269243121, -0.019075384363532066, -0.019365357235074043, 0.01851011998951435, 0.09412426501512527, -0.04911787062883377, -0.0128995506092906, -0.012053918093442917, 0.018046263605356216, 0.009170940145850182, -0.002959242556244135, 0.017280634492635727, -0.08543619513511658, 0.026256514713168144, 0.011546459048986435, -0.060465261340141296, -0.010382202453911304, -0.025028161704540253, 0.014011220075190067, 0.06226490065455437, 0.009866099804639816, 0.00215950608253479, 0.044206373393535614, -0.025937983766198158, -0.04592662304639816, 0.0696454867720604, -0.04790687933564186, 0.033494751900434494, -0.0342155396938324, 0.018412841483950615, 0.006006625946611166, -0.008958608843386173, -0.039286091923713684, -0.02734021097421646, 0.022405074909329414, 0.0077576590701937675, 0.0069428700953722, -0.009068222716450691, -0.015969447791576385, -0.003446749644353986, 0.018665464594960213, 0.024162519723176956, -0.0059588816948235035, 0.008749212138354778, 0.009875757619738579, -0.03014211170375347, 0.025601701810956, 0.01869679056107998, 0.0246793981641531, 0.019739555194973946, 0.06411167979240417, 0.05066834017634392, -0.014157998375594616, -0.005476726684719324, -0.01567935384809971, -0.02035285159945488, 0.02749427780508995, 0.0036189230158925056, -0.0247687716037035, 0.030312618240714073, 0.0089853061363101, 0.0016174375778064132, 0.056089311838150024, -0.022030271589756012, 0.006874339189380407, -0.00895246583968401, 0.032182205468416214, -0.03530276566743851, -0.019067786633968353, -0.00041821703780442476, 0.01952420547604561, -0.023877020925283432, -0.004116514232009649, -0.017472196370363235, -0.04512961208820343, -0.000665262050461024, -0.014393500983715057, -0.03532331436872482, 0.029158594086766243, 0.002970918081700802, 0.014826922677457333, -0.018131354823708534, -0.025618651881814003, -0.023017656058073044, 0.006374831777065992, -0.034000277519226074, -0.011428195051848888, 0.017366480082273483, 0.011100251227617264, 0.044000230729579926, 0.044098109006881714, 0.016931546851992607, 0.010904215276241302, -0.018336711451411247, 0.02236248552799225, -0.010801452212035656, -0.020552759990096092, -0.015648270025849342, 0.00944614503532648, -0.056049101054668427, 0.06992045789957047, -0.04755287989974022, 0.022811388596892357, -0.01905207894742489, -0.0005521976854652166, -0.0551159493625164, 0.05771920084953308, 0.003313681110739708, -0.012554156593978405, -0.03491245582699776, -0.0004493989108595997, -0.014836834743618965, 0.04550186172127724, 0.020224926993250847, -0.05434810370206833, -0.04117658734321594, 0.04879456013441086, 0.0044229221530258656, 0.00014753938012290746, -0.004815257154405117, 0.026253147050738335, -0.055342838168144226, 0.03325096517801285, -0.032094795256853104, -0.026725497096776962, 0.023136254400014877, 0.011950789950788021, -0.0103463688865304, -0.05655030533671379, -0.046430908143520355, -0.0267023965716362, 0.0395653173327446, 0.05470247194170952, -0.013899288140237331, -0.01553690992295742, -0.0022124205715954304, -0.04116209223866463, 0.008374559693038464, 0.00025515008019283414, -0.03426636382937431, 0.018935082480311394, -0.03281891345977783, 0.008798615075647831, -0.003970039077103138, 0.023412812501192093, 0.01249433308839798, 0.005455314181745052, -0.03127866983413696, -0.014486162923276424, -0.02090301364660263, 0.042937275022268295, 0.01781703159213066, 0.07737474888563156, -0.038432423025369644, 0.04660644009709358, 0.03936861827969551, -0.036005668342113495, -0.007055961061269045, -0.03164416924118996, -0.07419944554567337, 0.0163675956428051, -0.019986335188150406, 0.005489252973347902, -0.012046100571751595, 0.07889817655086517, 0.003632165491580963, 0.03799762949347496, 0.01776469498872757, -0.05217905715107918, -0.016886189579963684, -0.005470234900712967, -0.014474772848188877, 0.028447190299630165, -0.009267609566450119, 0.02553260140120983, 0.00029502619872801006, -0.04289427772164345, -0.07489494979381561, 0.0339854434132576, 0.0716659426689148, -0.048315130174160004, 0.03441132977604866, -0.04454869031906128, -0.054023511707782745, -0.055228911340236664, 0.0653805285692215, -0.06105642765760422, 0.02747117541730404, 0.022343460470438004, 0.054343778640031815, 0.054604314267635345, -0.05817830562591553, -0.01679248735308647, -0.0010837821755558252, 0.014680511318147182, -0.001355848740786314, 0.04336355999112129, -0.023284299299120903, 0.03481322154402733, -0.04792078211903572, 0.10271584987640381, 0.08732537180185318, 0.054378923028707504, -0.01721859723329544, -0.03389263153076172, -0.014271000400185585, 0.04410644993185997, -0.0589648000895977, -0.10395977646112442, -0.00496978173032403, -0.06351707130670547, -0.004880223888903856, -0.01944292150437832, -0.005041536875069141, 0.009868779219686985, -0.021076470613479614, 0.01312626339495182, 0.026089007034897804, -0.03957432508468628, -0.03165239095687866, -0.007891243323683739, 0.03477873653173447, -0.02714000642299652, 0.015237584710121155, 0.02066756784915924, 0.04407768324017525, 0.0550769567489624, 0.030107609927654266, 0.011853663250803947, -0.024173792451620102, 0.014376195147633553, 0.039699945598840714, 0.029913295060396194, -0.08497583121061325, -0.00600552000105381, -0.058703407645225525, 0.006733874324709177, -0.05282263830304146, 0.07921307533979416, -0.019159402698278427, -0.015873195603489876, -0.015008191578090191, 0.022100985050201416, -0.01039169542491436, 0.0033424696885049343, 0.008858509361743927, -0.0025448312517255545, -0.027001190930604935, -0.010651796124875546, 0.052164994180202484, 0.01010804995894432, 0.04327412322163582, 0.03155792877078056, 0.04873507469892502, -0.05584387108683586, -0.01144381333142519, 0.016647186130285263, -0.0056302244774997234, 0.028161536902189255, 0.003070868318900466, -0.06414170563220978, -0.0006059580482542515, -0.0428224615752697, -0.04291451722383499, 0.07868633419275284, 0.04224000126123428, -0.041797857731580734, -0.00715819513425231, 0.013175282627344131, -0.03949834778904915, 0.03971945121884346, 0.038237158209085464, -0.08042848855257034, 0.00833877269178629, -0.005447081755846739, 0.001438029925338924, 0.05658696964383125, -0.031710442155599594, 0.012549635954201221, -0.04449569806456566, -0.013632243499159813, -0.027496619150042534, -0.05011378601193428, 0.07866339385509491, -0.009958427399396896, 0.02002735435962677, -0.004567462485283613, -0.02472861297428608, -0.04544831067323685, -0.006320023909211159, -0.052056245505809784, 0.03617715835571289, -0.036273665726184845, -0.006447257474064827, -0.015921685844659805, -0.012914253398776054, -0.061711035668849945, 0.010351206175982952, 0.06757895648479462, -0.01615845412015915, -0.0064978646114468575, -0.054074425250291824, -0.00034396920818835497, -0.01857716031372547, 0.006079723127186298, -0.012334990315139294, 0.012357001192867756, -0.026382653042674065, 0.11951392143964767, 0.05628421530127525, 0.03174267336726189, 0.03577876463532448, 0.012030803598463535, 0.03710776939988136, -0.01720442809164524, -0.036914411932229996, 0.007174555212259293, -0.062310632318258286], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'group_ids': ['guardkit__feature_specs']}
WARNING:guardkit.knowledge.graphiti_client:Search request failed: Task <Task pending name='Task-2609' coro=<semaphore_gather.<locals>._wrap_coroutine() running at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/helpers.py:131> cb=[gather.<locals>._done_callback() at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/tasks.py:810]> got Future <Future pending> attached to a different loop
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop

        MATCH (n:Entity)-[e:RELATES_TO]->(m:Entity)
     WHERE e.group_id IN $group_ids
            WITH DISTINCT e, n, m, (2 - vec.cosineDistance(e.fact_embedding, vecf32($search_vector)))/2 AS score
            WHERE score > $min_score
            RETURN

        e.uuid AS uuid,
        n.uuid AS source_node_uuid,
        m.uuid AS target_node_uuid,
        e.group_id AS group_id,
        e.created_at AS created_at,
        e.name AS name,
        e.fact AS fact,
        e.episodes AS episodes,
        e.expired_at AS expired_at,
        e.valid_at AS valid_at,
        e.invalid_at AS invalid_at,
    properties(e) AS attributes
            ORDER BY score DESC
            LIMIT $limit

{'search_vector': [0.030854303389787674, 0.044420111924409866, -0.15249265730381012, -0.10637671500444412, 0.012100446037948132, -0.04243450611829758, 0.06303342431783676, 0.05075465887784958, -0.047419700771570206, 0.0009705084376037121, 0.009739557281136513, 0.04131072014570236, 0.08332853764295578, -0.005968444515019655, 0.01620110496878624, -0.011293135583400726, -0.023377785459160805, -0.040890589356422424, -0.014678672887384892, 0.01408441923558712, 0.021125677973031998, 0.014033679850399494, 0.008591284044086933, 0.003143634181469679, 0.05504145100712776, 0.06179807707667351, 0.06027386337518692, 0.023254888132214546, -0.07322773337364197, -0.0015845297602936625, 0.01256964635103941, 0.02799363248050213, -0.010015960782766342, -0.02794552408158779, -0.010754699818789959, -0.05704345181584358, 0.06929459422826767, 0.013339617289602757, -0.026477301493287086, 0.1007043793797493, 0.011091486550867558, -0.022794658318161964, -0.043136175721883774, -0.035925161093473434, -0.021653834730386734, 0.05920710787177086, 0.04779873415827751, 0.023044103756546974, 0.08490107208490372, -0.03656909987330437, 0.019860370084643364, -0.028341177850961685, -0.002615087665617466, -0.020844578742980957, 0.03786735609173775, 0.013601577840745449, -0.0690835490822792, 0.002306619891896844, 0.014626855961978436, -0.05860478803515434, 0.05304853990674019, 0.0210631862282753, -0.03381204232573509, 0.08490485697984695, -0.021656999364495277, -0.026230907067656517, -0.013023956678807735, 0.026644958183169365, -0.006920541170984507, 0.0022428191732615232, 0.010287022218108177, 0.005865653045475483, 0.054995182901620865, -0.0004908764385618269, -0.049247149378061295, 0.0036455276422202587, -0.06764188408851624, -0.018114738166332245, 0.0019920601043850183, 0.05261099711060524, 0.015266765840351582, 0.02861945517361164, 0.06591132283210754, 0.018922867253422737, 0.0808321088552475, 0.022713014855980873, -0.04787297546863556, -0.021220700815320015, -0.015257363207638264, 0.0631396546959877, 0.022089799866080284, -0.045135218650102615, 0.0016985991969704628, -0.0017307768575847149, -0.013725039549171925, 0.02300383895635605, 0.02858244627714157, 0.027713574469089508, -0.04497513547539711, -0.010807839222252369, -0.0005689088138751686, -0.02208631858229637, 0.010738998651504517, -0.020457973703742027, 0.0062552327290177345, -0.008118418976664543, -0.010401858948171139, 0.02946615405380726, -0.022565709426999092, -0.021249422803521156, -0.002396004507318139, 0.03271045535802841, -0.03326736390590668, -0.04666890203952789, 0.006411004811525345, -0.021300725638866425, 0.07643263787031174, -0.008594678714871407, -0.03858562931418419, -0.004771820735186338, -0.05669908598065376, -0.03527238219976425, 0.034821417182683945, 0.015394859947264194, 0.008935380727052689, 0.003926821518689394, -0.07924550026655197, 0.024671422317624092, 0.03546642139554024, -0.060819003731012344, 0.0009726603166200221, -0.006069427356123924, -0.0038421167992055416, 0.0001724377943901345, -0.0020962082780897617, 0.013231690041720867, -0.024662524461746216, -0.010383550077676773, 0.0033337066415697336, -0.006201694719493389, 0.0038142516277730465, 0.032491639256477356, -0.028349796310067177, -0.006959280930459499, 0.019415810704231262, -0.07051411271095276, 0.07964842766523361, -0.01962967962026596, -0.018353372812271118, -0.02979769930243492, 0.005925977602601051, 0.021830657497048378, -0.00649291044101119, 0.00039740066858939826, 0.03224555030465126, -0.062428221106529236, 0.008772051893174648, -0.02437880076467991, -0.06016026437282562, 0.018655987456440926, 0.019988814368844032, 0.020625432953238487, -0.04049528390169144, 0.06219000369310379, -0.008940177969634533, -0.032510481774806976, -0.020898744463920593, 0.06542886793613434, 0.008219041861593723, 0.006392613518983126, -0.021587945520877838, -0.059104468673467636, -0.031420961022377014, 0.03684833273291588, 0.03224372863769531, 0.020564617589116096, 0.043242231011390686, -0.019283603876829147, 0.042374178767204285, -0.021024450659751892, 0.008654273115098476, -0.032648131251335144, 0.021188003942370415, 0.05635427311062813, -0.06458787620067596, -0.04846027493476868, 0.00910431332886219, 0.01107641588896513, 0.0037845447659492493, 0.034955985844135284, 0.017448285594582558, 0.011762850917875767, -0.02987404726445675, -0.06040117144584656, -0.06594642996788025, -0.0631508156657219, 0.055318839848041534, -0.030537614598870277, 0.03246859833598137, -0.07413487881422043, -0.030114291235804558, -0.0014587757177650928, -0.050498105585575104, 0.012630513869225979, -0.040876977145671844, -0.003998949658125639, -0.015539627522230148, 0.012419530190527439, -0.020841114223003387, 0.024615377187728882, 0.060920827090740204, -0.0021354290656745434, -0.009589679539203644, 0.03668854758143425, 0.015315311960875988, -0.03200007975101471, 0.01947806216776371, 0.015535399317741394, 0.020832939073443413, 0.0009696008637547493, 0.005744085181504488, 0.016746096312999725, 0.014648695476353168, -0.02947499230504036, 0.04059843346476555, -0.004542586859315634, -0.007973958738148212, 0.003135488834232092, -0.02053406462073326, -0.017218248918652534, -0.05251000449061394, -0.07307291030883789, 0.022258274257183075, -0.009196942672133446, 0.027808845043182373, 0.02904067188501358, -0.004367210902273655, 0.04121246561408043, 0.005061573814600706, -0.006116786971688271, -0.03674761578440666, 0.05556017532944679, -0.024896636605262756, -0.05013922601938248, -0.030814172700047493, -0.044162649661302567, -0.062292709946632385, -0.00476666959002614, 0.036525826901197433, 0.07863802462816238, -0.04127079248428345, 0.006779748480767012, 0.011375892907381058, 0.0451117604970932, 0.011544778011739254, -0.013557630591094494, 0.005790486000478268, -0.002336176810786128, 0.020907722413539886, -0.016921933740377426, 0.031004132702946663, -0.04633437469601631, 0.04534037411212921, -0.03389233350753784, 0.010420849546790123, -0.0890313908457756, -0.04273815453052521, -0.01057367492467165, 0.05078711360692978, 0.03159687668085098, 0.01779579184949398, 0.04049094393849373, -0.025351176038384438, 0.024667920544743538, 0.043645527213811874, 0.012137873098254204, 0.01148583646863699, -0.009936831891536713, -0.08014784753322601, 0.05653044581413269, -0.022937113419175148, -0.03800298646092415, -0.019486207515001297, 0.03335690498352051, -0.036296501755714417, -0.00939237605780363, -0.009519068524241447, -0.014362206682562828, 0.02882012352347374, -0.0030117493588477373, 0.011293298564851284, 0.04440426826477051, -0.04244352877140045, 0.04045085608959198, -0.009608084335923195, -0.0014369775308296084, -0.011853301897644997, 0.02250063233077526, 0.02013247087597847, -0.03055228479206562, 0.01267393957823515, 0.036434441804885864, 0.024539291858673096, 0.050041742622852325, -0.0454033724963665, -0.07346516102552414, 0.028372399508953094, -0.057826071977615356, 0.015335231088101864, 0.012711949646472931, -0.0006121371989138424, -0.026560060679912567, 0.0012799426913261414, 0.03885176032781601, 0.026761408895254135, 0.05877883732318878, 0.04543119668960571, 0.00772586464881897, 0.009745956398546696, 0.023411206901073456, 0.04102284088730812, -0.0332082137465477, -0.009814807213842869, -0.033480823040008545, -2.577722079877276e-05, 0.030126843601465225, -0.045105114579200745, 0.041004374623298645, 0.0007842665654607117, -0.005297037307173014, 0.04166249930858612, 0.013740862719714642, 0.031283389776945114, -0.047054190188646317, -0.02877264842391014, 0.014451572671532631, -0.008330912329256535, 0.01575607620179653, 0.03836655616760254, 0.028585998341441154, 0.06022465229034424, 0.014461432583630085, -0.03179130330681801, -0.06466642022132874, 0.0034272712655365467, 0.007016490679234266, -0.039520036429166794, 0.01176874153316021, 0.055041804909706116, 0.033385615795850754, -0.027390390634536743, -0.0014993591466918588, -0.008779149502515793, -0.014434798620641232, 0.061815883964300156, -0.004920365288853645, 0.027369704097509384, 0.04413000866770744, 0.013179410248994827, -0.011484737507998943, 0.039524201303720474, 0.0029732936527580023, -0.007710814476013184, -0.037705957889556885, 0.031537484377622604, -0.03127321973443031, 0.06780079752206802, 0.02633778750896454, 0.017419500276446342, 0.0197469349950552, 0.01951937936246395, -0.0045591192319989204, -0.04099363088607788, 0.023796187713742256, 0.006555421743541956, 0.011366328224539757, -0.014717042446136475, 0.02203069068491459, 0.001036526169627905, 0.03396951034665108, 0.04762829467654228, -0.01835354045033455, 0.0145875234156847, -0.030947545543313026, -0.009025374427437782, 0.01380422804504633, 0.00512863602489233, -0.016163822263479233, -0.008085471577942371, 0.012907581403851509, -0.034962475299835205, -0.03494299575686455, -0.08717834204435349, -0.04466240108013153, -0.04784223809838295, -0.06964295357465744, 0.007275538984686136, 0.02197417803108692, 0.016688084229826927, 0.006269244477152824, 0.011667494662106037, -0.030290938913822174, 0.02479977160692215, 0.052434783428907394, -0.0038801429327577353, -0.0033761279191821814, -0.022816507145762444, 0.01698196493089199, 0.03448723256587982, -0.007017314899712801, -0.014474830590188503, 0.013092100620269775, -0.03375625982880592, -0.04335114359855652, 0.0083944546058774, -0.050631266087293625, 0.037903398275375366, 0.03784511238336563, -0.004824098665267229, -0.03681499883532524, 0.02633029595017433, 0.02761826477944851, -0.041753675788640976, 0.044726572930812836, -0.025942586362361908, 0.004498520400375128, -0.016526924446225166, 0.022614790126681328, -0.008134102448821068, -0.05933374911546707, -0.0170682892203331, 0.01950790546834469, 0.021993154659867287, 0.009258713573217392, 0.03577309474349022, -0.006040777079761028, -0.01689918525516987, 0.06474629044532776, -0.02051452361047268, -0.00036078979610465467, -0.03116770274937153, -0.05411141738295555, -0.000868296017870307, -0.021237049251794815, -0.02066796086728573, 0.1410542130470276, 0.013606356456875801, -0.07145093381404877, -0.04837123304605484, 0.08660349249839783, -0.002405100269243121, -0.019075384363532066, -0.019365357235074043, 0.01851011998951435, 0.09412426501512527, -0.04911787062883377, -0.0128995506092906, -0.012053918093442917, 0.018046263605356216, 0.009170940145850182, -0.002959242556244135, 0.017280634492635727, -0.08543619513511658, 0.026256514713168144, 0.011546459048986435, -0.060465261340141296, -0.010382202453911304, -0.025028161704540253, 0.014011220075190067, 0.06226490065455437, 0.009866099804639816, 0.00215950608253479, 0.044206373393535614, -0.025937983766198158, -0.04592662304639816, 0.0696454867720604, -0.04790687933564186, 0.033494751900434494, -0.0342155396938324, 0.018412841483950615, 0.006006625946611166, -0.008958608843386173, -0.039286091923713684, -0.02734021097421646, 0.022405074909329414, 0.0077576590701937675, 0.0069428700953722, -0.009068222716450691, -0.015969447791576385, -0.003446749644353986, 0.018665464594960213, 0.024162519723176956, -0.0059588816948235035, 0.008749212138354778, 0.009875757619738579, -0.03014211170375347, 0.025601701810956, 0.01869679056107998, 0.0246793981641531, 0.019739555194973946, 0.06411167979240417, 0.05066834017634392, -0.014157998375594616, -0.005476726684719324, -0.01567935384809971, -0.02035285159945488, 0.02749427780508995, 0.0036189230158925056, -0.0247687716037035, 0.030312618240714073, 0.0089853061363101, 0.0016174375778064132, 0.056089311838150024, -0.022030271589756012, 0.006874339189380407, -0.00895246583968401, 0.032182205468416214, -0.03530276566743851, -0.019067786633968353, -0.00041821703780442476, 0.01952420547604561, -0.023877020925283432, -0.004116514232009649, -0.017472196370363235, -0.04512961208820343, -0.000665262050461024, -0.014393500983715057, -0.03532331436872482, 0.029158594086766243, 0.002970918081700802, 0.014826922677457333, -0.018131354823708534, -0.025618651881814003, -0.023017656058073044, 0.006374831777065992, -0.034000277519226074, -0.011428195051848888, 0.017366480082273483, 0.011100251227617264, 0.044000230729579926, 0.044098109006881714, 0.016931546851992607, 0.010904215276241302, -0.018336711451411247, 0.02236248552799225, -0.010801452212035656, -0.020552759990096092, -0.015648270025849342, 0.00944614503532648, -0.056049101054668427, 0.06992045789957047, -0.04755287989974022, 0.022811388596892357, -0.01905207894742489, -0.0005521976854652166, -0.0551159493625164, 0.05771920084953308, 0.003313681110739708, -0.012554156593978405, -0.03491245582699776, -0.0004493989108595997, -0.014836834743618965, 0.04550186172127724, 0.020224926993250847, -0.05434810370206833, -0.04117658734321594, 0.04879456013441086, 0.0044229221530258656, 0.00014753938012290746, -0.004815257154405117, 0.026253147050738335, -0.055342838168144226, 0.03325096517801285, -0.032094795256853104, -0.026725497096776962, 0.023136254400014877, 0.011950789950788021, -0.0103463688865304, -0.05655030533671379, -0.046430908143520355, -0.0267023965716362, 0.0395653173327446, 0.05470247194170952, -0.013899288140237331, -0.01553690992295742, -0.0022124205715954304, -0.04116209223866463, 0.008374559693038464, 0.00025515008019283414, -0.03426636382937431, 0.018935082480311394, -0.03281891345977783, 0.008798615075647831, -0.003970039077103138, 0.023412812501192093, 0.01249433308839798, 0.005455314181745052, -0.03127866983413696, -0.014486162923276424, -0.02090301364660263, 0.042937275022268295, 0.01781703159213066, 0.07737474888563156, -0.038432423025369644, 0.04660644009709358, 0.03936861827969551, -0.036005668342113495, -0.007055961061269045, -0.03164416924118996, -0.07419944554567337, 0.0163675956428051, -0.019986335188150406, 0.005489252973347902, -0.012046100571751595, 0.07889817655086517, 0.003632165491580963, 0.03799762949347496, 0.01776469498872757, -0.05217905715107918, -0.016886189579963684, -0.005470234900712967, -0.014474772848188877, 0.028447190299630165, -0.009267609566450119, 0.02553260140120983, 0.00029502619872801006, -0.04289427772164345, -0.07489494979381561, 0.0339854434132576, 0.0716659426689148, -0.048315130174160004, 0.03441132977604866, -0.04454869031906128, -0.054023511707782745, -0.055228911340236664, 0.0653805285692215, -0.06105642765760422, 0.02747117541730404, 0.022343460470438004, 0.054343778640031815, 0.054604314267635345, -0.05817830562591553, -0.01679248735308647, -0.0010837821755558252, 0.014680511318147182, -0.001355848740786314, 0.04336355999112129, -0.023284299299120903, 0.03481322154402733, -0.04792078211903572, 0.10271584987640381, 0.08732537180185318, 0.054378923028707504, -0.01721859723329544, -0.03389263153076172, -0.014271000400185585, 0.04410644993185997, -0.0589648000895977, -0.10395977646112442, -0.00496978173032403, -0.06351707130670547, -0.004880223888903856, -0.01944292150437832, -0.005041536875069141, 0.009868779219686985, -0.021076470613479614, 0.01312626339495182, 0.026089007034897804, -0.03957432508468628, -0.03165239095687866, -0.007891243323683739, 0.03477873653173447, -0.02714000642299652, 0.015237584710121155, 0.02066756784915924, 0.04407768324017525, 0.0550769567489624, 0.030107609927654266, 0.011853663250803947, -0.024173792451620102, 0.014376195147633553, 0.039699945598840714, 0.029913295060396194, -0.08497583121061325, -0.00600552000105381, -0.058703407645225525, 0.006733874324709177, -0.05282263830304146, 0.07921307533979416, -0.019159402698278427, -0.015873195603489876, -0.015008191578090191, 0.022100985050201416, -0.01039169542491436, 0.0033424696885049343, 0.008858509361743927, -0.0025448312517255545, -0.027001190930604935, -0.010651796124875546, 0.052164994180202484, 0.01010804995894432, 0.04327412322163582, 0.03155792877078056, 0.04873507469892502, -0.05584387108683586, -0.01144381333142519, 0.016647186130285263, -0.0056302244774997234, 0.028161536902189255, 0.003070868318900466, -0.06414170563220978, -0.0006059580482542515, -0.0428224615752697, -0.04291451722383499, 0.07868633419275284, 0.04224000126123428, -0.041797857731580734, -0.00715819513425231, 0.013175282627344131, -0.03949834778904915, 0.03971945121884346, 0.038237158209085464, -0.08042848855257034, 0.00833877269178629, -0.005447081755846739, 0.001438029925338924, 0.05658696964383125, -0.031710442155599594, 0.012549635954201221, -0.04449569806456566, -0.013632243499159813, -0.027496619150042534, -0.05011378601193428, 0.07866339385509491, -0.009958427399396896, 0.02002735435962677, -0.004567462485283613, -0.02472861297428608, -0.04544831067323685, -0.006320023909211159, -0.052056245505809784, 0.03617715835571289, -0.036273665726184845, -0.006447257474064827, -0.015921685844659805, -0.012914253398776054, -0.061711035668849945, 0.010351206175982952, 0.06757895648479462, -0.01615845412015915, -0.0064978646114468575, -0.054074425250291824, -0.00034396920818835497, -0.01857716031372547, 0.006079723127186298, -0.012334990315139294, 0.012357001192867756, -0.026382653042674065, 0.11951392143964767, 0.05628421530127525, 0.03174267336726189, 0.03577876463532448, 0.012030803598463535, 0.03710776939988136, -0.01720442809164524, -0.036914411932229996, 0.007174555212259293, -0.062310632318258286], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'group_ids': ['guardkit__task_outcomes']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop
CREATE INDEX FOR (n:Community) ON (n.uuid)
{}
ERROR:asyncio:Task exception was never retrieved
future: <Task finished name='Task-2611' coro=<FalkorDriver.build_indices_and_constraints() done, defined at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py:300> exception=RuntimeError('<asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop')>
Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 305, in build_indices_and_constraints
    await self.execute_query(query)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 230, in execute_query
    result = await graph.query(cypher_query_, params)  # type: ignore[reportUnknownArgumentType]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 105, in query
    return await self._query(q, params=params, timeout=timeout, read_only=False)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 79, in _query
    response = await self.execute_command(*command)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/client.py", line 720, in execute_command
    conn = self.connection or await pool.get_connection()
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/connection.py", line 1194, in get_connection
    async with self._lock:
               ^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 14, in __aenter__
    await self.acquire()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 105, in acquire
    fut = self._get_loop().create_future()
          ~~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/mixins.py", line 20, in _get_loop
    raise RuntimeError(f'{self!r} is bound to a different event loop')
RuntimeError: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop
CREATE INDEX FOR ()-[e:HAS_EPISODE]-() ON (e.uuid, e.group_id)
{}
ERROR:asyncio:Task exception was never retrieved
future: <Task finished name='Task-2603' coro=<FalkorDriver.build_indices_and_constraints() done, defined at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py:300> exception=RuntimeError('<asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop')>
Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 305, in build_indices_and_constraints
    await self.execute_query(query)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 230, in execute_query
    result = await graph.query(cypher_query_, params)  # type: ignore[reportUnknownArgumentType]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 105, in query
    return await self._query(q, params=params, timeout=timeout, read_only=False)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 79, in _query
    response = await self.execute_command(*command)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/client.py", line 720, in execute_command
    conn = self.connection or await pool.get_connection()
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/connection.py", line 1194, in get_connection
    async with self._lock:
               ^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 14, in __aenter__
    await self.acquire()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 105, in acquire
    fut = self._get_loop().create_future()
          ~~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/mixins.py", line 20, in _get_loop
    raise RuntimeError(f'{self!r} is bound to a different event loop')
RuntimeError: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop
WARNING:guardkit.knowledge.graphiti_client:Search request failed: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop
CREATE INDEX FOR (n:Entity) ON (n.uuid, n.group_id, n.name, n.created_at)
{}
ERROR:asyncio:Task exception was never retrieved
future: <Task finished name='Task-2619' coro=<FalkorDriver.build_indices_and_constraints() done, defined at /Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py:300> exception=RuntimeError('<asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop')>
Traceback (most recent call last):
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 305, in build_indices_and_constraints
    await self.execute_query(query)
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py", line 230, in execute_query
    result = await graph.query(cypher_query_, params)  # type: ignore[reportUnknownArgumentType]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 105, in query
    return await self._query(q, params=params, timeout=timeout, read_only=False)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/falkordb/asyncio/graph.py", line 79, in _query
    response = await self.execute_command(*command)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/client.py", line 720, in execute_command
    conn = self.connection or await pool.get_connection()
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/redis/asyncio/connection.py", line 1194, in get_connection
    async with self._lock:
               ^^^^^^^^^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 14, in __aenter__
    await self.acquire()
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/locks.py", line 105, in acquire
    fut = self._get_loop().create_future()
          ~~~~~~~~~~~~~~^^
  File "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/mixins.py", line 20, in _get_loop
    raise RuntimeError(f'{self!r} is bound to a different event loop')
RuntimeError: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/embeddings "HTTP/1.1 200 OK"
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    WITH rel AS e, score, startNode(rel) AS n, endNode(rel) AS m
     WHERE e.group_id IN $group_ids
            WITH e, score, n, m
            RETURN

        e.uuid AS uuid,
        n.uuid AS source_node_uuid,
        m.uuid AS target_node_uuid,
        e.group_id AS group_id,
        e.created_at AS created_at,
        e.name AS name,
        e.fact AS fact,
        e.episodes AS episodes,
        e.expired_at AS expired_at,
        e.valid_at AS valid_at,
        e.invalid_at AS invalid_at,
    properties(e) AS attributes
            ORDER BY score DESC
            LIMIT $limit

{'query': ' (Task | Exclude | internal | artifacts | from | documentation | constraint | count)', 'limit': 20, 'routing_': 'r', 'group_ids': ['patterns']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop

        MATCH (n:Entity)-[e:RELATES_TO]->(m:Entity)
     WHERE e.group_id IN $group_ids
            WITH DISTINCT e, n, m, (2 - vec.cosineDistance(e.fact_embedding, vecf32($search_vector)))/2 AS score
            WHERE score > $min_score
            RETURN

        e.uuid AS uuid,
        n.uuid AS source_node_uuid,
        m.uuid AS target_node_uuid,
        e.group_id AS group_id,
        e.created_at AS created_at,
        e.name AS name,
        e.fact AS fact,
        e.episodes AS episodes,
        e.expired_at AS expired_at,
        e.valid_at AS valid_at,
        e.invalid_at AS invalid_at,
    properties(e) AS attributes
            ORDER BY score DESC
            LIMIT $limit

{'search_vector': [0.030854303389787674, 0.044420111924409866, -0.15249265730381012, -0.10637671500444412, 0.012100446037948132, -0.04243450611829758, 0.06303342431783676, 0.05075465887784958, -0.047419700771570206, 0.0009705084376037121, 0.009739557281136513, 0.04131072014570236, 0.08332853764295578, -0.005968444515019655, 0.01620110496878624, -0.011293135583400726, -0.023377785459160805, -0.040890589356422424, -0.014678672887384892, 0.01408441923558712, 0.021125677973031998, 0.014033679850399494, 0.008591284044086933, 0.003143634181469679, 0.05504145100712776, 0.06179807707667351, 0.06027386337518692, 0.023254888132214546, -0.07322773337364197, -0.0015845297602936625, 0.01256964635103941, 0.02799363248050213, -0.010015960782766342, -0.02794552408158779, -0.010754699818789959, -0.05704345181584358, 0.06929459422826767, 0.013339617289602757, -0.026477301493287086, 0.1007043793797493, 0.011091486550867558, -0.022794658318161964, -0.043136175721883774, -0.035925161093473434, -0.021653834730386734, 0.05920710787177086, 0.04779873415827751, 0.023044103756546974, 0.08490107208490372, -0.03656909987330437, 0.019860370084643364, -0.028341177850961685, -0.002615087665617466, -0.020844578742980957, 0.03786735609173775, 0.013601577840745449, -0.0690835490822792, 0.002306619891896844, 0.014626855961978436, -0.05860478803515434, 0.05304853990674019, 0.0210631862282753, -0.03381204232573509, 0.08490485697984695, -0.021656999364495277, -0.026230907067656517, -0.013023956678807735, 0.026644958183169365, -0.006920541170984507, 0.0022428191732615232, 0.010287022218108177, 0.005865653045475483, 0.054995182901620865, -0.0004908764385618269, -0.049247149378061295, 0.0036455276422202587, -0.06764188408851624, -0.018114738166332245, 0.0019920601043850183, 0.05261099711060524, 0.015266765840351582, 0.02861945517361164, 0.06591132283210754, 0.018922867253422737, 0.0808321088552475, 0.022713014855980873, -0.04787297546863556, -0.021220700815320015, -0.015257363207638264, 0.0631396546959877, 0.022089799866080284, -0.045135218650102615, 0.0016985991969704628, -0.0017307768575847149, -0.013725039549171925, 0.02300383895635605, 0.02858244627714157, 0.027713574469089508, -0.04497513547539711, -0.010807839222252369, -0.0005689088138751686, -0.02208631858229637, 0.010738998651504517, -0.020457973703742027, 0.0062552327290177345, -0.008118418976664543, -0.010401858948171139, 0.02946615405380726, -0.022565709426999092, -0.021249422803521156, -0.002396004507318139, 0.03271045535802841, -0.03326736390590668, -0.04666890203952789, 0.006411004811525345, -0.021300725638866425, 0.07643263787031174, -0.008594678714871407, -0.03858562931418419, -0.004771820735186338, -0.05669908598065376, -0.03527238219976425, 0.034821417182683945, 0.015394859947264194, 0.008935380727052689, 0.003926821518689394, -0.07924550026655197, 0.024671422317624092, 0.03546642139554024, -0.060819003731012344, 0.0009726603166200221, -0.006069427356123924, -0.0038421167992055416, 0.0001724377943901345, -0.0020962082780897617, 0.013231690041720867, -0.024662524461746216, -0.010383550077676773, 0.0033337066415697336, -0.006201694719493389, 0.0038142516277730465, 0.032491639256477356, -0.028349796310067177, -0.006959280930459499, 0.019415810704231262, -0.07051411271095276, 0.07964842766523361, -0.01962967962026596, -0.018353372812271118, -0.02979769930243492, 0.005925977602601051, 0.021830657497048378, -0.00649291044101119, 0.00039740066858939826, 0.03224555030465126, -0.062428221106529236, 0.008772051893174648, -0.02437880076467991, -0.06016026437282562, 0.018655987456440926, 0.019988814368844032, 0.020625432953238487, -0.04049528390169144, 0.06219000369310379, -0.008940177969634533, -0.032510481774806976, -0.020898744463920593, 0.06542886793613434, 0.008219041861593723, 0.006392613518983126, -0.021587945520877838, -0.059104468673467636, -0.031420961022377014, 0.03684833273291588, 0.03224372863769531, 0.020564617589116096, 0.043242231011390686, -0.019283603876829147, 0.042374178767204285, -0.021024450659751892, 0.008654273115098476, -0.032648131251335144, 0.021188003942370415, 0.05635427311062813, -0.06458787620067596, -0.04846027493476868, 0.00910431332886219, 0.01107641588896513, 0.0037845447659492493, 0.034955985844135284, 0.017448285594582558, 0.011762850917875767, -0.02987404726445675, -0.06040117144584656, -0.06594642996788025, -0.0631508156657219, 0.055318839848041534, -0.030537614598870277, 0.03246859833598137, -0.07413487881422043, -0.030114291235804558, -0.0014587757177650928, -0.050498105585575104, 0.012630513869225979, -0.040876977145671844, -0.003998949658125639, -0.015539627522230148, 0.012419530190527439, -0.020841114223003387, 0.024615377187728882, 0.060920827090740204, -0.0021354290656745434, -0.009589679539203644, 0.03668854758143425, 0.015315311960875988, -0.03200007975101471, 0.01947806216776371, 0.015535399317741394, 0.020832939073443413, 0.0009696008637547493, 0.005744085181504488, 0.016746096312999725, 0.014648695476353168, -0.02947499230504036, 0.04059843346476555, -0.004542586859315634, -0.007973958738148212, 0.003135488834232092, -0.02053406462073326, -0.017218248918652534, -0.05251000449061394, -0.07307291030883789, 0.022258274257183075, -0.009196942672133446, 0.027808845043182373, 0.02904067188501358, -0.004367210902273655, 0.04121246561408043, 0.005061573814600706, -0.006116786971688271, -0.03674761578440666, 0.05556017532944679, -0.024896636605262756, -0.05013922601938248, -0.030814172700047493, -0.044162649661302567, -0.062292709946632385, -0.00476666959002614, 0.036525826901197433, 0.07863802462816238, -0.04127079248428345, 0.006779748480767012, 0.011375892907381058, 0.0451117604970932, 0.011544778011739254, -0.013557630591094494, 0.005790486000478268, -0.002336176810786128, 0.020907722413539886, -0.016921933740377426, 0.031004132702946663, -0.04633437469601631, 0.04534037411212921, -0.03389233350753784, 0.010420849546790123, -0.0890313908457756, -0.04273815453052521, -0.01057367492467165, 0.05078711360692978, 0.03159687668085098, 0.01779579184949398, 0.04049094393849373, -0.025351176038384438, 0.024667920544743538, 0.043645527213811874, 0.012137873098254204, 0.01148583646863699, -0.009936831891536713, -0.08014784753322601, 0.05653044581413269, -0.022937113419175148, -0.03800298646092415, -0.019486207515001297, 0.03335690498352051, -0.036296501755714417, -0.00939237605780363, -0.009519068524241447, -0.014362206682562828, 0.02882012352347374, -0.0030117493588477373, 0.011293298564851284, 0.04440426826477051, -0.04244352877140045, 0.04045085608959198, -0.009608084335923195, -0.0014369775308296084, -0.011853301897644997, 0.02250063233077526, 0.02013247087597847, -0.03055228479206562, 0.01267393957823515, 0.036434441804885864, 0.024539291858673096, 0.050041742622852325, -0.0454033724963665, -0.07346516102552414, 0.028372399508953094, -0.057826071977615356, 0.015335231088101864, 0.012711949646472931, -0.0006121371989138424, -0.026560060679912567, 0.0012799426913261414, 0.03885176032781601, 0.026761408895254135, 0.05877883732318878, 0.04543119668960571, 0.00772586464881897, 0.009745956398546696, 0.023411206901073456, 0.04102284088730812, -0.0332082137465477, -0.009814807213842869, -0.033480823040008545, -2.577722079877276e-05, 0.030126843601465225, -0.045105114579200745, 0.041004374623298645, 0.0007842665654607117, -0.005297037307173014, 0.04166249930858612, 0.013740862719714642, 0.031283389776945114, -0.047054190188646317, -0.02877264842391014, 0.014451572671532631, -0.008330912329256535, 0.01575607620179653, 0.03836655616760254, 0.028585998341441154, 0.06022465229034424, 0.014461432583630085, -0.03179130330681801, -0.06466642022132874, 0.0034272712655365467, 0.007016490679234266, -0.039520036429166794, 0.01176874153316021, 0.055041804909706116, 0.033385615795850754, -0.027390390634536743, -0.0014993591466918588, -0.008779149502515793, -0.014434798620641232, 0.061815883964300156, -0.004920365288853645, 0.027369704097509384, 0.04413000866770744, 0.013179410248994827, -0.011484737507998943, 0.039524201303720474, 0.0029732936527580023, -0.007710814476013184, -0.037705957889556885, 0.031537484377622604, -0.03127321973443031, 0.06780079752206802, 0.02633778750896454, 0.017419500276446342, 0.0197469349950552, 0.01951937936246395, -0.0045591192319989204, -0.04099363088607788, 0.023796187713742256, 0.006555421743541956, 0.011366328224539757, -0.014717042446136475, 0.02203069068491459, 0.001036526169627905, 0.03396951034665108, 0.04762829467654228, -0.01835354045033455, 0.0145875234156847, -0.030947545543313026, -0.009025374427437782, 0.01380422804504633, 0.00512863602489233, -0.016163822263479233, -0.008085471577942371, 0.012907581403851509, -0.034962475299835205, -0.03494299575686455, -0.08717834204435349, -0.04466240108013153, -0.04784223809838295, -0.06964295357465744, 0.007275538984686136, 0.02197417803108692, 0.016688084229826927, 0.006269244477152824, 0.011667494662106037, -0.030290938913822174, 0.02479977160692215, 0.052434783428907394, -0.0038801429327577353, -0.0033761279191821814, -0.022816507145762444, 0.01698196493089199, 0.03448723256587982, -0.007017314899712801, -0.014474830590188503, 0.013092100620269775, -0.03375625982880592, -0.04335114359855652, 0.0083944546058774, -0.050631266087293625, 0.037903398275375366, 0.03784511238336563, -0.004824098665267229, -0.03681499883532524, 0.02633029595017433, 0.02761826477944851, -0.041753675788640976, 0.044726572930812836, -0.025942586362361908, 0.004498520400375128, -0.016526924446225166, 0.022614790126681328, -0.008134102448821068, -0.05933374911546707, -0.0170682892203331, 0.01950790546834469, 0.021993154659867287, 0.009258713573217392, 0.03577309474349022, -0.006040777079761028, -0.01689918525516987, 0.06474629044532776, -0.02051452361047268, -0.00036078979610465467, -0.03116770274937153, -0.05411141738295555, -0.000868296017870307, -0.021237049251794815, -0.02066796086728573, 0.1410542130470276, 0.013606356456875801, -0.07145093381404877, -0.04837123304605484, 0.08660349249839783, -0.002405100269243121, -0.019075384363532066, -0.019365357235074043, 0.01851011998951435, 0.09412426501512527, -0.04911787062883377, -0.0128995506092906, -0.012053918093442917, 0.018046263605356216, 0.009170940145850182, -0.002959242556244135, 0.017280634492635727, -0.08543619513511658, 0.026256514713168144, 0.011546459048986435, -0.060465261340141296, -0.010382202453911304, -0.025028161704540253, 0.014011220075190067, 0.06226490065455437, 0.009866099804639816, 0.00215950608253479, 0.044206373393535614, -0.025937983766198158, -0.04592662304639816, 0.0696454867720604, -0.04790687933564186, 0.033494751900434494, -0.0342155396938324, 0.018412841483950615, 0.006006625946611166, -0.008958608843386173, -0.039286091923713684, -0.02734021097421646, 0.022405074909329414, 0.0077576590701937675, 0.0069428700953722, -0.009068222716450691, -0.015969447791576385, -0.003446749644353986, 0.018665464594960213, 0.024162519723176956, -0.0059588816948235035, 0.008749212138354778, 0.009875757619738579, -0.03014211170375347, 0.025601701810956, 0.01869679056107998, 0.0246793981641531, 0.019739555194973946, 0.06411167979240417, 0.05066834017634392, -0.014157998375594616, -0.005476726684719324, -0.01567935384809971, -0.02035285159945488, 0.02749427780508995, 0.0036189230158925056, -0.0247687716037035, 0.030312618240714073, 0.0089853061363101, 0.0016174375778064132, 0.056089311838150024, -0.022030271589756012, 0.006874339189380407, -0.00895246583968401, 0.032182205468416214, -0.03530276566743851, -0.019067786633968353, -0.00041821703780442476, 0.01952420547604561, -0.023877020925283432, -0.004116514232009649, -0.017472196370363235, -0.04512961208820343, -0.000665262050461024, -0.014393500983715057, -0.03532331436872482, 0.029158594086766243, 0.002970918081700802, 0.014826922677457333, -0.018131354823708534, -0.025618651881814003, -0.023017656058073044, 0.006374831777065992, -0.034000277519226074, -0.011428195051848888, 0.017366480082273483, 0.011100251227617264, 0.044000230729579926, 0.044098109006881714, 0.016931546851992607, 0.010904215276241302, -0.018336711451411247, 0.02236248552799225, -0.010801452212035656, -0.020552759990096092, -0.015648270025849342, 0.00944614503532648, -0.056049101054668427, 0.06992045789957047, -0.04755287989974022, 0.022811388596892357, -0.01905207894742489, -0.0005521976854652166, -0.0551159493625164, 0.05771920084953308, 0.003313681110739708, -0.012554156593978405, -0.03491245582699776, -0.0004493989108595997, -0.014836834743618965, 0.04550186172127724, 0.020224926993250847, -0.05434810370206833, -0.04117658734321594, 0.04879456013441086, 0.0044229221530258656, 0.00014753938012290746, -0.004815257154405117, 0.026253147050738335, -0.055342838168144226, 0.03325096517801285, -0.032094795256853104, -0.026725497096776962, 0.023136254400014877, 0.011950789950788021, -0.0103463688865304, -0.05655030533671379, -0.046430908143520355, -0.0267023965716362, 0.0395653173327446, 0.05470247194170952, -0.013899288140237331, -0.01553690992295742, -0.0022124205715954304, -0.04116209223866463, 0.008374559693038464, 0.00025515008019283414, -0.03426636382937431, 0.018935082480311394, -0.03281891345977783, 0.008798615075647831, -0.003970039077103138, 0.023412812501192093, 0.01249433308839798, 0.005455314181745052, -0.03127866983413696, -0.014486162923276424, -0.02090301364660263, 0.042937275022268295, 0.01781703159213066, 0.07737474888563156, -0.038432423025369644, 0.04660644009709358, 0.03936861827969551, -0.036005668342113495, -0.007055961061269045, -0.03164416924118996, -0.07419944554567337, 0.0163675956428051, -0.019986335188150406, 0.005489252973347902, -0.012046100571751595, 0.07889817655086517, 0.003632165491580963, 0.03799762949347496, 0.01776469498872757, -0.05217905715107918, -0.016886189579963684, -0.005470234900712967, -0.014474772848188877, 0.028447190299630165, -0.009267609566450119, 0.02553260140120983, 0.00029502619872801006, -0.04289427772164345, -0.07489494979381561, 0.0339854434132576, 0.0716659426689148, -0.048315130174160004, 0.03441132977604866, -0.04454869031906128, -0.054023511707782745, -0.055228911340236664, 0.0653805285692215, -0.06105642765760422, 0.02747117541730404, 0.022343460470438004, 0.054343778640031815, 0.054604314267635345, -0.05817830562591553, -0.01679248735308647, -0.0010837821755558252, 0.014680511318147182, -0.001355848740786314, 0.04336355999112129, -0.023284299299120903, 0.03481322154402733, -0.04792078211903572, 0.10271584987640381, 0.08732537180185318, 0.054378923028707504, -0.01721859723329544, -0.03389263153076172, -0.014271000400185585, 0.04410644993185997, -0.0589648000895977, -0.10395977646112442, -0.00496978173032403, -0.06351707130670547, -0.004880223888903856, -0.01944292150437832, -0.005041536875069141, 0.009868779219686985, -0.021076470613479614, 0.01312626339495182, 0.026089007034897804, -0.03957432508468628, -0.03165239095687866, -0.007891243323683739, 0.03477873653173447, -0.02714000642299652, 0.015237584710121155, 0.02066756784915924, 0.04407768324017525, 0.0550769567489624, 0.030107609927654266, 0.011853663250803947, -0.024173792451620102, 0.014376195147633553, 0.039699945598840714, 0.029913295060396194, -0.08497583121061325, -0.00600552000105381, -0.058703407645225525, 0.006733874324709177, -0.05282263830304146, 0.07921307533979416, -0.019159402698278427, -0.015873195603489876, -0.015008191578090191, 0.022100985050201416, -0.01039169542491436, 0.0033424696885049343, 0.008858509361743927, -0.0025448312517255545, -0.027001190930604935, -0.010651796124875546, 0.052164994180202484, 0.01010804995894432, 0.04327412322163582, 0.03155792877078056, 0.04873507469892502, -0.05584387108683586, -0.01144381333142519, 0.016647186130285263, -0.0056302244774997234, 0.028161536902189255, 0.003070868318900466, -0.06414170563220978, -0.0006059580482542515, -0.0428224615752697, -0.04291451722383499, 0.07868633419275284, 0.04224000126123428, -0.041797857731580734, -0.00715819513425231, 0.013175282627344131, -0.03949834778904915, 0.03971945121884346, 0.038237158209085464, -0.08042848855257034, 0.00833877269178629, -0.005447081755846739, 0.001438029925338924, 0.05658696964383125, -0.031710442155599594, 0.012549635954201221, -0.04449569806456566, -0.013632243499159813, -0.027496619150042534, -0.05011378601193428, 0.07866339385509491, -0.009958427399396896, 0.02002735435962677, -0.004567462485283613, -0.02472861297428608, -0.04544831067323685, -0.006320023909211159, -0.052056245505809784, 0.03617715835571289, -0.036273665726184845, -0.006447257474064827, -0.015921685844659805, -0.012914253398776054, -0.061711035668849945, 0.010351206175982952, 0.06757895648479462, -0.01615845412015915, -0.0064978646114468575, -0.054074425250291824, -0.00034396920818835497, -0.01857716031372547, 0.006079723127186298, -0.012334990315139294, 0.012357001192867756, -0.026382653042674065, 0.11951392143964767, 0.05628421530127525, 0.03174267336726189, 0.03577876463532448, 0.012030803598463535, 0.03710776939988136, -0.01720442809164524, -0.036914411932229996, 0.007174555212259293, -0.062310632318258286], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'group_ids': ['patterns']}
WARNING:guardkit.knowledge.graphiti_client:Search request failed: <asyncio.locks.Lock object at 0x12065b8c0 [locked]> is bound to a different event loop
WARNING:guardkit.knowledge.graphiti_client:Graphiti disabled after 3 consecutive failures -- continuing without knowledge graph context
INFO:guardkit.knowledge.turn_state_operations:[TurnState] Loaded from local file: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/turn_state_turn_1.json (454 chars)
INFO:guardkit.knowledge.autobuild_context_loader:[TurnState] Turn continuation loaded: 454 chars for turn 2
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Coach context categories: []
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Context loaded in 0.1s
INFO:guardkit.knowledge.autobuild_context_loader:[Graphiti] Coach context: 0 categories, 0/7892 tokens
INFO:guardkit.orchestrator.autobuild:Using LLM Coach (primary) for TASK-FIX-IA03 turn 2
INFO:guardkit.orchestrator.autobuild:[Graphiti] Coach context provided: 503 chars
INFO:guardkit.orchestrator.quality_gates.coach_validator:CoachValidator pinning independent-test interpreter to /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.venv/bin/python
INFO:guardkit.orchestrator.quality_gates.coach_validator:Quality gate evaluation complete: tests=True (required=True), coverage=True (required=True), arch=True (required=False), audit=True (required=True), ALL_PASSED=True
INFO:guardkit.orchestrator.quality_gates.coach_validator:Test execution environment: sys.executable=/usr/local/bin/python3, which pytest=/Library/Frameworks/Python.framework/Versions/3.14/bin/pytest, coach_test_execution=sdk, resolved_interpreter=/Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.venv/bin/python
INFO:guardkit.orchestrator.quality_gates.coach_validator:Task-specific tests detected via task_work_results: 2 file(s)
INFO:guardkit.orchestrator.quality_gates.coach_validator:Running independent tests via SDK (environment parity): pytest tests/unit/test_agent_invoker.py tests/unit/test_doc_level_constraint.py -v --tb=short
INFO:guardkit.orchestrator.quality_gates.coach_validator:Coach SDK test command pinned to bootstrap interpreter: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.venv/bin/python -m pytest tests/unit/test_agent_invoker.py tests/unit/test_doc_level_constraint.py -v --tb=short
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
ERROR:guardkit.orchestrator.quality_gates.coach_validator:SDK coach test execution timed out after 300s
INFO:guardkit.orchestrator.quality_gates.coach_validator:SDK independent tests failed in 300.0s
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] SDK timeout: 3600s (CLI override, skipping dynamic calculation)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (30s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (60s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (90s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (120s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (150s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (180s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (210s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (240s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (270s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (300s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (330s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (360s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (390s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (420s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (450s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (480s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (510s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (540s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (570s elapsed)
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (600s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
INFO:guardkit.orchestrator.agent_invoker:[TASK-FIX-IA03] Coach invocation in progress... (630s elapsed)
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 200 OK"
WARNING:guardkit.orchestrator.autobuild:Coach verdict-emission failed in primary path for TASK-FIX-IA03 turn 2: Coach decision not found: no fenced ```json block in Coach response for TASK-FIX-IA03 turn 2 (1155 chars content + 1347 chars reasoning_content). Emitting synthetic feedback decision (substrate F2 at Coach level — Player will retry on turn 3 with this feedback).
INFO:guardkit.orchestrator.autobuild:Wrote synthetic feedback decision to /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/coach_turn_2.json (rationale: Coach verdict-emission failed: Coach decision not found: no fenced ```json block in Coach response for TASK-FIX-IA03 turn 2 (1155 chars content + 1347 chars reasoning_content). Likely substrate limitation (qwen36-workhorse F2 at Coach level). Player should retry on turn 3 with this feedback.)
  ⚠ [2026-06-08T14:50:32.492Z] Feedback: Coach verdict-emission failed: Coach decision not found: no fenced ```json block...
  [2026-06-08T14:34:42.646Z] Turn 2/5: Coach Validation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
INFO:guardkit.orchestrator.progress:[2026-06-08T14:50:32.492Z] Completed turn 2: feedback - Feedback: Coach verdict-emission failed: Coach decision not found: no fenced ```json block...
   Context: retrieved (0 categories, 0/7892 tokens)
INFO:guardkit.orchestrator.autobuild:Turn state saved to local file: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/turn_state_turn_2.json
INFO:guardkit.orchestrator.autobuild:Criteria Progress (Turn 2): 0/5 verified (0%)
INFO:guardkit.orchestrator.autobuild:Criteria: 0 verified, 0 rejected, 5 pending
INFO:guardkit.orchestrator.worktree_checkpoints:Creating checkpoint for TASK-FIX-IA03 turn 2 (tests: fail, count: 0)
INFO:guardkit.orchestrator.worktree_checkpoints:Created checkpoint: 86ebca85 for turn 2 (2 total)
INFO:guardkit.orchestrator.autobuild:Checkpoint created: 86ebca85 for turn 2
INFO:guardkit.orchestrator.autobuild:Coach provided feedback on turn 2
INFO:guardkit.orchestrator.autobuild:Timeout budget exhausted for TASK-FIX-IA03 at turn 3: remaining=350.3s < min=600s
INFO:guardkit.orchestrator.autobuild:Phase 4 (Finalize): Preserving worktree for FEAT-AOF

                                                    AutoBuild Summary (TIMEOUT_BUDGET_EXHAUSTED)
╭────────┬───────────────────────────┬──────────────┬───────────────────────────────────────────────────────────────────────────────────────────────╮
│ Turn   │ Phase                     │ Status       │ Summary                                                                                       │
├────────┼───────────────────────────┼──────────────┼───────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1      │ Player Implementation     │ ✓ success    │ 29 files created, 2 modified, 0 tests (failing)                                               │
│ 1      │ Coach Validation          │ ⚠ feedback   │ Feedback: Coach verdict-emission failed: Coach decision not found: no fenced ```json block... │
│ 2      │ Player Implementation     │ ✓ success    │ 0 files created, 67 modified, 0 tests (failing)                                               │
│ 2      │ Coach Validation          │ ⚠ feedback   │ Feedback: Coach verdict-emission failed: Coach decision not found: no fenced ```json block... │
╰────────┴───────────────────────────┴──────────────┴───────────────────────────────────────────────────────────────────────────────────────────────╯

╭────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Status: TIMEOUT_BUDGET_EXHAUSTED                                                                                                                                                                                           │
│                                                                                                                                                                                                                            │
│ Unknown error occurred. Worktree preserved for inspection.                                                                                                                                                                 │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
INFO:guardkit.orchestrator.progress:Summary rendered: timeout_budget_exhausted after 2 turns
INFO:guardkit.orchestrator.autobuild:Worktree preserved at /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF for human review. Decision: timeout_budget_exhausted
INFO:guardkit.orchestrator.autobuild:Orchestration complete: TASK-FIX-IA03, decision=timeout_budget_exhausted, turns=2
    ✗ TASK-FIX-IA03: timeout_budget_exhausted (2 turns)
  [2026-06-08T14:50:32.818Z] ✗ TASK-FIX-IA03: FAILED (2 turns) timeout_budget_exhausted

  [2026-06-08T14:50:32.822Z] Wave 1 ✗ FAILED: 0 passed, 1 failed
INFO:guardkit.cli.display:[2026-06-08T14:50:32.822Z] Wave 1 complete: passed=0, failed=1
⚠ Stopping execution (stop_on_failure=True)
INFO:guardkit.orchestrator.feature_orchestrator:Phase 3 (Finalize): Updating feature FEAT-AOF

════════════════════════════════════════════════════════════
FEATURE RESULT: FAILED
════════════════════════════════════════════════════════════

Feature: FEAT-AOF - AutoBuild Observability Fixes
Status: FAILED
Tasks: 0/3 completed (1 failed)
Total Turns: 2
Duration: 74m 9s

                                  Wave Summary
╭────────┬──────────┬────────────┬──────────┬──────────┬──────────┬─────────────╮
│  Wave  │  Tasks   │   Status   │  Passed  │  Failed  │  Turns   │  Recovered  │
├────────┼──────────┼────────────┼──────────┼──────────┼──────────┼─────────────┤
│   1    │    1     │   ✗ FAIL   │    0     │    1     │    2     │      -      │
╰────────┴──────────┴────────────┴──────────┴──────────┴──────────┴─────────────╯

Execution Quality:
  Clean executions: 1/1 (100%)

Worktree: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF
Branch: autobuild/FEAT-AOF

Next Steps:
  1. Review failed tasks: cd /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF
  2. Check status: guardkit autobuild status FEAT-AOF
  3. Resume: guardkit autobuild feature FEAT-AOF --resume
INFO:guardkit.cli.display:Final summary rendered: FEAT-AOF - failed
INFO:guardkit.orchestrator.review_summary:Review summary written to /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/autobuild/FEAT-AOF/review-summary.md
✓ Review summary: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/autobuild/FEAT-AOF/review-summary.md
INFO:guardkit.orchestrator.feature_orchestrator:Feature orchestration complete: FEAT-AOF, status=failed, completed=0/3
richardwoollcott@Mac guardkit %