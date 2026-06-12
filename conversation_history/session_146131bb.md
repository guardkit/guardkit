## Summarized at 2026-06-12T16:41:28.688258+00:00

Human: You are the code-reviewer specialist for task TASK-QAWE-002.

Task context (from the task markdown):
Task context unavailable for TASK-QAWE-002

Phase 4 summary (test-orchestrator outcome):
- tests_run: 50
- tests_failed: 0
- coverage_pct: 8.81
- quality_gates_passed: True
- output_summary: 50/50 tests passed; 8.81% line coverage on guardkit/orchestrator; all quality gates green

Your job:
1. Review the implementation in the worktree against the task's acceptance criteria using Read/Search/Grep.
2. Apply the review checklist from your agent definition (build, requirements, code quality, testing, security, performance, documentation).
3. Report findings via your normal response stream — the orchestrator records the review outcome in specialist_results.json.
Do NOT modify source files: the Write tool is intentionally withheld from this invocation.
AI: [{'name': 'ls', 'args': {'path': '.'}, 'id': 'DycK5jC9oQjxKEi3NIosunPzvMiGucUk', 'type': 'tool_call'}]
Tool: ['/bin.usr-is-merged/', '/bin/', '/boot/', '/cdrom/', '/dev/', '/etc/', '/home/', '/lib.usr-is-merged/', '/lib/', '/lost+found/', '/media/', '/mnt/', '/opt/', '/proc/', '/raid/', '/root/', '/run/', '/sbin.usr-is-merged/', '/sbin/', '/snap/', '/srv/', '/swap.img', '/sys/', '/tmp/', '/usr/', '/var/']
AI: [{'name': 'ls', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/'}, 'id': '1vZGHvScYeG3PsifceZgLJ6uiBiBr6N2', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/.cache/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/.clarification_execution.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/.claude/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/.coverage', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/.env.example', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/.git', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/.github/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/.gitignore', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/.guardkit-git.lock', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/.guardkit/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/.mcp.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/.pytest_cache/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/.tmp_clarification_context_sensitive_coach.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/.venv/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/CHANGELOG.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/CLARIFICATION_EXECUTION_TASK-FBSDK-020.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/CLARIFICATION_QUICK_REFERENCE.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/CLARIFICATION_SUMMARY.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/CLAUDE.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/CNAME', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/CONTRIBUTING.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/DESIGN-DELIVERY-SUMMARY.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/FEAT-AOF-verify/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/FastApi_feature_plans.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/IMPLEMENTATION-SUMMARY-TASK-AB-584A.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/IMPLEMENTATION-SUMMARY.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/IMPLEMENTATION_SUMMARY.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/LICENSE', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/README.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/TASK-DM-008-IMPLEMENTATION-SUMMARY.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/TASK-FBSDK-020-CODE-REVIEW.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/TASK-FBSDK-020-COMPLETION-REPORT.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/TASK-FBSDK-020-EXECUTION-SUMMARY.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/TASK_FBSDK_002_IMPLEMENTATION.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/TEST_RESULTS_FBSDK_020.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/TEST_RESULTS_TASK_BRF_001.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/__pycache__/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/_scratch/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/api/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/autobuild_local_vllm.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/backups/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/conftest.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/conversation_history/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/cov.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/coverage.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/docker/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/docs/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/examples/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/execute_clarification.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/features/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit.sln', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/ia03_ai_cov.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/ia03_cov.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/ia03_final_cov.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/installer/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/lib/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/logitech_gb10.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/main.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/measurements/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/minimax-backup-setup.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/mkdocs.yml', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/node_modules/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/package-lock.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/package.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/phase_4_test_results.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/pyproject.toml', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/pytest.ini', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/requirements.txt', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/run_adr_tests.sh', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/scratch_notes.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/scripts/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tasks/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/templates/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/test_api/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tsconfig.json', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/uv.lock', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/vitest.config.ts']
AI: [{'name': 'glob', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tasks/', 'pattern': '**/*TASK-QAWE-002*'}, 'id': 'iYcCevw3aE1kEf5mdlZVnzJE6QAwF4oD', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tasks/design_approved/TASK-QAWE-002-unwired-bundle-integration.md']
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tasks/design_approved/TASK-QAWE-002-unwired-bundle-integration.md'}, 'id': 'pyauPQK5nNiETqWHaZGjcfpKr6vJmY0U', 'type': 'tool_call'}]
Tool:      1	---
     2	complexity: 5
     3	dependencies:
     4	- TASK-QAWE-001
     5	feature_id: FEAT-C332
     6	id: TASK-QAWE-002
     7	implementation_mode: task-work
     8	parent_task: TASK-HMIG-BDDWIRE
     9	priority: medium
    10	status: design_approved
    11	task_type: feature
    12	title: UNWIRED_PATH bundle integration — coach_evidence fields, gather_evidence, render
    13	wave: 2
    14	---
    15	
    16	# Task: UNWIRED_PATH bundle integration (Wave 1)
    17	
    18	## Description
    19	
    20	Wire the Wave-0 `WiringAnalyzer` UNWIRED_PATH output into the Coach evidence path via
    21	the verified, unchanged seams in `docs/features/qa-verifier-wiring-probes-scope.md` §5.
    22	guardkit consumes guardkitfactory's `analyze_wiring(...)` lazily (the BDDWIRE pattern)
    23	and stores the returned **dict** (never the dataclass), so `coach_evidence.py` keeps
    24	zero guardkitfactory import.
    25	
    26	## Acceptance Criteria
    27	
    28	- [ ] **AC-002 (bundle fields):** add `wiring`, `mocked_seam`, `spec_gap`
    29	  `Optional[Dict]` fields after `tests:` at `coach_evidence.py:169`; `to_dict()`
    30	  (`asdict`, `:180-191`) unchanged.
    31	- [ ] **AC (gather population):** populate at the **complete-path return only**
    32	  (`coach_validator.py:2120`); partial returns (2030/2058/2103) leave them `None`.
    33	  Authored set from `_compute_own_authored` (`:775-783`, extract or duplicate — not
    34	  `files_modified`). `detect_stack_template` (`:64`) supplies the language.
    35	- [ ] **AC-008 (task-type gate):** SCAFFOLDING/DOCUMENTATION or zero-target turns →
    36	  all three fields `None`.
    37	- [ ] **AC-011 (reaches verdict):** `_render_evidence_bundle_section`
    38	  (`agent_invoker.py:3098`) surfaces the fields; advisory guard sentence #7 appended
    39	  after guard #6 (`:3320-3332`).
    40	- [ ] **AC-016 (truncation):** `>20` findings → first 20 + "... and N more" mirroring
    41	  `bdd.discoveries` (`agent_invoker.py:3138-3152`).
    42	- [ ] **AC-015 (absent-vs-empty):** `findings:[]` + positive status is distinct from
    43	  `None`.
    44	- [ ] **AC-017 (graceful import absence):** with guardkitfactory/tree-sitter absent,
    45	  the lazy seam catches `ImportError`, all three fields `None`, `gather_evidence`
    46	  does not crash.
    47	- [ ] **AC-018 (no regression):** existing guardkit + guardkitfactory suites green.
    48	- [ ] All modified files pass project-configured lint/format checks with zero errors.
    49	
    50	## Coach Validation
    51	- `pytest tests/orchestrator -k "wiring or coach_evidence" -v`
    52	- Lint/format pass with zero errors.
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/coach_evidence.py', 'limit': 200, 'offset': 150}, 'id': 'e2KBuRSUZF3jSpwTdoKpCAGaeCxqeReo', 'type': 'tool_call'}]
Tool: Error: File '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/coach_evidence.py' not found
AI: [{'name': 'glob', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/', 'pattern': '*.py'}, 'id': 'XeOlRsfoyOMwx0NWJuftLDd322em4vpe', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/_group_defs.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/cli/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/cli/autobuild.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/cli/decorators.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/cli/display.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/cli/doctor.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/cli/feature.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/cli/graphiti.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/cli/graphiti_query_commands.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/cli/init.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/cli/main.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/cli/review.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/cli/system_context.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/cli/system_plan.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/cli/task.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/commands/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/commands/feature_plan_integration.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/design/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/design/cache_manager.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/design/change_detector.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/design/state_handlers.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/integrations/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/integrations/graphiti/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/integrations/graphiti/constants.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/integrations/graphiti/episodes/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/integrations/graphiti/episodes/architectural_decision.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/integrations/graphiti/episodes/implementation_mode.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/integrations/graphiti/episodes/project_architecture.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/integrations/graphiti/episodes/project_overview.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/integrations/graphiti/exists_result.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/integrations/graphiti/metadata.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/integrations/graphiti/parsers/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/integrations/graphiti/parsers/adr.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/integrations/graphiti/parsers/base.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/integrations/graphiti/parsers/feature_spec.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/integrations/graphiti/parsers/full_doc_parser.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/integrations/graphiti/parsers/project_doc_parser.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/integrations/graphiti/parsers/project_overview.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/integrations/graphiti/parsers/registry.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/integrations/graphiti/parsers/yaml_parser.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/integrations/graphiti/project.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/integrations/graphiti/upsert_result.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/adr.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/adr_discovery.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/adr_service.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/autobuild_context_loader.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/budget_calculator.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/config.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/context_formatter.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/context_loader.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/decision_detector.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/entities/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/entities/api_contract.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/entities/architecture_context.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/entities/component.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/entities/crosscutting.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/entities/data_model.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/entities/design_decision.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/entities/failed_approach.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/entities/feature_overview.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/entities/outcome.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/entities/system_context.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/entities/turn_state.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/episode_splitting.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/facts/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/facts/quality_gate_config.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/facts/role_constraint.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/failed_approach_manager.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/falkordb_workaround.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/feature_detector.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/feature_plan_context.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/gap_analyzer.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/graphiti_client.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/interactive_capture.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/job_context_retriever.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/outcome_manager.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/outcome_queries.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/project_seeding.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/quality_gate_formatter.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/query_logger.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/relevance_tuning.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/review_knowledge_capture.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/role_constraint_formatter.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/seed_agents.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/seed_architecture_decisions.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/seed_command_workflows.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/seed_component_status.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/seed_failed_approaches.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/seed_failure_patterns.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/seed_feature_build_adrs.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/seed_feature_build_architecture.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/seed_feature_overviews.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/seed_helpers.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/seed_integration_points.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/seed_pattern_examples.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/seed_patterns.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/seed_product_knowledge.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/seed_project_architecture.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/seed_project_overview.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/seed_quality_gate_phases.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/seed_role_constraints.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/seed_rules.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/seed_technology_stack.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/seed_templates.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/seeding.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/system_seeding.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/task_analyzer.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/template_pattern_loader.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/template_sync.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/knowledge/turn_state_operations.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/lib/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/lib/pytest_argv.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/lib/task_type_detector.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/models/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/models/task_types.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/agent_invoker.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/autobuild.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/browser_verifier.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/coach_grammar.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/coach_output_parser.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/coach_verification.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/docker_fixtures.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/environment_bootstrap.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/exceptions.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/feature_complete.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/feature_loader.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/feature_orchestrator.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/feature_validator.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/gpu_monitor.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/harness/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/harness/adapter.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/harness/sdk_harness.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/harness/selector.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/instrumentation/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/instrumentation/concurrency.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/instrumentation/digests.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/instrumentation/emitter.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/instrumentation/llm_instrumentation.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/instrumentation/prompt_profile.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/instrumentation/redaction.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/instrumentation/schemas.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/intensity_detector.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/mcp_design_extractor.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/parallel_strategy.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/paths.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/phase_specialists.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/preflight.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/preflight_ignore_gate.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/progress.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/progress_logger.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/prohibition_checklist.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/prompts/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/protocol.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/ac_linter.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/assumption_confidence_checker.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/bdd_runner.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_evidence.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_validator.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/command_failure_classifier.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/command_models.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/criteria_classifier.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/design_protocol.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/exceptions.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/pre_loop.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/security_checker.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/security_detection.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/security_review.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/task_work_interface.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/review_summary.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/schemas.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/sdk_ceiling.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/sdk_debug.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/sdk_utils.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/security_config.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/smoke_gates.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/specialist_invocations.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/state_detection.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/state_tracker.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/synthetic_report.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/visual_comparator.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/worktree_checkpoints.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/planning/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/planning/arch_spec_parser.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/planning/architecture_writer.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/planning/coach_context_builder.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/planning/complexity_gating.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/planning/context_switch.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/planning/design_writer.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/planning/graphiti_arch.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/planning/graphiti_design.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/planning/impact_analysis.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/planning/mode_detector.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/planning/system_overview.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/planning/system_plan.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/tasks/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/tasks/state_bridge.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/tasks/task_loader.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/templates/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/templates/resolver.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/validation/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/validation/ac_validator.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/worktrees/__init__.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/worktrees/manager.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/worktrees/pth_leak_scanner.py']
AI: [{'name': 'glob', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/', 'pattern': '*coach_evidence.py'}, 'id': 'yxvlmc5Koh1YQrypluXscC7t5gJisCp1', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_evidence.py']
AI: [{'name': 'glob', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/', 'pattern': '*coach_evidence*'}, 'id': 'oohwLuPp3EwxTtH6qVFOssk0DgTxX6Am', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/__pycache__/coach_evidence.cpython-312-pytest-9.0.3.pyc', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/__pycache__/coach_evidence.cpython-312.pyc', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_evidence.py']
AI: [{'name': 'glob', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/', 'pattern': '*coach_evidence*'}, 'id': 'b7zdhbUqe1RWzpu1m9FHzmQItbchoWrC', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/__pycache__/coach_evidence.cpython-312-pytest-9.0.3.pyc', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/__pycache__/coach_evidence.cpython-312.pyc', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_evidence.py']
AI: [{'name': 'glob', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/', 'pattern': '**/*coach_evidence.py'}, 'id': 'I2hL5DutYwBc15FXE83rIlpqZ7BtI2Xs', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_evidence.py']
AI: [{'name': 'glob', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/', 'pattern': '**/*coach_evidence.py'}, 'id': 'rvDe0L9eqrB4X8MwBMOS0eyKcr08tEkL', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_evidence.py']
AI: [{'name': 'glob', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/', 'pattern': '**/*coach_evidence.py'}, 'id': 'SK1tzFuHQsgZEqSGLM4a8AjwwBGhEmIV', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_evidence.py']
AI: [{'name': 'glob', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/', 'pattern': '**/*coach_evidence.py'}, 'id': '1NiFj3XToGqakyKLZx9s910qYnXgLSrh', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_evidence.py']
AI: [{'name': 'glob', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/', 'pattern': '**/*coach_evidence.py'}, 'id': 'SLtYjrQwZJzUbHKgdR3SMRafqoKraaVO', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_evidence.py']
AI: [{'name': 'glob', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/', 'pattern': '**/*coach_evidence*'}, 'id': 'UeVCNBw6YD9F4hULuKhZ6acqyPsDDuHP', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/__pycache__/coach_evidence.cpython-312-pytest-9.0.3.pyc', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/__pycache__/coach_evidence.cpython-312.pyc', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_evidence.py']
AI: [{'name': 'glob', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/', 'pattern': '**/*coach_evidence*'}, 'id': 'kSXQs4GqADp1ZWA52sdEehFWRYql53mG', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/__pycache__/coach_evidence.cpython-312-pytest-9.0.3.pyc', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/__pycache__/coach_evidence.cpython-312.pyc', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_evidence.py']
AI: [{'name': 'glob', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/', 'pattern': '**/*coach_evidence*'}, 'id': 'TbCFSWiPp7N2z6RCh7BYsUdhwd4xZeqE', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/__pycache__/coach_evidence.cpython-312-pytest-9.0.3.pyc', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/__pycache__/coach_evidence.cpython-312.pyc', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_evidence.py']
AI: [{'name': 'glob', 'args': {'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/', 'pattern': '**/*coach_evidence*'}, 'id': 'B5vKN1EMPNTb2pLIuHoWfO6geLHbQkaM', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/__pycache__/coach_evidence.cpython-312-pytest-9.0.3.pyc', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/__pycache__/coach_evidence.cpython-312.pyc', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_evidence.py']
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_evidence.py'}, 'id': 'XTz6DVKNHxosSCcsGydJmUhgVyLK6lN5', 'type': 'tool_call'}]
Tool:      1	"""CoachEvidenceBundle — structured evidence supplied by CoachValidator.
     2	
     3	TASK-HMIG-008R Part A (Revision 3, operator-approved 2026-05-20). Restores the
     4	LLM Coach as the primary decision-maker per the Block adversarial-cooperation
     5	paper, demoting CoachValidator from primary decision path to evidence supplier.
     6	
     7	The bundle is produced by ``CoachValidator.gather_evidence(...)`` and consumed
     8	by ``AgentInvoker.invoke_coach(...)`` which renders it into the Coach prompt
     9	via ``_build_coach_prompt(...)``. Every field corresponds to an intermediate
    10	value that the legacy ``CoachValidator.validate()`` method previously consumed
    11	internally to reach approve/feedback decisions. Under the new architecture
    12	those intermediates become read-only evidence the LLM Coach reasons about.
    13	
    14	Design rules (see ``.claude/rules/patterns/dataclasses.md``):
    15	
    16	* Internal value object — no external API boundary, no field-level validation
    17	  constraints, serialised via ``dataclasses.asdict`` + ``json.dumps``.
    18	* All evidence fields are ``Optional[...]`` so the bundle can be returned even
    19	  when one of the gathering stages aborted early.
    20	* ``gathering_status`` disambiguates "field is None because gathering aborted"
    21	  from "field is None because no signal was reported". The absence-of-failure
    22	  guards in the Coach prompt (TASK-HMIG-008R §4) instruct the Coach to treat
    23	  any ``None`` field as ABSENT SIGNAL when ``gathering_status != "complete"``.
    24	
    25	Cross-references:
    26	
    27	* ``.claude/rules/absence-of-failure-is-not-success.md`` — the structural
    28	  rule the LLM-layer guards mirror. Pair-with-attempted-count semantics map
    29	  directly onto the bundle's ``bdd.scenarios_attempted`` / ``tests.tests_run``
    30	  fields.
    31	* ``.claude/rules/path-string-mismatch-is-not-dishonesty.md`` — Layer-1
    32	  identity resolution lives in ``honesty.resolved_paths``; Layer-2 demotion
    33	  hint surfaces in ``severity_recommendations``.
    34	* TASK-REV-HMIG §14.9 (the architectural correction).
    35	"""
    36	
    37	from __future__ import annotations
    38	
    39	from dataclasses import dataclass, field
    40	from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional
    41	
    42	if TYPE_CHECKING:  # pragma: no cover — annotation-only imports
    43	    # Imported under TYPE_CHECKING to avoid the circular dependency
    44	    # coach_validator.py -> coach_evidence.py -> coach_validator.py.
    45	    # Runtime values are duck-typed; the annotations document intent.
    46	    from guardkit.orchestrator.coach_verification import HonestyVerification
    47	    from guardkit.orchestrator.quality_gates.coach_validator import (
    48	        IndependentTestResult,
    49	        QualityGateStatus,
    50	    )
    51	
    52	
    53	GatheringStatus = Literal[
    54	    "complete",
    55	    "partial_honesty_abort",
    56	    "partial_gate_abort",
    57	    "partial_exception",
    58	]
    59	"""Status of the evidence-gathering pipeline.
    60	
    61	* ``complete`` — all gathering stages ran successfully and populated their fields.
    62	* ``partial_honesty_abort`` — honesty verification produced ``must_fix``
    63	  discrepancies; downstream gathering (gates, independent tests, requirements)
    64	  was skipped because the legacy decision tree would have short-circuited here.
    65	  Fields downstream of honesty are ``None``.
    66	* ``partial_gate_abort`` — quality gates failed; downstream gathering
    67	  (independent tests, requirements) was skipped. ``quality_gates`` is populated;
    68	  ``independent_tests`` and ``requirements_*`` fields are ``None``.
    69	* ``partial_exception`` — pre-evidence error (invalid task type, missing
    70	  task_work_results, or unexpected exception in a gathering helper). Inspect
    71	  ``gathering_error`` for the cause.
    72	"""
    73	
    74	
    75	@dataclass
    76	class CoachEvidenceBundle:
    77	    """Structured evidence gathered by CoachValidator for the LLM Coach.
    78	
    79	    Each field maps to an intermediate value the legacy ``validate()`` method
    80	    consumed internally. Under TASK-HMIG-008R the LLM Coach reads this bundle
    81	    (rendered as JSON into the Coach prompt) plus the honesty result and makes
    82	    the final approve/feedback decision.
    83	
    84	    Attributes
    85	    ----------
    86	    honesty
    87	        ``HonestyVerification`` from ``CoachVerifier``. Carries
    88	        ``resolved_paths`` (Layer 1 / TASK-FIX-1B4A) and ``should_fix_count``
    89	        (Layer 2 demotion / TASK-FIX-1B4B). Populated on every non-pre-evidence
    90	        gather path. The Coach reads this field unconditionally.
    91	    gathering_status
    92	        Pipeline status; see :data:`GatheringStatus` for the meaning of each
    93	        value. Used by the Coach to decide whether ``None`` evidence fields
    94	        mean ABSENT SIGNAL (status != "complete") or NO SIGNAL REPORTED
    95	        (status == "complete").
    96	    gathering_error
    97	        Optional human-readable description of what went wrong when
    98	        ``gathering_status == "partial_exception"``. ``None`` on every other
    99	        status. Surfaced verbatim in the synthetic feedback rationale when the
   100	        primary ``_invoke_coach`` path catches an exception around evidence
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_evidence.py', 'limit': 200, 'offset': 100}, 'id': '451ozFy4XnOxB7I9M3UpOoX15QEc25q9', 'type': 'tool_call'}]
Tool:    101	        gathering.
   102	    quality_gates
   103	        ``QualityGateStatus`` aggregate (tests / coverage / arch_review /
   104	        plan_audit). ``None`` when gathering aborted before the gates ran or
   105	        when the task type opts out of all gates.
   106	    coverage_details
   107	        Raw coverage dict slice from ``task_work_results['test_results']``
   108	        (line_coverage, branch_coverage, files_below_threshold). ``None`` when
   109	        coverage was not reported.
   110	    plan_audit
   111	        Plan-audit findings dict from ``task_work_results['plan_audit']``.
   112	        ``None`` when the producer wrote no plan_audit block (e.g.
   113	        ``--implement-only`` without a saved plan).
   114	    bdd
   115	        Raw ``task_work_results['bdd_results']`` dict (scenarios_attempted,
   116	        scenarios_failed, scenarios_passed, scenarios_pending, failures,
   117	        pending, feature_files). ``None`` when no BDD oracle ran. The Coach
   118	        applies the Pattern-2 absence-of-failure guard against
   119	        ``bdd['scenarios_attempted']``.
   120	    arch_review
   121	        Architectural review dict slice (``{"score": int, ...}``). ``None``
   122	        when no Phase 2.5B output was produced.
   123	    tests
   124	        Aggregate test result dict (tests_passed / tests_run /
   125	        line_coverage_met / branch_coverage_met / requires_infrastructure).
   126	        ``None`` when no test_results block was produced. The Coach applies
   127	        the absence-of-failure guard against ``tests['tests_run']``.
   128	    independent_tests
   129	        ``IndependentTestResult`` from Coach's own pytest pass. ``None`` when
   130	        gathering aborted before independent tests or when the task type's
   131	        profile opts out of independent verification.
   132	    requirements
   133	        ``RequirementsValidation`` from ``validate_requirements``. ``None``
   134	        when gathering aborted before requirements validation.
   135	    severity_recommendations
   136	        Structured hints derived from ``_honesty_issues_from`` demotion logic
   137	        (Layer 2). Each hint is ``{"recommendation": str, "rule": str}``. The
   138	        Coach reads these to know when to demote ``file_existence``
   139	        discrepancies from ``must_fix`` to ``should_fix``.
   140	    task_type
   141	        Resolved task type string (e.g. ``"feature"``, ``"refactor"``,
   142	        ``"scaffolding"``). ``None`` when task type could not be resolved
   143	        (``partial_exception`` with invalid_task_type cause).
   144	    profile_name
   145	        Quality-gate profile name string. ``None`` on the same paths as
   146	        ``task_type``.
   147	    advisory_issues
   148	        Non-blocking issues that ride along with the final decision regardless
   149	        of approve/feedback outcome. Currently sourced from:
   150	
   151	        * Agent-invocations advisory (TASK-REV-F6E1 F3c) — process observation,
   152	          ``severity == "warning"``.
   153	        * Layer-2-demoted honesty ``should_fix`` issues — content observation,
   154	          ``severity == "should_fix"``.
   155	
   156	        Pre-populated so the LLM Coach can read them without re-computing the
   157	        Layer-2 demotion.
   158	    wiring
   159	        UNWIRED_PATH analysis result (dict) from ``guardkitfactory.wiring``.
   160	        Contains ``status``, ``dialect``, ``language``, ``targets_scanned``,
   161	        ``symbols_examined``, ``findings``, ``degraded_files``. ``None`` when
   162	        the task type gates out (SCAFFOLDING/DOCUMENTATION), there are no
   163	        authored source targets, or the factory is unavailable.
   164	    mocked_seam
   165	        MOCKED_SEAM analysis result (dict). Contains ``status``, ``ran``,
   166	        ``dialect``, ``findings``, ``external_mocks_ignored``. ``None`` when
   167	        the task type gates out, there are no authored acceptance files, or
   168	        the factory is unavailable.
   169	    spec_gap
   170	        SPEC_GAP analysis result (dict). Contains ``status``,
   171	        ``ground_truth_count``, ``executed_count``, ``findings``,
   172	        ``whole_file_deselection``. ``None`` when the task type gates out,
   173	        the factory BDD plugin is unavailable, or Wave-3 wiring is not yet
   174	        implemented.
   175	    """
   176	
   177	    honesty: "HonestyVerification"
   178	    gathering_status: GatheringStatus = "complete"
   179	    gathering_error: Optional[str] = None
   180	
   181	    quality_gates: Optional["QualityGateStatus"] = None
   182	    coverage_details: Optional[Dict[str, Any]] = None
   183	    plan_audit: Optional[Dict[str, Any]] = None
   184	    bdd: Optional[Dict[str, Any]] = None
   185	    arch_review: Optional[Dict[str, Any]] = None
   186	    tests: Optional[Dict[str, Any]] = None
   187	
   188	    # Wave-1 wiring evidence fields (TASK-QAWE-002).
   189	    # Populated by CoachValidator.gather_evidence at the complete-path return.
   190	    # Left None for SCAFFOLDING/DOCUMENTATION tasks, zero-target turns,
   191	    # or when guardkitfactory.wiring is unavailable (ImportError).
   192	    wiring: Optional[Dict[str, Any]] = None         # UNWIRED_PATH analysis
   193	    mocked_seam: Optional[Dict[str, Any]] = None    # MOCKED_SEAM analysis
   194	    spec_gap: Optional[Dict[str, Any]] = None       # SPEC_GAP (Wave-3)
   195	
   196	    independent_tests: Optional["IndependentTestResult"] = None
   197	    requirements: Optional[Any] = None  # RequirementsValidation; avoid circular import
   198	
   199	    severity_recommendations: List[Dict[str, str]] = field(default_factory=list)
   200	    advisory_issues: List[Dict[str, Any]] = field(default_factory=list)
   201	
   202	    task_type: Optional[str] = None
   203	    profile_name: Optional[str] = None
   204	
   205	    def to_dict(self) -> Dict[str, Any]:
   206	        """Serialise the bundle to a JSON-compatible dict.
   207	
   208	        Nested ``HonestyVerification`` / ``QualityGateStatus`` /
   209	        ``IndependentTestResult`` / ``RequirementsValidation`` instances are
   210	        also dataclasses, so ``dataclasses.asdict`` walks the entire tree.
   211	        ``ResolvedPath`` / ``Discrepancy`` inside ``HonestyVerification`` are
   212	        also dataclasses — the whole bundle is safe for ``json.dumps``.
   213	        """
   214	        from dataclasses import asdict
   215	
   216	        return asdict(self)
AI: [{'name': 'grep', 'args': {'glob': 'guardkit/orchestrator/quality_gates/coach_validator.py', 'pattern': 'gather_evidence'}, 'id': 'aBN0alrppmMhGi1TMOuXOjWruGCPdg7i', 'type': 'tool_call'}]
Tool: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_validator.py
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 500, 'offset': 1800}, 'id': 'NJqaLRmUof8XkwrmPkrWJz8FhK5gFh5m', 'type': 'tool_call'}]
Tool:   1801	                        f"infrastructure failure ({failure_class}/{failure_confidence}) "
  1802	                        f"on a known-broken bootstrap; all Player gates passed. "
  1803	                        f"Marking approved with environment flag."
  1804	                    )
  1805	                elif failure_class == "collection_error":
  1806	                    logger.warning(
  1807	                        f"Conditional approval for {task_id}: test collection errors in "
  1808	                        f"independent verification, all Player gates passed. "
  1809	                        f"Continuing to requirements check."
  1810	                    )
  1811	                elif failure_class == "parallel_contention":
  1812	                    logger.warning(
  1813	                        f"Conditional approval for {task_id}: parallel contention failure "
  1814	                        f"(wave_size={self.wave_size}), all Player gates passed. "
  1815	                        f"Continuing to requirements check."
  1816	                    )
  1817	                elif failure_class == "code" and self.is_parallel:
  1818	                    logger.warning(
  1819	                        f"Conditional approval for {task_id}: code failure in parallel wave "
  1820	                        f"(wave_size={self.wave_size}), all Player gates passed. "
  1821	                        f"Continuing to requirements check."
  1822	                    )
  1823	                else:
  1824	                    logger.warning(
  1825	                        f"Conditional approval for {task_id}: infrastructure failure "
  1826	                        f"with declared deps {requires_infra}, Docker unavailable. "
  1827	                        f"Continuing to requirements check."
  1828	                    )
  1829	                # Fall through to requirements check with conditional flag set
  1830	            else:
  1831	                # Check for psycopg2/asyncpg mismatch before falling back to
  1832	                # generic infrastructure feedback (TASK-FIX-4415).
  1833	                if self._is_psycopg2_asyncpg_mismatch(test_result.raw_output, task):
  1834	                    description = (
  1835	                        "ModuleNotFoundError for 'psycopg2' — this project uses "
  1836	                        "asyncpg. Remove `import psycopg2` from your code and use "
  1837	                        "asyncpg-compatible database patterns instead."
  1838	                    )
  1839	                    rationale = (
  1840	                        "Tests failed because psycopg2 was imported in an asyncpg "
  1841	                        "project"
  1842	                    )
  1843	                elif (
  1844	                    is_parallel_contention_class
  1845	                    and source_file_contention_overlaps
  1846	                ):
  1847	                    # TASK-FIX-A7B2: Source-file contention with at least one
  1848	                    # peer in the same wave. Name the overlapping files so the
  1849	                    # Player can resolve the conflict on retry. The retry will
  1850	                    # be naturally serialised — by the time the Player runs
  1851	                    # its next turn, peers have completed and the wave is
  1852	                    # effectively single-tasked.
  1853	                    error_output = (test_result.test_output_summary or "").strip()
  1854	                    if len(error_output) > 500:
  1855	                        error_output = error_output[:497] + "..."
  1856	                    overlap_lines = []
  1857	                    for peer_id in sorted(source_file_contention_overlaps):
  1858	                        files = sorted(source_file_contention_overlaps[peer_id])
  1859	                        overlap_lines.append(
  1860	                            f"  - {peer_id}: {', '.join(files)}"
  1861	                        )
  1862	                    overlap_block = "\n".join(overlap_lines)
  1863	                    base = (
  1864	                        f"Tests failed due to source-file contention with peer "
  1865	                        f"task(s) in this parallel wave (wave_size={self.wave_size}). "
  1866	                        f"Both this task and the peer(s) below edited the same "
  1867	                        f"source file(s); the resulting shared-branch state is "
  1868	                        f"inconsistent and an isolation-snapshot retry cannot "
  1869	                        f"recover it. Resolve the conflict on the next turn — "
  1870	                        f"by then the peer(s) will have completed and the wave "
  1871	                        f"is effectively serialised.\n"
  1872	                        f"Overlapping files by peer:\n{overlap_block}\n"
  1873	                        f"Test command: {test_result.test_command}."
  1874	                    )
  1875	                    description = (
  1876	                        f"{base} Error detail: {error_output}"
  1877	                        if error_output
  1878	                        else base
  1879	                    )
  1880	                    rationale = (
  1881	                        "Tests failed due to source-file contention with peer "
  1882	                        "wave tasks (real correctness damage, not transient "
  1883	                        "infra contention) — see TASK-FIX-A7B2"
  1884	                    )
  1885	                elif failure_class == "parallel_contention":
  1886	                    error_output = (test_result.test_output_summary or "").strip()
  1887	                    if len(error_output) > 500:
  1888	                        error_output = error_output[:497] + "..."
  1889	                    base = (
  1890	                        f"Tests failed due to likely parallel wave contention "
  1891	                        f"(wave_size={self.wave_size}). Another task may have "
  1892	                        f"concurrently modified shared files (e.g. __init__.py) "
  1893	                        f"during Coach independent verification. "
  1894	                        f"Test command: {test_result.test_command}."
  1895	                    )
  1896	                    description = (
  1897	                        f"{base} Error detail: {error_output}"
  1898	                        if error_output
  1899	                        else base
  1900	                    )
  1901	                    rationale = (
  1902	                        "Tests failed due to likely parallel wave contention, "
  1903	                        "not code defects"
  1904	                    )
  1905	                elif failure_class in ("infrastructure", "collection_error"):
  1906	                    error_output = (test_result.test_output_summary or "").strip()
  1907	                    if len(error_output) > 500:
  1908	                        error_output = error_output[:497] + "..."
  1909	                    base = (
  1910	                        "Tests failed due to infrastructure/environment issues "
  1911	                        f"(not code defects). Test command: {test_result.test_command}. "
  1912	                        "Remediation options: "
  1913	                        "(1) Add mock fixtures for external services, "
  1914	                        "(2) Use SQLite for test database, "
  1915	                        "(3) Mark integration tests with @pytest.mark.integration "
  1916	                        "and exclude via -m 'not integration'."
  1917	                    )
  1918	                    description = (
  1919	                        f"{base} Error detail: {error_output}"
  1920	                        if error_output
  1921	                        else base
  1922	                    )
  1923	                    rationale = (
  1924	                        "Tests failed due to infrastructure/environment issues, "
  1925	                        "not code defects"
  1926	                    )
  1927	                else:
  1928	                    description = "Independent test verification failed"
  1929	                    rationale = (
  1930	                        "Tests passed according to task-work but failed on "
  1931	                        "independent verification"
  1932	                    )
  1933	
  1934	                return self._feedback_result(
  1935	                    task_id=task_id,
  1936	                    turn=turn,
  1937	                    quality_gates=gates_status,
  1938	                    independent_tests=test_result,
  1939	                    issues=advisory_issues + [{
  1940	                        "severity": "must_fix",
  1941	                        "category": "test_verification",
  1942	                        "description": description,
  1943	                        "test_output": test_result.test_output_summary,
  1944	                        "failure_classification": failure_class,
  1945	                        "failure_confidence": failure_confidence,
  1946	                    }],
  1947	                    rationale=rationale,
  1948	                    context_used=context,
  1949	                    honesty_verification=honesty_verification,
  1950	                )
  1951	
  1952	        # 4. Validate requirements satisfaction (already hoisted above —
  1953	        # see TASK-GK-CR-001).
  1954	        if not requirements.all_criteria_met:
  1955	            logger.info(f"Requirements not met for {task_id}: missing {requirements.missing}")
  1956	            return self._feedback_result(
  1957	                task_id=task_id,
  1958	                turn=turn,
  1959	                quality_gates=gates_status,
  1960	                independent_tests=test_result,
  1961	                requirements=requirements,
  1962	                issues=advisory_issues + [{
  1963	                    "severity": "must_fix",
  1964	                    "category": "missing_requirement",
  1965	                    "description": f"Not all acceptance criteria met",
  1966	                    "missing_criteria": requirements.missing,
  1967	                }],
  1968	                rationale=f"Missing {len(requirements.missing)} acceptance criteria: {', '.join(requirements.missing)}",
  1969	                context_used=context,
  1970	                honesty_verification=honesty_verification,
  1971	            )
  1972	
  1973	        # 5. Check for blocking zero-test anomaly before approval
  1974	        zero_test_issues = self._check_zero_test_anomaly(
  1975	            task_work_results, profile, independent_tests=test_result,
  1976	            task_id=task_id,
  1977	        )
  1978	        has_blocking_zero_test = any(
  1979	            issue.get("severity") == "error" for issue in zero_test_issues
  1980	        )
  1981	
  1982	        if has_blocking_zero_test:
  1983	            logger.info(f"Coach rejected {task_id} turn {turn}: zero-test anomaly (blocking)")
  1984	            return self._feedback_result(
  1985	                task_id=task_id,
  1986	                turn=turn,
  1987	                quality_gates=gates_status,
  1988	                independent_tests=test_result,
  1989	                requirements=requirements,
  1990	                issues=advisory_issues + zero_test_issues,
  1991	                rationale=(
  1992	                    "Zero-test anomaly detected: quality gates reported as passed but "
  1993	                    "no tests were executed. Tests are required for this task type. "
  1994	                    "Please write and run tests before resubmitting."
  1995	                ),
  1996	                context_used=context,
  1997	                honesty_verification=honesty_verification,
  1998	            )
  1999	
  2000	        # 5.5. Check for seam test recommendations (soft gate, non-blocking)
  2001	        seam_test_issues = self._check_seam_test_recommendation(
  2002	            task_work_results, profile
  2003	        )
  2004	
  2005	        # 5.6. Validate consumer_context format constraints (soft gate, non-blocking)
  2006	        consumer_context_issues = self._validate_consumer_context(
  2007	            task, task_work_results
  2008	        )
  2009	
  2010	        # 5.65. Unconfirmed low-confidence assumptions (TASK-FIX-RWOP1.4a).
  2011	        # Warn-mode gate: feature-spec.md:337 says Coach verifies
  2012	        # low-confidence assumptions before accepting a spec. The producer
  2013	        # (AgentInvoker._write_task_work_results) writes the block;
  2014	        # here we surface it as a non-blocking warning so the human
  2015	        # reviewing the merge sees it. Escalation to block-mode is a
  2016	        # separate task driven by evidence that warn-mode is being ignored.
  2017	        assumption_issues = self._check_unconfirmed_assumptions(
  2018	            task_work_results
  2019	        )
  2020	
  2021	        # 5.7. BDD oracle gate (TASK-BDD-E8954): when present in task_work_results,
  2022	        # scenarios_failed > 0 blocks approval. scenarios_pending is informational
  2023	        # and surfaces in feedback without blocking — see bdd_runner module docstring
  2024	        # for the three-state model and rationale for not collapsing pending into
  2025	        # failed.
  2026	        bdd_blocking, bdd_non_blocking = self._check_bdd_results(task_work_results)
  2027	        if bdd_blocking:
  2028	            logger.info(
  2029	                f"Coach rejected {task_id} turn {turn}: bdd_results.scenarios_failed > 0"
  2030	            )
  2031	            return self._feedback_result(
  2032	                task_id=task_id,
  2033	                turn=turn,
  2034	                quality_gates=gates_status,
  2035	                independent_tests=test_result,
  2036	                requirements=requirements,
  2037	                issues=advisory_issues + bdd_blocking + bdd_non_blocking,
  2038	                rationale=(
  2039	                    "BDD scenarios failed: "
  2040	                    f"{task_work_results.get('bdd_results', {}).get('scenarios_failed', 0)} "
  2041	                    "scenario(s) reported assertion failure during pytest-bdd execution."
  2042	                ),
  2043	                context_used=context,
  2044	                honesty_verification=honesty_verification,
  2045	            )
  2046	
  2047	        # 5.8. Seam tests blocking gate (TASK-FIX-A7B4).
  2048	        # Distinct from the soft `_check_seam_test_recommendation` above:
  2049	        # this gate fires only when the task description itself contains a
  2050	        # non-empty `## Seam Tests` section AND the Player wrote zero tests
  2051	        # carrying @pytest.mark.{seam,contract,boundary}. Detected before
  2052	        # approval, after the BDD blocker, so the rest of this turn's gates
  2053	        # have already filtered out lower-quality failure modes.
  2054	        seam_blocking = self._check_seam_tests_implemented(task, task_work_results)
  2055	        if seam_blocking:
  2056	            logger.info(
  2057	                f"Coach rejected {task_id} turn {turn}: "
  2058	                "task description specifies seam tests but Player wrote none"
  2059	            )
  2060	            return self._feedback_result(
  2061	                task_id=task_id,
  2062	                turn=turn,
  2063	                quality_gates=gates_status,
  2064	                independent_tests=test_result,
  2065	                requirements=requirements,
  2066	                issues=advisory_issues + seam_blocking,
  2067	                rationale=(
  2068	                    "Seam tests gate: task description specifies a "
  2069	                    "non-empty `## Seam Tests` section but no "
  2070	                    "@pytest.mark.{seam,contract,boundary} tests were "
  2071	                    "written. Implement the seam test stub before "
  2072	                    "resubmitting."
  2073	                ),
  2074	                context_used=context,
  2075	                honesty_verification=honesty_verification,
  2076	            )
  2077	
  2078	        # Combine all non-blocking issues. The agent_invocations advisory
  2079	        # (F3c) rides along here on the approval path so the Player still
  2080	        # sees the process observation even when outcome gates approve.
  2081	        all_issues = (
  2082	            advisory_issues
  2083	            + zero_test_issues
  2084	            + seam_test_issues
  2085	            + consumer_context_issues
  2086	            + assumption_issues
  2087	            + bdd_non_blocking
  2088	        )
  2089	
  2090	        # 6. All checks passed - approve
  2091	        if conditional_approval:
  2092	            if failure_class == "collection_error":
  2093	                logger.warning(
  2094	                    f"Coach conditionally approved {task_id} turn {turn}: "
  2095	                    f"test collection errors in independent verification, all gates passed"
  2096	                )
  2097	            else:
  2098	                logger.warning(
  2099	                    f"Coach conditionally approved {task_id} turn {turn}: "
  2100	                    f"infrastructure-dependent, independent tests skipped"
  2101	                )
  2102	        else:
  2103	            logger.info(f"Coach approved {task_id} turn {turn}")
  2104	
  2105	        # Build accurate rationale based on actual verification status
  2106	        rationale = self._build_approval_rationale(
  2107	            test_result=test_result,
  2108	            gates_status=gates_status,
  2109	            task_work_results=task_work_results,
  2110	            profile=profile,
  2111	            context=context,
  2112	            conditional_approval=conditional_approval,
  2113	            failure_class=failure_class,
  2114	            environment_conditional_approval=environment_conditional_approval,
  2115	        )
  2116	
  2117	        return CoachValidationResult(
  2118	            task_id=task_id,
  2119	            turn=turn,
  2120	            decision="approve",
  2121	            quality_gates=gates_status,
  2122	            independent_tests=test_result,
  2123	            requirements=requirements,
  2124	            issues=all_issues,
  2125	            rationale=rationale,
  2126	            context_used=context,
  2127	            approved_without_independent_tests=conditional_approval,
  2128	            environment_conditional_approval=environment_conditional_approval,
  2129	            honesty_verification=honesty_verification,
  2130	        )
  2131	
  2132	    def gather_evidence(
  2133	        self,
  2134	        task_id: str,
  2135	        turn: int,
  2136	        task: Dict[str, Any],
  2137	        skip_arch_review: bool = False,
  2138	        context: Optional[str] = None,
  2139	    ) -> CoachEvidenceBundle:
  2140	        """Gather structured evidence for the LLM Coach (TASK-HMIG-008R Part A).
  2141	
  2142	        Runs the same deterministic gathering pipeline the legacy
  2143	        ``validate()`` method uses internally, but packages the results into a
  2144	        :class:`CoachEvidenceBundle` instead of applying decision logic. The
  2145	        LLM Coach reads this bundle (rendered as JSON into the Coach prompt by
  2146	        ``_build_coach_prompt``) plus the honesty result and makes the final
  2147	        approve/feedback decision per the Block adversarial-cooperation paper.
  2148	
  2149	        The pipeline aborts early under three conditions, leaving downstream
  2150	        fields as ``None`` and setting ``bundle.gathering_status`` so the
  2151	        Coach's absence-of-failure guards know to treat the ``None`` fields
  2152	        as ABSENT SIGNAL:
  2153	
  2154	        * Pre-evidence error (invalid task type, missing task_work_results,
  2155	          or an unexpected exception in a gathering helper) →
  2156	          ``"partial_exception"`` with a human-readable cause in
  2157	          ``bundle.gathering_error``.
  2158	        * Honesty verification produced ``must_fix`` discrepancies →
  2159	          ``"partial_honesty_abort"``. Gates and independent tests are not
  2160	          run because the legacy decision tree would have short-circuited
  2161	          here too — the LLM Coach reaches the same conclusion by reading
  2162	          ``bundle.honesty.discrepancies``.
  2163	        * Quality gates failed → ``"partial_gate_abort"``. Independent
  2164	          tests / requirements validation are not run. The LLM Coach
  2165	          reaches a feedback decision by reading ``bundle.quality_gates``.
  2166	
  2167	        Per the Phase 2.5 architectural review and §3 "Exception handling
  2168	        for gather_evidence" in the implementation plan, this method MUST
  2169	        NOT raise to its caller. Wrapping inner helper exceptions in a
  2170	        ``partial_exception`` bundle prevents an exception fallback to
  2171	        ``validate()`` from re-activating the primary decision path that
  2172	        falsifier #1 ("CoachValidator.validate() for the decision is GONE")
  2173	        requires to be gone. ``GUARDKIT_COACH_LEGACY=1`` remains the sole
  2174	        operator-controlled mechanism for re-activating ``validate()``.
  2175	
  2176	        Parameters
  2177	        ----------
  2178	        task_id : str
  2179	            Task identifier (e.g., ``"TASK-001"``). Used to read
  2180	            ``task_work_results.json`` from the standard autobuild path and
  2181	            to wire state-bridge identity resolution into the honesty
  2182	            verifier (TASK-FIX-1B4A Layer 1).
  2183	        turn : int
  2184	            Current turn number (1-based). Passed to
  2185	            ``validate_requirements`` and ``run_independent_tests``.
  2186	        task : Dict[str, Any]
  2187	            Task data dict. Must contain ``acceptance_criteria`` and may
  2188	            contain ``task_type``, ``requires_infrastructure``,
  2189	            ``_docker_available``, ``consumer_context``, ``description``.
  2190	        skip_arch_review : bool, optional
  2191	            If ``True``, the architectural-review gate is skipped regardless
  2192	            of the profile setting. Used for ``--implement-only`` mode where
  2193	            Phase 2.5B did not run. Default: ``False``.
  2194	        context : Optional[str], optional
  2195	            Optional Graphiti / coach context string. Not currently consumed
  2196	            by gather_evidence itself; threaded through for symmetry with
  2197	            ``validate()``'s signature so the legacy shim (when AC-003 is
  2198	            completed in a follow-up) can pass it forward.
  2199	
  2200	        Returns
  2201	        -------
  2202	        CoachEvidenceBundle
  2203	            Populated evidence bundle. Always returned; never raises.
  2204	        """
  2205	        default_honest = HonestyVerification(verified=True)
  2206	
  2207	        # ------------------------------------------------------------------
  2208	        # Pre-evidence: resolve task type. Mirrors validate() lines 821-838.
  2209	        # ------------------------------------------------------------------
  2210	        try:
  2211	            task_type = self._resolve_task_type(task)
  2212	        except ValueError as exc:
  2213	            logger.error(
  2214	                "gather_evidence: failed to resolve task type: %s", exc
  2215	            )
  2216	            return CoachEvidenceBundle(
  2217	                honesty=default_honest,
  2218	                gathering_status="partial_exception",
  2219	                gathering_error=f"invalid_task_type: {exc}",
  2220	            )
  2221	
  2222	        try:
  2223	            profile = get_profile(task_type)
  2224	        except Exception as exc:  # noqa: BLE001 — defensive; get_profile is total
  2225	            logger.error(
  2226	                "gather_evidence: failed to load profile for %s: %s",
  2227	                task_type, exc,
  2228	            )
  2229	            return CoachEvidenceBundle(
  2230	                honesty=default_honest,
  2231	                gathering_status="partial_exception",
  2232	                gathering_error=f"missing_profile: {exc}",
  2233	                task_type=task_type.value,
  2234	            )
  2235	
  2236	        profile_name = getattr(profile, "name", None) or task_type.value
  2237	
  2238	        # OPERATOR_HANDOFF: no evidence to gather. The legacy validate() returns
  2239	        # decision="deferred" here; gather_evidence reports a clean status so
  2240	        # the LLM Coach prompt sees an empty bundle with the task_type marker.
  2241	        # The Part B / Part C wiring is responsible for short-circuiting the
  2242	        # Coach invocation for operator-handoff tasks at the autobuild layer
  2243	        # (the same place the legacy validate() returned deferred).
  2244	        if task_type == TaskType.OPERATOR_HANDOFF:
  2245	            logger.info(
  2246	                "gather_evidence: skipping evidence collection for "
  2247	                "operator_handoff task %s (runtime verification deferred to "
  2248	                "operator)", task_id,
  2249	            )
  2250	            return CoachEvidenceBundle(
  2251	                honesty=default_honest,
  2252	                gathering_status="complete",
  2253	                task_type=task_type.value,
  2254	                profile_name=profile_name,
  2255	            )
  2256	
  2257	        # ------------------------------------------------------------------
  2258	        # Pre-evidence: read task_work_results. Mirrors validate() lines 875-895.
  2259	        # ------------------------------------------------------------------
  2260	        task_work_results = self.read_quality_gate_results(task_id)
  2261	        if "error" in task_work_results:
  2262	            logger.warning(
  2263	                "gather_evidence: task-work results missing for %s: %s",
  2264	                task_id, task_work_results.get("error", "unknown"),
  2265	            )
  2266	            return CoachEvidenceBundle(
  2267	                honesty=default_honest,
  2268	                gathering_status="partial_exception",
  2269	                gathering_error=(
  2270	                    f"missing_results: {task_work_results.get('error', 'unknown')}"
  2271	                ),
  2272	                task_type=task_type.value,
  2273	                profile_name=profile_name,
  2274	            )
  2275	
  2276	        # ------------------------------------------------------------------
  2277	        # 1. Honesty verification. Mirrors validate() lines 918-952.
  2278	        # ------------------------------------------------------------------
  2279	        try:
  2280	            honesty = self._verify_honesty(task_work_results)
  2281	        except Exception as exc:  # noqa: BLE001
  2282	            logger.error(
  2283	                "gather_evidence: _verify_honesty raised unexpectedly: %s", exc,
  2284	            )
  2285	            return CoachEvidenceBundle(
  2286	                honesty=default_honest,
  2287	                gathering_status="partial_exception",
  2288	                gathering_error=f"honesty_exception: {exc}",
  2289	                task_type=task_type.value,
  2290	                profile_name=profile_name,
  2291	            )
  2292	
  2293	        honesty_issues = self._honesty_issues_from(honesty)
  2294	        honesty_must_fix = [
  2295	            i for i in honesty_issues if i["severity"] == "must_fix"
  2296	        ]
  2297	        honesty_should_fix = [
  2298	            i for i in honesty_issues if i["severity"] == "should_fix"
  2299	        ]
  2300	
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 500, 'offset': 2250}, 'id': 'bPagjQCCJr5xT4anPg1HLPBFCZo9rl8R', 'type': 'tool_call'}]
Tool:   2251	                honesty=default_honest,
  2252	                gathering_status="complete",
  2253	                task_type=task_type.value,
  2254	                profile_name=profile_name,
  2255	            )
  2256	
  2257	        # ------------------------------------------------------------------
  2258	        # Pre-evidence: read task_work_results. Mirrors validate() lines 875-895.
  2259	        # ------------------------------------------------------------------
  2260	        task_work_results = self.read_quality_gate_results(task_id)
  2261	        if "error" in task_work_results:
  2262	            logger.warning(
  2263	                "gather_evidence: task-work results missing for %s: %s",
  2264	                task_id, task_work_results.get("error", "unknown"),
  2265	            )
  2266	            return CoachEvidenceBundle(
  2267	                honesty=default_honest,
  2268	                gathering_status="partial_exception",
  2269	                gathering_error=(
  2270	                    f"missing_results: {task_work_results.get('error', 'unknown')}"
  2271	                ),
  2272	                task_type=task_type.value,
  2273	                profile_name=profile_name,
  2274	            )
  2275	
  2276	        # ------------------------------------------------------------------
  2277	        # 1. Honesty verification. Mirrors validate() lines 918-952.
  2278	        # ------------------------------------------------------------------
  2279	        try:
  2280	            honesty = self._verify_honesty(task_work_results)
  2281	        except Exception as exc:  # noqa: BLE001
  2282	            logger.error(
  2283	                "gather_evidence: _verify_honesty raised unexpectedly: %s", exc,
  2284	            )
  2285	            return CoachEvidenceBundle(
  2286	                honesty=default_honest,
  2287	                gathering_status="partial_exception",
  2288	                gathering_error=f"honesty_exception: {exc}",
  2289	                task_type=task_type.value,
  2290	                profile_name=profile_name,
  2291	            )
  2292	
  2293	        honesty_issues = self._honesty_issues_from(honesty)
  2294	        honesty_must_fix = [
  2295	            i for i in honesty_issues if i["severity"] == "must_fix"
  2296	        ]
  2297	        honesty_should_fix = [
  2298	            i for i in honesty_issues if i["severity"] == "should_fix"
  2299	        ]
  2300	
  2301	        # Layer-2 demotion hint for the LLM Coach. Mirrors the structural
  2302	        # condition inside _honesty_issues_from (lines 5456-5460): a single
  2303	        # critical file_existence discrepancy that was Layer-1-resolved (via
  2304	        # state_bridge.canonical_path_for) is demoted from must_fix to
  2305	        # should_fix. Surface that hint structurally so the LLM Coach can
  2306	        # apply absence-of-failure guard #4 without re-deriving the demotion.
  2307	        severity_recommendations: List[Dict[str, str]] = []
  2308	        critical_discrepancies = [
  2309	            d for d in honesty.discrepancies if d.severity == "critical"
  2310	        ]
  2311	        non_audit_critical = [
  2312	            d for d in critical_discrepancies
  2313	            if d.claim_type != "claim_audit"
  2314	        ]
  2315	        if (
  2316	            len(non_audit_critical) == 1
  2317	            and non_audit_critical[0].claim_type == "file_existence"
  2318	        ):
  2319	            severity_recommendations.append({
  2320	                "recommendation": (
  2321	                    "A single file_existence discrepancy was suppressed by "
  2322	                    "Layer-1 identity resolution (state_bridge "
  2323	                    "canonical_path_for). Treat as should_fix, not must_fix. "
  2324	                    "Continue AC evaluation."
  2325	                ),
  2326	                "rule": (
  2327	                    "path-string-mismatch-is-not-dishonesty "
  2328	                    "(Layer 2 demotion)"
  2329	                ),
  2330	            })
  2331	
  2332	        # Advisory issues: agent-invocations advisory (F3c) + Layer-2 honesty
  2333	        # should_fix issues. Both ride along with the final decision (approve
  2334	        # or feedback) and are surfaced to the Player so process observations
  2335	        # remain visible. Pre-computed here so the LLM Coach can read them
  2336	        # without re-deriving from raw fields.
  2337	        advisory_issues: List[Dict[str, Any]] = []
  2338	        agent_invocations_advisory = (
  2339	            self._compute_agent_invocations_advisory(task_work_results)
  2340	        )
  2341	        if agent_invocations_advisory is not None:
  2342	            advisory_issues.append(agent_invocations_advisory)
  2343	        advisory_issues.extend(honesty_should_fix)
  2344	
  2345	        # Honesty short-circuit: don't run downstream gathering. Legacy
  2346	        # validate() also short-circuits here.
  2347	        if honesty_must_fix:
  2348	            logger.warning(
  2349	                "gather_evidence: honesty produced %d must_fix issue(s) "
  2350	                "for %s; downstream gathering skipped.",
  2351	                len(honesty_must_fix), task_id,
  2352	            )
  2353	            return CoachEvidenceBundle(
  2354	                honesty=honesty,
  2355	                gathering_status="partial_honesty_abort",
  2356	                severity_recommendations=severity_recommendations,
  2357	                advisory_issues=advisory_issues,
  2358	                task_type=task_type.value,
  2359	                profile_name=profile_name,
  2360	            )
  2361	
  2362	        # ------------------------------------------------------------------
  2363	        # 2. Quality gates. Mirrors validate() lines 1130-1132.
  2364	        # ------------------------------------------------------------------
  2365	        try:
  2366	            gates = self.verify_quality_gates(
  2367	                task_work_results,
  2368	                profile=profile,
  2369	                skip_arch_review=skip_arch_review,
  2370	            )
  2371	        except Exception as exc:  # noqa: BLE001
  2372	            logger.error(
  2373	                "gather_evidence: verify_quality_gates raised: %s", exc,
  2374	            )
  2375	            return CoachEvidenceBundle(
  2376	                honesty=honesty,
  2377	                gathering_status="partial_exception",
  2378	                gathering_error=f"quality_gates_exception: {exc}",
  2379	                severity_recommendations=severity_recommendations,
  2380	                advisory_issues=advisory_issues,
  2381	                task_type=task_type.value,
  2382	                profile_name=profile_name,
  2383	            )
  2384	
  2385	        # Build the evidence dict slices the LLM Coach reads.
  2386	        quality_gates_raw = task_work_results.get("quality_gates")
  2387	        if not isinstance(quality_gates_raw, dict):
  2388	            quality_gates_raw = {}
  2389	
  2390	        coverage_details: Dict[str, Any] = {
  2391	            "coverage_met": quality_gates_raw.get("coverage_met"),
  2392	            "line_coverage": quality_gates_raw.get("line_coverage"),
  2393	            "branch_coverage": quality_gates_raw.get("branch_coverage"),
  2394	            "line_threshold": quality_gates_raw.get("line_threshold"),
  2395	            "branch_threshold": quality_gates_raw.get("branch_threshold"),
  2396	            "coverage_required": gates.coverage_required,
  2397	        }
  2398	
  2399	        tests_dict: Dict[str, Any] = {
  2400	            "tests_passed": gates.tests_passed,
  2401	            "tests_required": gates.tests_required,
  2402	            "tests_run": quality_gates_raw.get("tests_run"),
  2403	            "tests_failed": quality_gates_raw.get("tests_failed"),
  2404	            "all_passed": quality_gates_raw.get("all_passed"),
  2405	            "requires_infrastructure": task.get("requires_infrastructure"),
  2406	        }
  2407	
  2408	        plan_audit_raw = task_work_results.get("plan_audit")
  2409	        plan_audit_dict: Optional[Dict[str, Any]] = (
  2410	            plan_audit_raw if isinstance(plan_audit_raw, dict) else None
  2411	        )
  2412	
  2413	        code_review_raw = task_work_results.get("code_review")
  2414	        arch_review_dict: Optional[Dict[str, Any]] = None
  2415	        if isinstance(code_review_raw, dict):
  2416	            arch_review_dict = {
  2417	                "score": code_review_raw.get("score"),
  2418	                "threshold": getattr(profile, "arch_review_threshold", 60),
  2419	                "passed": gates.arch_review_passed,
  2420	                "required": gates.arch_review_required,
  2421	            }
  2422	            # Surface any sub-scores the producer wrote (solid/dry/yagni).
  2423	            for sub in ("solid_score", "dry_score", "yagni_score"):
  2424	                if sub in code_review_raw:
  2425	                    arch_review_dict[sub] = code_review_raw[sub]
  2426	
  2427	        # ------------------------------------------------------------------
  2428	        # BDD evidence. TASK-BDDW-001: wire factory BDD plugin discovery
  2429	        # into the Coach evidence path.
  2430	        #
  2431	        # Priority:
  2432	        #   1. Factory discovery (guardkitfactory.bdd.discover) — if available
  2433	        #      and stack profile is known, run the BDD plugin and map the
  2434	        #      result into bundle.bdd shape.
  2435	        #   2. Player-reported bdd_results — legacy fallback when the factory
  2436	        #      is unavailable, the stack is unknown, or discovery fails.
  2437	        # ------------------------------------------------------------------
  2438	        _reset_factory_cache()
  2439	        _reset_wiring_factory_cache()
  2440	
  2441	        bdd_raw = task_work_results.get("bdd_results")
  2442	        bdd_dict: Optional[Dict[str, Any]] = None
  2443	
  2444	        if bdd_raw is not None and isinstance(bdd_raw, dict):
  2445	            # Player already produced BDD results — use them as-is.
  2446	            bdd_dict = bdd_raw
  2447	        elif _is_factory_available():
  2448	            # Factory is available but Player didn't produce results.
  2449	            # Attempt independent discovery via the factory plugin.
  2450	            stack_profile = _detect_stack_profile(self.worktree_path)
  2451	            factory_result = _run_factory_bdd(self.worktree_path, stack_profile)
  2452	            if factory_result is not None:
  2453	                bdd_dict = factory_result
  2454	                logger.info(
  2455	                    "gather_evidence: BDD evidence from factory plugin "
  2456	                    "(stack=%s, scenarios_attempted=%s).",
  2457	                    stack_profile,
  2458	                    factory_result.get("scenarios_attempted"),
  2459	                )
  2460	            else:
  2461	                logger.debug(
  2462	                    "gather_evidence: factory BDD discovery returned None; "
  2463	                    "bdd field left as absent signal.",
  2464	                )
  2465	        else:
  2466	            # Factory unavailable — bdd_dict stays None (absent signal).
  2467	            logger.debug(
  2468	                "gather_evidence: guardkitfactory not available; "
  2469	                "Player-reported bdd_results were empty; "
  2470	                "bdd field left as absent signal.",
  2471	            )
  2472	
  2473	        # Quality-gate-failure short-circuit. Legacy validate() also
  2474	        # short-circuits here via _feedback_from_gates.
  2475	        if not gates.all_gates_passed:
  2476	            logger.info(
  2477	                "gather_evidence: quality gates failed for %s; downstream "
  2478	                "(requirements, independent tests) skipped.", task_id,
  2479	            )
  2480	            return CoachEvidenceBundle(
  2481	                honesty=honesty,
  2482	                gathering_status="partial_gate_abort",
  2483	                quality_gates=gates,
  2484	                coverage_details=coverage_details,
  2485	                plan_audit=plan_audit_dict,
  2486	                bdd=bdd_dict,
  2487	                arch_review=arch_review_dict,
  2488	                tests=tests_dict,
  2489	                severity_recommendations=severity_recommendations,
  2490	                advisory_issues=advisory_issues,
  2491	                task_type=task_type.value,
  2492	                profile_name=profile_name,
  2493	            )
  2494	
  2495	        # ------------------------------------------------------------------
  2496	        # 3. Requirements validation. Mirrors validate() line 1139.
  2497	        # Hoisted ahead of independent-test in the legacy path; preserved
  2498	        # here for the same reason — cheaper, idempotent.
  2499	        # ------------------------------------------------------------------
  2500	        try:
  2501	            requirements = self.validate_requirements(
  2502	                task, task_work_results, turn=turn
  2503	            )
  2504	        except Exception as exc:  # noqa: BLE001
  2505	            logger.error(
  2506	                "gather_evidence: validate_requirements raised: %s", exc,
  2507	            )
  2508	            return CoachEvidenceBundle(
  2509	                honesty=honesty,
  2510	                gathering_status="partial_exception",
  2511	                gathering_error=f"requirements_exception: {exc}",
  2512	                quality_gates=gates,
  2513	                coverage_details=coverage_details,
  2514	                plan_audit=plan_audit_dict,
  2515	                bdd=bdd_dict,
  2516	                arch_review=arch_review_dict,
  2517	                tests=tests_dict,
  2518	                severity_recommendations=severity_recommendations,
  2519	                advisory_issues=advisory_issues,
  2520	                task_type=task_type.value,
  2521	                profile_name=profile_name,
  2522	            )
  2523	
  2524	        # ------------------------------------------------------------------
  2525	        # 4. Independent tests. Mirrors validate() lines 1156-1175.
  2526	        # ------------------------------------------------------------------
  2527	        if not profile.tests_required:
  2528	            test_result: IndependentTestResult = IndependentTestResult(
  2529	                tests_passed=True,
  2530	                test_command="skipped",
  2531	                test_output_summary=(
  2532	                    f"Independent test verification skipped "
  2533	                    f"(tests not required for {task_type.value} tasks)"
  2534	                ),
  2535	                duration_seconds=0.0,
  2536	            )
  2537	            logger.info(
  2538	                "gather_evidence: independent test verification skipped for "
  2539	                "%s (tests not required for %s tasks)",
  2540	                task_id, task_type.value,
  2541	            )
  2542	        else:
  2543	            try:
  2544	                test_result = self.run_independent_tests(
  2545	                    task_work_results=task_work_results,
  2546	                    task=task,
  2547	                    turn=turn,
  2548	                )
  2549	            except Exception as exc:  # noqa: BLE001
  2550	                logger.error(
  2551	                    "gather_evidence: run_independent_tests raised: %s", exc,
  2552	                )
  2553	                return CoachEvidenceBundle(
  2554	                    honesty=honesty,
  2555	                    gathering_status="partial_exception",
  2556	                    gathering_error=f"independent_tests_exception: {exc}",
  2557	                    quality_gates=gates,
  2558	                    coverage_details=coverage_details,
  2559	                    plan_audit=plan_audit_dict,
  2560	                    bdd=bdd_dict,
  2561	                    arch_review=arch_review_dict,
  2562	                    tests=tests_dict,
  2563	                    requirements=requirements,
  2564	                    severity_recommendations=severity_recommendations,
  2565	                    advisory_issues=advisory_issues,
  2566	                    task_type=task_type.value,
  2567	                    profile_name=profile_name,
  2568	                )
  2569	
  2570	        # ------------------------------------------------------------------
  2571	        # 5. Wiring analysis (Wave-1, TASK-QAWE-002).
  2572	        # Populates wiring / mocked_seam / spec_gap at the complete-path
  2573	        # return only. Partial returns (honesty_abort, gate_abort,
  2574	        # exception) leave all three None.
  2575	        # ------------------------------------------------------------------
  2576	        wiring_dict: Optional[Dict[str, Any]] = None
  2577	        mocked_seam_dict: Optional[Dict[str, Any]] = None
  2578	        spec_gap_dict: Optional[Dict[str, Any]] = None
  2579	
  2580	        try:
  2581	            stack_template = detect_stack_template(self.worktree_path)
  2582	            authored = _compute_authored_set(task_work_results)
  2583	            wiring_result = _run_wiring_analysis(
  2584	                worktree_path=self.worktree_path,
  2585	                authored_files=authored,
  2586	                task_type=task_type.value,
  2587	                stack_template=stack_template,
  2588	            )
  2589	            if wiring_result is not None:
  2590	                wiring_dict = wiring_result.get("wiring")
  2591	                mocked_seam_dict = wiring_result.get("mocked_seam")
  2592	                spec_gap_dict = wiring_result.get("spec_gap")
  2593	                logger.info(
  2594	                    "gather_evidence: wiring analysis complete "
  2595	                    "(wiring_findings=%d, mocked_seam_findings=%d, "
  2596	                    "spec_gap_findings=%d).",
  2597	                    len(wiring_dict.get("findings", [])) if wiring_dict else 0,
  2598	                    len(mocked_seam_dict.get("findings", [])) if mocked_seam_dict else 0,
  2599	                    len(spec_gap_dict.get("findings", [])) if spec_gap_dict else 0,
  2600	                )
  2601	        except Exception as exc:  # noqa: BLE001 — wiring errors must not break gathering
  2602	            logger.warning(
  2603	                "gather_evidence: wiring analysis raised %s; "
  2604	                "all three fields left as None.",
  2605	                exc.__class__.__name__,
  2606	            )
  2607	
  2608	        return CoachEvidenceBundle(
  2609	            honesty=honesty,
  2610	            gathering_status="complete",
  2611	            quality_gates=gates,
  2612	            coverage_details=coverage_details,
  2613	            plan_audit=plan_audit_dict,
  2614	            bdd=bdd_dict,
  2615	            arch_review=arch_review_dict,
  2616	            tests=tests_dict,
  2617	            independent_tests=test_result,
  2618	            requirements=requirements,
  2619	            severity_recommendations=severity_recommendations,
  2620	            advisory_issues=advisory_issues,
  2621	            task_type=task_type.value,
  2622	            profile_name=profile_name,
  2623	            wiring=wiring_dict,
  2624	            mocked_seam=mocked_seam_dict,
  2625	            spec_gap=spec_gap_dict,
  2626	        )
  2627	
  2628	    def _compute_agent_invocations_advisory(
  2629	        self, task_work_results: Dict[str, Any],
  2630	    ) -> Optional[Dict[str, Any]]:
  2631	        """Compute the non-blocking agent-invocations advisory issue.
  2632	
  2633	        Extracted from ``validate()`` lines 1028-1126 (TASK-FIX-RWOP1.3.1 /
  2634	        TASK-REV-F6E1 F3c) for reuse by ``gather_evidence()`` (TASK-HMIG-008R
  2635	        Part A). Returns ``None`` when no advisory is needed.
  2636	
  2637	        The logic mirrors the inline computation in ``validate()``: a
  2638	        ``"violation"`` status in ``task_work_results['agent_invocations_validation']``
  2639	        produces a ``severity == "warning"`` advisory naming the missing
  2640	        phases and recommending stack-specific specialists. ``"passed"``,
  2641	        ``"validator_error"``, and ``"no_data"`` statuses are not advised
  2642	        on — they ride through without comment.
  2643	        """
  2644	        agent_invocations_validation = task_work_results.get(
  2645	            "agent_invocations_validation"
  2646	        )
  2647	        if not (
  2648	            isinstance(agent_invocations_validation, dict)
  2649	            and agent_invocations_validation.get("status") == "violation"
  2650	        ):
  2651	            return None
  2652	
  2653	        raw_missing = agent_invocations_validation.get("missing_phases") or []
  2654	        missing_phases: List[str] = []
  2655	        if raw_missing and isinstance(raw_missing[0], dict):
  2656	            missing_phases = [
  2657	                str(m.get("phase", ""))
  2658	                for m in raw_missing
  2659	                if m.get("phase")
  2660	            ]
  2661	        else:
  2662	            missing_phases = [str(m) for m in raw_missing]
  2663	        missing_phases_sorted = sorted(missing_phases)
  2664	        missing_phases_with_names = ", ".join(
  2665	            f"{p} ({PHASE_DESCRIPTIONS.get(p, 'Unknown')})"
  2666	            for p in missing_phases_sorted
  2667	        ) if missing_phases_sorted else "unknown"
  2668	
  2669	        stack_template = detect_stack_template(self.worktree_path)
  2670	        specialist_lines = render_missing_phase_list(
  2671	            missing_phases_sorted,
  2672	            stack_template=stack_template,
  2673	            workspace_root=self.worktree_path,
  2674	        )
  2675	        specialist_block = "\n".join(
  2676	            f"- {line}" for line in specialist_lines
  2677	        )
  2678	
  2679	        expected_phases_val = agent_invocations_validation.get("expected_phases")
  2680	        actual_invocations_val = agent_invocations_validation.get("actual_invocations")
  2681	        expected_str = (
  2682	            str(expected_phases_val) if expected_phases_val is not None else "?"
  2683	        )
  2684	        actual_str = (
  2685	            str(actual_invocations_val)
  2686	            if actual_invocations_val is not None
  2687	            else "?"
  2688	        )
  2689	
  2690	        return {
  2691	            "severity": "warning",
  2692	            "category": "agent_invocations_advisory",
  2693	            "description": (
  2694	                f"Advisory (non-blocking): task-work produced a report with "
  2695	                f"{actual_str} of {expected_str} expected agent invocations. "
  2696	                f"Missing phases: {missing_phases_with_names}. "
  2697	                f"Consider invoking these agents via the Task tool to "
  2698	                f"strengthen stack-specific quality:\n{specialist_block}"
  2699	            ),
  2700	            "details": {
  2701	                "missing_phases": missing_phases_sorted,
  2702	                "expected_phases": expected_phases_val,
  2703	                "actual_invocations": actual_invocations_val,
  2704	            },
  2705	        }
  2706	
  2707	    def read_quality_gate_results(self, task_id: str) -> Dict[str, Any]:
  2708	        """
  2709	        Read quality gate results from task-work execution.
  2710	
  2711	        Looks for results in the standard location:
  2712	        `.guardkit/autobuild/{task_id}/task_work_results.json`
  2713	
  2714	        Parameters
  2715	        ----------
  2716	        task_id : str
  2717	            Task identifier
  2718	
  2719	        Returns
  2720	        -------
  2721	        Dict[str, Any]
  2722	            Task-work results, or dict with "error" key if not found
  2723	        """
  2724	        results_path = TaskArtifactPaths.task_work_results_path(task_id, self.worktree_path)
  2725	        logger.debug(f"Looking for task_work_results at: {results_path}")
  2726	
  2727	        if not results_path.exists():
  2728	            logger.warning(f"task_work_results.json not found at {results_path}")
  2729	            logger.debug(f"Worktree path: {self.worktree_path}")
  2730	            logger.debug(f"Task ID: {task_id}")
  2731	            return {"error": f"Task-work results not found at {results_path}"}
  2732	
  2733	        try:
  2734	            with open(results_path) as f:
  2735	                results = json.load(f)
  2736	            logger.debug(f"Successfully loaded task_work_results from {results_path}")
  2737	            return results
  2738	        except json.JSONDecodeError as e:
  2739	            logger.error(f"Failed to parse task-work results: {e}")
  2740	            return {"error": f"Failed to parse task-work results: {e}"}
  2741	        except Exception as e:
  2742	            logger.error(f"Failed to read task-work results: {e}")
  2743	            return {"error": f"Failed to read task-work results: {e}"}
  2744	
  2745	    def verify_quality_gates(
  2746	        self,
  2747	        task_work_results: Dict[str, Any],
  2748	        profile: Optional[QualityGateProfile] = None,
  2749	        skip_arch_review: bool = False,
  2750	    ) -> QualityGateStatus:
