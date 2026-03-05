richardwoollcott@Richards-MBP vllm-profiling % guardkit init fastapi-python -n vllm-profiling --copy-graphiti-from ~/Projects/appmilla_github/guardkit
Initializing GuardKit in /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling
  Project: vllm-profiling
  Template: fastapi-python

Step 1: Applying template...
INFO:guardkit.cli.init:Skipping agent fastapi-database-specialist.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/agents/fastapi-database-specialist.md
INFO:guardkit.cli.init:Skipping agent fastapi-specialist.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/agents/fastapi-specialist.md
INFO:guardkit.cli.init:Skipping agent fastapi-testing-specialist.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/agents/fastapi-testing-specialist.md
INFO:guardkit.cli.init:Skipping rule api/dependencies.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/rules/api/dependencies.md
INFO:guardkit.cli.init:Skipping rule api/routing.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/rules/api/routing.md
INFO:guardkit.cli.init:Skipping rule api/schemas.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/rules/api/schemas.md
INFO:guardkit.cli.init:Skipping rule code-style.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/rules/code-style.md
INFO:guardkit.cli.init:Skipping rule database/crud.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/rules/database/crud.md
INFO:guardkit.cli.init:Skipping rule database/migrations.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/rules/database/migrations.md
INFO:guardkit.cli.init:Skipping rule database/models.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/rules/database/models.md
INFO:guardkit.cli.init:Skipping rule guidance/database.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/rules/guidance/database.md
INFO:guardkit.cli.init:Skipping rule guidance/fastapi.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/rules/guidance/fastapi.md
INFO:guardkit.cli.init:Skipping rule guidance/testing.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/rules/guidance/testing.md
INFO:guardkit.cli.init:Skipping rule patterns/pydantic-constraints.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/rules/patterns/pydantic-constraints.md
INFO:guardkit.cli.init:Skipping rule testing.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/rules/testing.md
INFO:guardkit.cli.init:Skipping root CLAUDE.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/CLAUDE.md
INFO:guardkit.cli.init:Skipping .claude/CLAUDE.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/CLAUDE.md
INFO:guardkit.cli.init:Skipping manifest.json: already exists at /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/manifest.json
INFO:guardkit.cli.init:Applied template 'fastapi-python' to /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling
  Applied template: fastapi-python
INFO:guardkit.cli.init:Copied graphiti config with project_id 'vllm-profiling' to /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.guardkit/graphiti.yaml
  Copied Graphiti config from /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/graphiti.yaml to .guardkit/graphiti.yaml

Step 2: Seeding project knowledge to Graphiti...
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
  Seeding episode 1/8...WARNING:graphiti_core.utils.maintenance.edge_operations:Source index 15 out of bounds for chunk of size 15 in edge CONTAINS_FILE
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 16 out of bounds for chunk of size 15 in edge CONTAINS_FILE
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [4] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0-1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [6] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0-0 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 189609.75217819214 ms
 done (189.6s)
  Seeding episode 2/8...INFO:graphiti_core.graphiti:Completed add_episode in 76918.83492469788 ms
 done (76.9s)
  Seeding episode 3/8...WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 7] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1, 6] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [3] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [4] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0-1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [3, 5] (valid range: 0--1 for EXISTING FACTS)
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 240s: project_architecture_vllm-profiling
 done (240.0s)
  Seeding episode 4/8.../Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/base_events.py:2031: RuntimeWarning: coroutine 'extract_attributes_from_node' was never awaited
  handle = self._ready.popleft()
RuntimeWarning: Enable tracemalloc to get the object allocation traceback
INFO:graphiti_core.graphiti:Completed add_episode in 26777.44698524475 ms
 done (26.8s)
INFO:guardkit.knowledge.seed_role_constraints:Seeded role constraint: role_constraint_player_feature-build
  Seeding episode 5/8...WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 120s: role_constraint_coach_feature-build
 done (120.0s)
INFO:guardkit.knowledge.seed_role_constraints:Seeded role constraint: role_constraint_coach_feature-build
  Seeding episode 6/8...INFO:graphiti_core.graphiti:Completed add_episode in 65811.04302406311 ms
 done (65.8s)
  Seeding episode 7/8...WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0-1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 62536.60988807678 ms
 done (62.5s)
  Seeding episode 8/8...INFO:graphiti_core.graphiti:Completed add_episode in 59174.61895942688 ms
 done (59.2s)
  Project knowledge seeded successfully (840.9s total)
    OK project_overview: Seeded from CLAUDE.md
    OK role_constraints: Seeded Player and Coach constraints
    OK implementation_modes: Seeded 3 modes

Step 2.5: Syncing template content to Graphiti...
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 98258.23998451233 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced template 'fastapi-python'
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0-0 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 69392.009973526 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced agent 'fastapi-database-specialist'
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0-0 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 61385.58101654053 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced agent 'fastapi-specialist'
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0-0 for EXISTING FACTS)
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 120s: agent_fastapi-python_fastapi-testing-specialist
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to sync agent 'fastapi-testing-specialist' (episode creation returned None)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 4] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [3] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2, 7, 8] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 2, 4] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 132099.85899925232 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'code-style'
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [3] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [3] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [4] (valid range: 0-0 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 73134.26804542542 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'testing'
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 2] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 106235.59379577637 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'migrations'
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [3] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 180s: rule_fastapi-python_crud
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to sync rule 'crud' (episode creation returned None)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 58664.23010826111 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'models'
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 115773.84972572327 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'pydantic-constraints'
INFO:graphiti_core.graphiti:Completed add_episode in 43300.02999305725 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'testing'
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [3] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 29998.56424331665 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'fastapi'
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [3] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1, 3, 5, 7, 9] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 41789.44993019104 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'database'
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [5] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 134550.22978782654 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'routing'
INFO:openai._base_client:Retrying request to /chat/completions in 0.396672 seconds
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 15 out of bounds for chunk of size 15 in edge HAS_VERSION
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 180s: rule_fastapi-python_schemas
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to sync rule 'schemas' (episode creation returned None)
INFO:graphiti_core.graphiti:Completed add_episode in 78607.31983184814 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'dependencies'
INFO:guardkit.knowledge.template_sync:[Graphiti] Template sync complete: 1 template, 2 agents, 10 rules synced (1523.3s)
  Template content synced to Graphiti

GuardKit initialized successfully!

Next steps:
  1. Create a task: /task-create "Your first task"
  2. Work on it: /task-work TASK-XXX
  3. Complete it: /task-complete TASK-XXX
richardwoollcott@Richards-MBP vllm-profiling %