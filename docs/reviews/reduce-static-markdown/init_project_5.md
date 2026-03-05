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
  Seeding episode 1/8...INFO:graphiti_core.graphiti:Completed add_episode in 171729.14099693298 ms
 done (171.7s)
  Seeding episode 2/8...WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [3] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 60169.89803314209 ms
 done (60.2s)
  Seeding episode 3/8...WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 2] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [3] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 176674.71313476562 ms
 done (176.7s)
  Seeding episode 4/8...INFO:graphiti_core.graphiti:Completed add_episode in 12155.07197380066 ms
 done (12.2s)
INFO:guardkit.knowledge.seed_role_constraints:Seeded role constraint: role_constraint_player_feature-build
  Seeding episode 5/8...WARNING:graphiti_core.utils.maintenance.node_operations:Invalid duplicate_idx 13 for extracted node a182507c-dc87-4f47-acd3-1ea773c3568c; treating as no duplicate.
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 116192.07692146301 ms
 done (116.2s)
INFO:guardkit.knowledge.seed_role_constraints:Seeded role constraint: role_constraint_coach_feature-build
  Seeding episode 6/8...WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [8] (valid range: 0-1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 60408.642053604126 ms
 done (60.4s)
  Seeding episode 7/8...WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 69763.32998275757 ms
 done (69.8s)
  Seeding episode 8/8...INFO:graphiti_core.graphiti:Completed add_episode in 47903.71584892273 ms
 done (47.9s)
  Project knowledge seeded successfully (715.0s total)
    OK project_overview: Seeded from CLAUDE.md
    OK role_constraints: Seeded Player and Coach constraints
    OK implementation_modes: Seeded 3 modes

Step 2.5: Syncing template content to Graphiti...
INFO:graphiti_core.graphiti:Completed add_episode in 103589.27893638611 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced template 'fastapi-python'
INFO:graphiti_core.graphiti:Completed add_episode in 49946.75087928772 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced agent 'fastapi-database-specialist'
INFO:graphiti_core.graphiti:Completed add_episode in 48390.748262405396 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced agent 'fastapi-specialist'
INFO:graphiti_core.graphiti:Completed add_episode in 64003.036975860596 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced agent 'fastapi-testing-specialist'
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 120s: rule_fastapi-python_code-style
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to sync rule 'code-style' (episode creation returned None)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 88865.91100692749 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'testing'
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1, 3] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 120s: rule_fastapi-python_migrations
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to sync rule 'migrations' (episode creation returned None)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 120s: rule_fastapi-python_crud
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to sync rule 'crud' (episode creation returned None)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [3] (valid range: 0-1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 66741.64199829102 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'models'
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 120s: rule_fastapi-python_pydantic-constraints
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to sync rule 'pydantic-constraints' (episode creation returned None)
/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/base_events.py:2031: RuntimeWarning: coroutine 'extract_attributes_from_node' was never awaited
  handle = self._ready.popleft()
RuntimeWarning: Enable tracemalloc to get the object allocation traceback
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [3, 4] (valid range: 0--1 for EXISTING FACTS)
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 120s: rule_fastapi-python_testing
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to sync rule 'testing' (episode creation returned None)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [4] (valid range: 0-1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 36212.22901344299 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'fastapi'
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [4] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 74100.56495666504 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'database'
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 114595.23391723633 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'routing'
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 120s: rule_fastapi-python_schemas
WARNING:guardkit.knowledge.template_sync:[Graphiti] Failed to sync rule 'schemas' (episode creation returned None)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1, 5] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 101709.45382118225 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'dependencies'
INFO:guardkit.knowledge.template_sync:[Graphiti] Template sync complete: 1 template, 3 agents, 6 rules synced (1468.2s)
  Template content synced to Graphiti

GuardKit initialized successfully!

Next steps:
  1. Create a task: /task-create "Your first task"
  2. Work on it: /task-work TASK-XXX
  3. Complete it: /task-complete TASK-XXX
richardwoollcott@Richards-MBP vllm-profiling %