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
  Seeding episode 1/8...WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 3, 6, 8, 31] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [7, 9, 16, 26] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [6] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [6, 4] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [15, 32] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 240576.46203041077 ms
 done (241.2s)
  Seeding episode 2/8...WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [3] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0-0 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 96098.11091423035 ms
 done (96.5s)
  Seeding episode 3/8...INFO:openai._base_client:Retrying request to /embeddings in 0.450862 seconds
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [8] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [13] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [5] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [4, 5] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [5] (valid range: 0-1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [7] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [3, 4] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [15, 17] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [3] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 1, 3, 6, 7] (valid range: 0--1 for EXISTING FACTS)
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 300s: project_architecture_vllm-profiling
 done (300.4s)
  Seeding episode 4/8.../Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/base_events.py:2031: RuntimeWarning: coroutine 'extract_attributes_from_node' was never awaited
  handle = self._ready.popleft()
RuntimeWarning: Enable tracemalloc to get the object allocation traceback
INFO:graphiti_core.graphiti:Completed add_episode in 28153.76615524292 ms
 done (28.2s)
INFO:guardkit.knowledge.seed_role_constraints:Seeded role constraint: role_constraint_player_feature-build
  Seeding episode 5/8...WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1, 5, 2, 6, 8, 9, 4] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 26571.664094924927 ms
 done (26.6s)
INFO:guardkit.knowledge.seed_role_constraints:Seeded role constraint: role_constraint_coach_feature-build
  Seeding episode 6/8...INFO:graphiti_core.graphiti:Completed add_episode in 74953.56607437134 ms
 done (75.1s)
  Seeding episode 7/8...WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [9] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [7] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1, 3] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 83433.26807022095 ms
 done (83.6s)
  Seeding episode 8/8...WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 30565.561056137085 ms
 done (30.8s)
  Project knowledge seeded successfully (882.2s total)
    OK project_overview: Seeded from CLAUDE.md
    OK role_constraints: Seeded Player and Coach constraints
    OK implementation_modes: Seeded 3 modes

Step 2.5: Syncing template content to Graphiti...
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 120s: template_fastapi-python
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced template 'fastapi-python'
INFO:graphiti_core.graphiti:Completed add_episode in 72033.83088111877 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced agent 'fastapi-specialist'
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 150s: agent_fastapi-python_fastapi-database-specialist
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to sync agent 'fastapi-database-specialist' (episode creation returned None)
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 150s: agent_fastapi-python_fastapi-testing-specialist
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to sync agent 'fastapi-testing-specialist' (episode creation returned None)
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 180s: rule_fastapi-python_migrations_chunk1
WARNING:guardkit.knowledge.graphiti_client:Graphiti disabled after 3 consecutive failures -- continuing without knowledge graph context
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to sync rule 'migrations' chunk 1 (episode creation returned None)
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to sync rule 'crud' chunk 1 (episode creation returned None)
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to sync rule 'models' chunk 1 (episode creation returned None)
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to sync rule 'pydantic-constraints' chunk 1 (episode creation returned None)
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to sync rule 'testing' chunk 1 (episode creation returned None)
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to sync rule 'fastapi' chunk 1 (episode creation returned None)
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to sync rule 'database' chunk 1 (episode creation returned None)
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to sync rule 'routing' chunk 1 (episode creation returned None)
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to sync rule 'schemas' chunk 1 (episode creation returned None)
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 180s: rule_fastapi-python_code-style_chunk1
WARNING:guardkit.knowledge.graphiti_client:Graphiti disabled after 4 consecutive failures -- continuing without knowledge graph context
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to sync rule 'code-style' chunk 1 (episode creation returned None)
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to sync rule 'dependencies' chunk 1 (episode creation returned None)
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 180s: rule_fastapi-python_testing_chunk1
WARNING:guardkit.knowledge.graphiti_client:Graphiti disabled after 5 consecutive failures -- continuing without knowledge graph context
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to sync rule 'testing' chunk 1 (episode creation returned None)
INFO:guardkit.knowledge.template_sync:[Graphiti] Template sync complete: 1 template, 1 agents, 0 rules synced (451.6s)
  Template content synced to Graphiti

GuardKit initialized successfully!

Next steps:
  1. Create a task: /task-create "Your first task"
  2. Work on it: /task-work TASK-XXX
  3. Complete it: /task-complete TASK-XXX
richardwoollcott@Richards-MBP vllm-profiling %