AI: [{'name': 'grep', 'args': {'glob': 'guardkit/orchestrator/agent_invoker.py', 'pattern': '_render_evidence_bundle_section'}, 'id': 'qtQB8giVP1sWgSOuCe0ZwLVtOC65F2rh', 'type': 'tool_call'}]
Tool: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/agent_invoker.py
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/agent_invoker.py', 'limit': 500, 'offset': 3000}, 'id': 'cQ6xoebcl2oD8iIVuBKRSVbBwY3rKUwN', 'type': 'tool_call'}]
Tool:   3001	
  3002	```json
  3003	{{
  3004	  "task_id": "{task_id}",
  3005	  "turn": {turn},
  3006	  "decision": "approve" | "feedback",
  3007	  ...fields as specified below...
  3008	}}
  3009	```
  3010	
  3011	For APPROVAL, the JSON block must contain:
  3012	```json
  3013	{{
  3014	  "task_id": "{task_id}",
  3015	  "turn": {turn},
  3016	  "decision": "approve",
  3017	  "validation_results": {{
  3018	    "requirements_met": ["list", "of", "verified", "requirements"],
  3019	    "tests_run": true,
  3020	    "tests_passed": true,
  3021	    "test_command": "command you ran",
  3022	    "test_output_summary": "summary of test results",
  3023	    "code_quality": "assessment",
  3024	    "edge_cases_covered": ["list", "of", "edge", "cases"]
  3025	  }},{verification_example}
  3026	  "rationale": "Why you approved"
  3027	}}
  3028	```
  3029	
  3030	For FEEDBACK, the JSON block must contain:
  3031	```json
  3032	{{
  3033	  "task_id": "{task_id}",
  3034	  "turn": {turn},
  3035	  "decision": "feedback",
  3036	  "issues": [
  3037	    {{
  3038	      "type": "missing_requirement" | "test_failure" | "code_quality" | "edge_case",
  3039	      "severity": "critical" | "major" | "minor",
  3040	      "description": "Specific issue with file paths and line numbers",
  3041	      "requirement": "Which requirement is affected",
  3042	      "suggestion": "How to fix it"
  3043	    }}
  3044	  ],{verification_example}
  3045	  "rationale": "Why you're providing feedback"
  3046	}}
  3047	```
  3048	
  3049	**IMPORTANT**: For each acceptance criterion, create a criteria_verification with:
  3050	- criterion_id: The ID (e.g., "AC-001") matching the Player's completion_promise
  3051	- result: "verified" if criterion is satisfied, "rejected" if not
  3052	- notes: Your reasoning - what you checked and found
  3053	
  3054	**CRITICAL**: The fenced ```json block MUST be the last thing in your response.
  3055	Do not write any prose after the closing ``` fence. If you emit exploratory JSON
  3056	blocks earlier in your response (e.g. while sketching alternatives), the
  3057	orchestrator takes only the **last** fenced block.
  3058	"""
  3059	        return prompt
  3060	
  3061	    # ------------------------------------------------------------------
  3062	    # TASK-HMIG-008R Part C — Coach prompt rendering helpers.
  3063	    # ------------------------------------------------------------------
  3064	
  3065	    # Token-budget truncation thresholds (plan §4 "Token budget"):
  3066	    _COACH_BDD_DISCOVERIES_LIMIT = 20
  3067	    _COACH_BDD_ERRORS_LIMIT = 10
  3068	    _COACH_HONESTY_DISCREPANCIES_LIMIT = 20
  3069	    # Wave-1 (TASK-QAWE-002): wiring / mocked_seam / spec_gap findings limit.
  3070	    _COACH_WIRING_FINDINGS_LIMIT = 20
  3071	
  3072	    # TASK-PERF-COACHSYNTH (AC-4 / Lever C): cap the Phase-A gather findings
  3073	    # text rendered into the Phase-B synthesis prompt. The gather is already
  3074	    # bounded at the source (recursion_limit + per-tool-result truncation),
  3075	    # but the findings the model *produces* can still be large; this is the
  3076	    # final belt so the synthesis prompt size does not grow unbounded with
  3077	    # gather volume (the run-20 latency creep). Truncation is MARKED, never
  3078	    # silent — respecting absence-of-failure-is-not-success.md: a silently
  3079	    # dropped tail would let the synthesis treat a partial checklist as
  3080	    # complete. ~16 k chars ≈ ~4 k tokens of findings.
  3081	    _COACH_GATHER_FINDINGS_LIMIT_CHARS = int(
  3082	        os.environ.get("GUARDKIT_COACH_GATHER_FINDINGS_LIMIT_CHARS", "16000")
  3083	    )
  3084	
  3085	    @classmethod
  3086	    def _truncate_gather_findings(cls, findings: str) -> str:
  3087	        """Cap findings at the char budget with a visible truncation marker."""
  3088	        limit = cls._COACH_GATHER_FINDINGS_LIMIT_CHARS
  3089	        if limit <= 0 or len(findings) <= limit:
  3090	            return findings
  3091	        elided = len(findings) - limit
  3092	        return (
  3093	            findings[:limit]
  3094	            + f"\n\n... [Phase-A findings truncated for synthesis-prompt "
  3095	            f"budget: {elided} more chars elided. Any acceptance criterion "
  3096	            f"NOT explicitly marked PASS above is unverified — treat as "
  3097	            f"FAIL/UNSURE, never an assumed pass.] ..."
  3098	        )
  3099	
  3100	    @classmethod
  3101	    def _truncate_findings(
  3102	        cls,
  3103	        findings_container: Optional[Dict[str, Any]],
  3104	        limit: int,
  3105	    ) -> None:
  3106	        """Truncate the ``findings`` list inside a wiring result dict.
  3107	
  3108	        Keeps the first ``limit`` entries and appends a ``"... and N more"``
  3109	        marker when the list exceeds the limit. Mirrors the
  3110	        ``bdd.discoveries`` truncation pattern. Wave-1, TASK-QAWE-002.
  3111	
  3112	        Parameters
  3113	        ----------
  3114	        findings_container : Optional[Dict[str, Any]]
  3115	            A dict with a ``"findings"`` key (e.g. wiring / mocked_seam /
  3116	            spec_gap result). May be ``None``.
  3117	        limit : int
  3118	            Maximum number of findings to keep.
  3119	        """
  3120	        if not isinstance(findings_container, dict):
  3121	            return
  3122	        findings = findings_container.get("findings")
  3123	        if isinstance(findings, list) and len(findings) > limit:
  3124	            remainder = len(findings) - limit
  3125	            findings_container["findings"] = (
  3126	                findings[:limit]
  3127	                + [f"... and {remainder} more (truncated for token budget)"]
  3128	            )
  3129	
  3130	    def _render_evidence_bundle_section(
  3131	        self,
  3132	        evidence_bundle: "CoachEvidenceBundle",
  3133	    ) -> str:
  3134	        """Render the CoachEvidenceBundle as a structured prompt section.
  3135	
  3136	        Emits the bundle as JSON inside ``<evidence_bundle>...</evidence_bundle>``
  3137	        XML-like tags so the LLM Coach can locate it deterministically and
  3138	        apply the absence-of-failure guards against specific fields.
  3139	
  3140	        Truncation rules (plan §4):
  3141	
  3142	        * ``evidence_bundle.bdd.discoveries`` — keep first 20 entries.
  3143	        * ``evidence_bundle.bdd.errors``     — keep first 10 entries.
  3144	        * ``evidence_bundle.honesty.discrepancies`` — keep first 20 entries.
  3145	        * ``evidence_bundle.wiring.findings`` — keep first 20 entries.
  3146	        * ``evidence_bundle.mocked_seam.findings`` — keep first 20 entries.
  3147	        * ``evidence_bundle.spec_gap.findings`` — keep first 20 entries.
  3148	
  3149	        Each truncation appends a ``"... and N more"`` marker so the Coach
  3150	        knows the list was bounded. Non-list fields are bounded by gate
  3151	        computation and pass through unchanged.
  3152	
  3153	        The bundle's honesty channel is NOT duplicated here — it lives in
  3154	        the separate ``<honesty_verification>`` section emitted by
  3155	        :py:meth:`_render_bundle_honesty_section`. Both sections read from
  3156	        the same bundle.honesty value, but rendering them separately lets
  3157	        the absence-of-failure guards reference each by tag.
  3158	        """
  3159	        try:
  3160	            bundle_dict = evidence_bundle.to_dict()
  3161	        except Exception as exc:  # noqa: BLE001 — never block prompt build
  3162	            logger.error(
  3163	                "Failed to serialise evidence_bundle for Coach prompt: %s. "
  3164	                "Emitting empty bundle section so the Coach prompt still "
  3165	                "carries the absence-of-failure guards.",
  3166	                exc,
  3167	            )
  3168	            bundle_dict = {
  3169	                "gathering_status": "partial_exception",
  3170	                "gathering_error": f"bundle_serialisation_failed: {exc}",
  3171	            }
  3172	
  3173	        # Truncate bdd.discoveries / bdd.errors.
  3174	        bdd = bundle_dict.get("bdd")
  3175	        if isinstance(bdd, dict):
  3176	            discoveries = bdd.get("discoveries")
  3177	            if isinstance(discoveries, list) and len(discoveries) > self._COACH_BDD_DISCOVERIES_LIMIT:
  3178	                remainder = len(discoveries) - self._COACH_BDD_DISCOVERIES_LIMIT
  3179	                bdd["discoveries"] = discoveries[: self._COACH_BDD_DISCOVERIES_LIMIT] + [
  3180	                    f"... and {remainder} more (truncated for token budget)"
  3181	                ]
  3182	            errors = bdd.get("errors")
  3183	            if isinstance(errors, list) and len(errors) > self._COACH_BDD_ERRORS_LIMIT:
  3184	                remainder = len(errors) - self._COACH_BDD_ERRORS_LIMIT
  3185	                bdd["errors"] = errors[: self._COACH_BDD_ERRORS_LIMIT] + [
  3186	                    f"... and {remainder} more (truncated for token budget)"
  3187	                ]
  3188	
  3189	        # honesty.discrepancies truncation lives inside _render_bundle_honesty_section,
  3190	        # but we ALSO truncate the copy nested in bundle_dict["honesty"] so the
  3191	        # evidence-bundle JSON the Coach sees is internally consistent.
  3192	        honesty = bundle_dict.get("honesty")
  3193	        if isinstance(honesty, dict):
  3194	            discrepancies = honesty.get("discrepancies")
  3195	            if (
  3196	                isinstance(discrepancies, list)
  3197	                and len(discrepancies) > self._COACH_HONESTY_DISCREPANCIES_LIMIT
  3198	            ):
  3199	                remainder = len(discrepancies) - self._COACH_HONESTY_DISCREPANCIES_LIMIT
  3200	                honesty["discrepancies"] = discrepancies[
  3201	                    : self._COACH_HONESTY_DISCREPANCIES_LIMIT
  3202	                ] + [{
  3203	                    "truncated": True,
  3204	                    "remainder": remainder,
  3205	                    "note": (
  3206	                        f"... and {remainder} more discrepancies (truncated "
  3207	                        f"for token budget). See full honesty_verification "
  3208	                        f"in coach_turn_N.json."
  3209	                    ),
  3210	                }]
  3211	
  3212	        # Truncate wiring / mocked_seam / spec_gap findings.
  3213	        # Mirrors the bdd.discoveries truncation pattern (keep first 20 +
  3214	        # "... and N more" marker). Wave-1, TASK-QAWE-002.
  3215	        self._truncate_findings(bundle_dict.get("wiring"), self._COACH_WIRING_FINDINGS_LIMIT)
  3216	        self._truncate_findings(bundle_dict.get("mocked_seam"), self._COACH_WIRING_FINDINGS_LIMIT)
  3217	        self._truncate_findings(bundle_dict.get("spec_gap"), self._COACH_WIRING_FINDINGS_LIMIT)
  3218	
  3219	        try:
  3220	            payload = json.dumps(bundle_dict, indent=2, default=str)
  3221	        except Exception as exc:  # noqa: BLE001
  3222	            logger.error(
  3223	                "Failed to JSON-encode truncated evidence_bundle: %s", exc,
  3224	            )
  3225	            payload = '{"gathering_status": "partial_exception", "gathering_error": "json_encode_failed"}'
  3226	
  3227	        return f"""
  3228	## Deterministic Evidence Bundle
  3229	
  3230	<evidence_bundle>
  3231	{payload}
  3232	</evidence_bundle>
  3233	"""
  3234	
  3235	    def _render_bundle_honesty_section(
  3236	        self,
  3237	        honesty_verification: HonestyVerification,
  3238	    ) -> str:
  3239	        """Render the bundle's HonestyVerification as a structured prompt section.
  3240	
  3241	        Sourced from ``evidence_bundle.honesty`` (channel unification per
  3242	        plan §4). Emits a JSON-structured section inside
  3243	        ``<honesty_verification>...</honesty_verification>`` tags so the
  3244	        absence-of-failure guards can reference specific fields:
  3245	
  3246	        * ``honesty.discrepancies[*].claim_type``
  3247	        * ``honesty.discrepancies[*].severity``
  3248	        * ``honesty.resolved_paths`` — Layer-1 (TASK-FIX-1B4A) suppressions.
  3249	
  3250	        Truncation rule: keep first 20 discrepancies (plan §4 token budget).
  3251	        """
  3252	        from dataclasses import asdict
  3253	
  3254	        try:
  3255	            honesty_dict: Dict[str, Any] = asdict(honesty_verification)
  3256	        except Exception as exc:  # noqa: BLE001
  3257	            logger.error(
  3258	                "Failed to serialise honesty_verification for Coach prompt: %s",
  3259	                exc,
  3260	            )
  3261	            honesty_dict = {
  3262	                "verified": True,
  3263	                "discrepancies": [],
  3264	                "honesty_score": 1.0,
  3265	                "resolved_paths": [],
  3266	                "should_fix_count": 0,
  3267	                "serialisation_error": str(exc),
  3268	            }
  3269	
  3270	        discrepancies = honesty_dict.get("discrepancies")
  3271	        if (
  3272	            isinstance(discrepancies, list)
  3273	            and len(discrepancies) > self._COACH_HONESTY_DISCREPANCIES_LIMIT
  3274	        ):
  3275	            remainder = len(discrepancies) - self._COACH_HONESTY_DISCREPANCIES_LIMIT
  3276	            honesty_dict["discrepancies"] = discrepancies[
  3277	                : self._COACH_HONESTY_DISCREPANCIES_LIMIT
  3278	            ] + [{
  3279	                "truncated": True,
  3280	                "remainder": remainder,
  3281	                "note": (
  3282	                    f"... and {remainder} more discrepancies (truncated "
  3283	                    f"for token budget). See full list in coach_turn_N.json."
  3284	                ),
  3285	            }]
  3286	
  3287	        try:
  3288	            payload = json.dumps(honesty_dict, indent=2, default=str)
  3289	        except Exception as exc:  # noqa: BLE001
  3290	            logger.error(
  3291	                "Failed to JSON-encode honesty_verification: %s", exc,
  3292	            )
  3293	            payload = '{"verified": true, "discrepancies": [], "honesty_score": 1.0}'
  3294	
  3295	        return f"""
  3296	## Honesty Verification
  3297	
  3298	<honesty_verification>
  3299	{payload}
  3300	</honesty_verification>
  3301	"""
  3302	
  3303	    def _render_absence_of_failure_guards(self) -> str:
  3304	        """Render the six absence-of-failure guard sentences (AC-009 + #5 + #6).
  3305	
  3306	        The four guards from the TASK-HMIG-008R task spec (AC-009 points 1-4),
  3307	        the fifth guard added per Phase 2.5 review finding #2
  3308	        (gathering_status guard), and the sixth guard added by
  3309	        TASK-FIX-COACHTESTTO (independent-test absent guard — treat a
  3310	        timed-out / transport-errored independent-test oracle as ABSENT rather
  3311	        than approving on the Player's self-reported tests). The sentences are
  3312	        emitted verbatim inside
  3313	        an ``<absence_of_failure_guards>`` block so the Coach can locate
  3314	        them deterministically. Wording mirrors
  3315	        ``.claude/rules/absence-of-failure-is-not-success.md`` and
  3316	        ``.claude/rules/path-string-mismatch-is-not-dishonesty.md`` to
  3317	        preserve the rule citation chain.
  3318	        """
  3319	        return """
  3320	<absence_of_failure_guards>
  3321	CRITICAL READING RULES — apply these BEFORE any approval decision:
  3322	
  3323	1. ZERO-CARDINALITY BDD GUARD.
  3324	   If evidence_bundle.bdd is not null AND evidence_bundle.bdd.scenarios_attempted == 0:
  3325	   treat as ABSENT SIGNAL — do NOT approve based on absence of failure.
  3326	   Surface as feedback: "BDD oracle ran zero scenarios — no evidence of
  3327	   passing behaviour." Rule: .claude/rules/absence-of-failure-is-not-success.md.
  3328	
  3329	2. ZERO-CARDINALITY TEST GUARD.
  3330	   If evidence_bundle.tests is not null AND evidence_bundle.tests.tests_run == 0:
  3331	   treat as ABSENT SIGNAL — do NOT approve. Surface as feedback:
  3332	   "No tests ran — cannot verify correctness." Rule:
  3333	   .claude/rules/absence-of-failure-is-not-success.md.
  3334	
  3335	3. SOPHISTICATED-LIE GUARD.
  3336	   If honesty_verification.discrepancies contains entries with
  3337	   severity == "critical" AND claim_type != "file_existence" AND
  3338	   claim_type != "claim_audit": you MUST reject the turn. These are
  3339	   sophisticated lies (test_result, test_count, promise_file_existence
  3340	   fabrications). Structural rejection is mandatory — do not evaluate
  3341	   ACs further. Surface a "feedback" decision naming each discrepancy.
  3342	
  3343	4. LAYER-1 PATH DEMOTION GUARD.
  3344	   If honesty_verification.discrepancies contains exactly ONE entry with
  3345	   claim_type == "file_existence" AND honesty_verification.resolved_paths
  3346	   is non-empty: this discrepancy was Layer-1-resolved by state_bridge
  3347	   identity lookup (the orchestrator moved the task file, not Player
  3348	   dishonesty). Demote to should_fix and continue AC evaluation. Rule:
  3349	   .claude/rules/path-string-mismatch-is-not-dishonesty.md (Layer 2).
  3350	   Cross-check evidence_bundle.severity_recommendations for the
  3351	   structured hint — if present, it confirms this demotion applies.
  3352	
  3353	5. GATHERING-STATUS GUARD.
  3354	   If evidence_bundle.gathering_status != "complete": evidence collection
  3355	   aborted before all fields were populated. Treat any null/None field as
  3356	   ABSENT SIGNAL — do NOT approve. Surface as feedback with the
  3357	   gathering_status value verbatim in the rationale so operators can
  3358	   diagnose which stage failed (e.g. "partial_honesty_abort",
  3359	   "partial_gate_abort", "partial_exception"). When status is
  3360	   "partial_exception", also surface evidence_bundle.gathering_error.
  3361	
  3362	6. INDEPENDENT-TEST ABSENT GUARD.
  3363	   If evidence_bundle.independent_tests is not null AND
  3364	   evidence_bundle.independent_tests.signal_absent == true: the Coach's own
  3365	   trust-but-verify pytest run did NOT complete (it timed out or failed at
  3366	   the transport layer before producing a verdict). This is ABSENT SIGNAL,
  3367	   NOT a passing or failing test result — do NOT approve on the basis of the
  3368	   Player's self-reported tests plus the other gates. Surface as feedback:
  3369	   "Independent test verification did not complete (signal absent) — cannot
  3370	   independently confirm the Player's reported tests." Quote
  3371	   independent_tests.test_output_summary verbatim in the rationale so
  3372	   operators can see whether it timed out or errored. Rule:
  3373	   .claude/rules/absence-of-failure-is-not-success.md.
  3374	
  3375	7. WIRING-EVIDENCE ADVISORY GUARD.
  3376	   If evidence_bundle.wiring, evidence_bundle.mocked_seam, or
  3377	   evidence_bundle.spec_gap is not null AND any of these fields has a
  3378	   non-empty findings list for a FEATURE / REFACTOR / INTEGRATION task:
  3379	   treat the named symbols as candidate dead code (UNWIRED_PATH), suspect
  3380	   acceptance evidence (MOCKED_SEAM), or unexecuted scenarios (SPEC_GAP).
  3381	   Require evidence of registration / real-seam execution before approving.
  3382	   Surface as feedback unless the Player demonstrates the wiring path.
  3383	   Advisory only — does not override on its own; combines with other
  3384	   guards for the final decision. Rule:
  3385	   .claude/rules/absence-of-failure-is-not-success.md.
  3386	</absence_of_failure_guards>
  3387	"""
  3388	
  3389	    def _verify_player_claims(
  3390	        self,
  3391	        player_report: Dict[str, Any],
  3392	    ) -> HonestyVerification:
  3393	        """Verify Player's self-reported claims against reality.
  3394	
  3395	        This method uses CoachVerifier to cross-reference Player claims:
  3396	        - Test results vs actual test execution
  3397	        - Claimed files vs filesystem state
  3398	        - Test counts vs parsed output
  3399	
  3400	        Args:
  3401	            player_report: Player's report from current turn
  3402	
  3403	        Returns:
  3404	            HonestyVerification with verification results and honesty score
  3405	
  3406	        Note:
  3407	            Returns a default verification result if verification fails,
  3408	            allowing the workflow to continue while logging the issue.
  3409	        """
  3410	        try:
  3411	            verifier = CoachVerifier(
  3412	                self.worktree_path, venv_python=self._venv_python
  3413	            )
  3414	            verification = verifier.verify_player_report(player_report)
  3415	
  3416	            if verification.discrepancies:
  3417	                logger.warning(
  3418	                    f"Player honesty verification found {len(verification.discrepancies)} "
  3419	                    f"discrepancies (score: {verification.honesty_score:.2f})"
  3420	                )
  3421	                for disc in verification.discrepancies:
  3422	                    logger.warning(
  3423	                        f"  [{disc.severity}] {disc.claim_type}: "
  3424	                        f"claimed {disc.player_claim}, actual {disc.actual_value}"
  3425	                    )
  3426	            else:
  3427	                logger.info(
  3428	                    f"Player claims verified successfully (score: {verification.honesty_score:.2f})"
  3429	                )
  3430	
  3431	            return verification
  3432	
  3433	        except Exception as e:
  3434	            logger.warning(f"Failed to verify Player claims: {e}")
  3435	            # Return default verification (assume honest) to not block workflow
  3436	            return HonestyVerification(verified=True, discrepancies=[], honesty_score=1.0)
  3437	
  3438	    async def _invoke_with_role(
  3439	        self,
  3440	        prompt: str,
  3441	        agent_type: Literal["player", "coach"],
  3442	        allowed_tools: list[str],
  3443	        permission_mode: Literal["acceptEdits", "bypassPermissions"],
  3444	        model: Optional[str] = None,
  3445	        resume_session_id: Optional[str] = None,
  3446	        task_id: Optional[str] = None,
  3447	        turn: Optional[int] = None,
  3448	        heartbeat_label_override: Optional[str] = None,
  3449	        return_events: bool = False,
  3450	        synthesis: bool = False,
  3451	        grammar: Optional[str] = None,
  3452	        recursion_limit: Optional[int] = None,
  3453	        max_tool_result_chars: Optional[int] = None,
  3454	    ) -> Optional[Tuple[None, List[HarnessEvent]]]:
  3455	        """Low-level SDK invocation with role-based permissions.
  3456	
  3457	        This method handles the actual Claude Agent SDK invocation with
  3458	        appropriate permissions and timeout handling. Emits an ``llm.call``
  3459	        event for every invocation via the injected EventEmitter
  3460	        (TASK-INST-005b).
  3461	
  3462	        Args:
  3463	            prompt: Formatted prompt for agent
  3464	            agent_type: "player" or "coach"
  3465	            allowed_tools: List of allowed SDK tools
  3466	            permission_mode: "acceptEdits" (Player) or "bypassPermissions" (Coach)
  3467	            model: Model identifier, or None to use CLI default
  3468	            resume_session_id: Optional SDK session ID to resume from.
  3469	                If provided, passed as ``resume`` kwarg to ClaudeAgentOptions.
  3470	                If None, starts a fresh session. (TASK-RFX-B20B)
  3471	            heartbeat_label_override: Optional explicit phase label for
  3472	                ``async_heartbeat``. When provided, replaces the default
  3473	                ``f"{agent_type.capitalize()} invocation"`` label. Used by
  3474	                :func:`run_specialist` so orchestrator-invoked specialists
  3475	                surface as ``"specialist:{name} invocation"`` instead of
  3476	                masquerading as Player/Coach invocations (TASK-ABSR-DIAG).
  3477	            return_events: When ``True``, return ``(None, harness_events)``
  3478	                instead of ``None`` so callers can inspect the typed event
  3479	                stream the harness emitted. Used by the Coach call site
  3480	                (``invoke_coach``) to feed ``coach_output_parser`` the
  3481	                substrate-agnostic ``AssistantMessageEvent`` list it needs
  3482	                to extract the structured verdict (TASK-FIX-COACHOUT01
  3483	                Shape A). Player and specialist call sites leave this
  3484	                ``False`` and continue to receive ``None``.
  3485	
  3486	                The parameter-based mechanism (rather than an instance
  3487	                attribute like ``self._last_harness_events``) was chosen by
  3488	                the Phase 2.5B architectural review (Gap 1) to avoid the
  3489	                hidden stale-state risk a future concurrent-invocation
  3490	                refactor would silently activate.
  3491	            synthesis: When ``True``, dispatch through
  3492	                ``harness.invoke_synthesis(...)`` instead of
  3493	                ``harness.invoke(...)`` — a TOOLLESS call (no ``tools`` in
  3494	                the substrate request) optionally constrained by ``grammar``.
  3495	                Used by the Coach verdict-synthesis path
  3496	                (TASK-ARCH-COACHSPLIT D-3). The caller MUST also pass
  3497	                ``allowed_tools=[]`` so the harness is constructed toolless
  3498	                on every substrate (the SDK harness reads its tool surface
  3499	                from the constructor ``allowed_tools``, not from the invoke
  3500	                call). All other orchestrator-side concerns (cancel monitor,
AI: [{'name': 'grep', 'args': {'glob': 'guardkit/orchestrator/agent_invoker.py', 'pattern': '_render_evidence_bundle_section'}, 'id': 'Mw7NHKLxw56mMVzFK4lqbJErfPDlPD9U', 'type': 'tool_call'}]
Tool: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/agent_invoker.py

