richardwoollcott@Richards-MBP vllm-profiling % guardkit init fastapi-python -n vllm-profiling --copy-graphiti-from ~/Projects/appmilla_github/guardkit
Initializing GuardKit in /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling
  Project: vllm-profiling
  Template: fastapi-python

Step 1: Applying template...
INFO:guardkit.cli.init:Skipping agent fastapi-database-specialist-ext.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/agents/fastapi-database-specialist-ext.md
INFO:guardkit.cli.init:Skipping agent fastapi-database-specialist.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/agents/fastapi-database-specialist.md
INFO:guardkit.cli.init:Skipping agent fastapi-specialist-ext.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/agents/fastapi-specialist-ext.md
INFO:guardkit.cli.init:Skipping agent fastapi-specialist.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/agents/fastapi-specialist.md
INFO:guardkit.cli.init:Skipping agent fastapi-testing-specialist-ext.md: already exists at /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/agents/fastapi-testing-specialist-ext.md
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
  Seeding episode 1/3...WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [6] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1, 6] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [11] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1, 3, 4] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [9, 11, 25, 34] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [5] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [7, 12, 13, 15, 33] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 2, 5, 6] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [8, 22, 35, 39] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [6, 7, 9, 14, 18, 24] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [6, 10, 13, 25, 33, 37] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [9, 11, 15, 35] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [12] (valid range: 0--1 for EXISTING FACTS)
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 300s: project_purpose_vllm-profiling
 done (300.5s)
  Seeding episode 2/3.../Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/base_events.py:2031: RuntimeWarning: coroutine 'resolve_extracted_edge' was never awaited
  handle = self._ready.popleft()
RuntimeWarning: Enable tracemalloc to get the object allocation traceback
INFO:graphiti_core.graphiti:Completed add_episode in 111893.93091201782 ms
 done (112.3s)
  Seeding episode 3/3...INFO:graphiti_core.graphiti:Completed add_episode in 98699.25498962402 ms
 done (99.1s)
  Project knowledge seeded successfully (511.9s total)
    OK project_overview: Seeded from CLAUDE.md

GuardKit initialized successfully!

Next steps:
  1. Seed system knowledge: guardkit graphiti seed-system
  2. Create a task: /task-create "Your first task"
  3. Work on it: /task-work TASK-XXX
  4. Complete it: /task-complete TASK-XXX
richardwoollcott@Richards-MBP vllm-profiling % guardkit init fastapi-python -n vllm-profiling --copy-graphiti-from ~/Projects/appmilla_github/guardkit
Initializing GuardKit in /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling
  Project: vllm-profiling
  Template: fastapi-python

Step 1: Applying template...
INFO:guardkit.cli.init:Copied agent fastapi-database-specialist-ext.md → /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/agents/fastapi-database-specialist-ext.md
INFO:guardkit.cli.init:Copied agent fastapi-database-specialist.md → /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/agents/fastapi-database-specialist.md
INFO:guardkit.cli.init:Copied agent fastapi-specialist-ext.md → /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/agents/fastapi-specialist-ext.md
INFO:guardkit.cli.init:Copied agent fastapi-specialist.md → /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/agents/fastapi-specialist.md
INFO:guardkit.cli.init:Copied agent fastapi-testing-specialist-ext.md → /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/agents/fastapi-testing-specialist-ext.md
INFO:guardkit.cli.init:Copied agent fastapi-testing-specialist.md → /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/agents/fastapi-testing-specialist.md
INFO:guardkit.cli.init:Copied 6 agent(s): fastapi-database-specialist-ext.md, fastapi-database-specialist.md, fastapi-specialist-ext.md, fastapi-specialist.md, fastapi-testing-specialist-ext.md, fastapi-testing-specialist.md
INFO:guardkit.cli.init:Copied rule api/dependencies.md → /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/rules/api/dependencies.md
INFO:guardkit.cli.init:Copied rule api/routing.md → /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/rules/api/routing.md
INFO:guardkit.cli.init:Copied rule api/schemas.md → /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/rules/api/schemas.md
INFO:guardkit.cli.init:Copied rule code-style.md → /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/rules/code-style.md
INFO:guardkit.cli.init:Copied rule database/crud.md → /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/rules/database/crud.md
INFO:guardkit.cli.init:Copied rule database/migrations.md → /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/rules/database/migrations.md
INFO:guardkit.cli.init:Copied rule database/models.md → /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/rules/database/models.md
INFO:guardkit.cli.init:Copied rule guidance/database.md → /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/rules/guidance/database.md
INFO:guardkit.cli.init:Copied rule guidance/fastapi.md → /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/rules/guidance/fastapi.md
INFO:guardkit.cli.init:Copied rule guidance/testing.md → /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/rules/guidance/testing.md
INFO:guardkit.cli.init:Copied rule patterns/pydantic-constraints.md → /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/rules/patterns/pydantic-constraints.md
INFO:guardkit.cli.init:Copied rule testing.md → /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/rules/testing.md
INFO:guardkit.cli.init:Copied 12 rule(s)
INFO:guardkit.cli.init:Copied root CLAUDE.md → /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/CLAUDE.md
INFO:guardkit.cli.init:Copied .claude/CLAUDE.md → /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/CLAUDE.md
INFO:guardkit.cli.init:Copied CLAUDE.md: CLAUDE.md, .claude/CLAUDE.md
INFO:guardkit.cli.init:Copied manifest.json → /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/manifest.json
INFO:guardkit.cli.init:Copied manifest.json
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
  Seeding episode 1/3...INFO:openai._base_client:Retrying request to /embeddings in 0.402702 seconds
INFO:openai._base_client:Retrying request to /embeddings in 0.423471 seconds
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2, 13, 39] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 3, 4, 11] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 2, 15, 29] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2, 6, 27, 34] (valid range: 0-1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 2, 4, 8, 11, 23, 24] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 22, 25, 30, 37, 48] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2, 8, 21, 28, 29, 30] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 1, 5] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 8, 11, 18, 19, 25, 27, 29, 30, 31, 34, 37, 42, 46, 47] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 3, 7, 33] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [9] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 1, 3, 5, 26, 29, 44, 47] (valid range: 0--1 for EXISTING FACTS)
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 300s: project_purpose_vllm-profiling
 done (300.5s)
  Seeding episode 2/3...WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [4] (valid range: 0-1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 109749.82690811157 ms
 done (110.2s)
  Seeding episode 3/3...WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 15 out of bounds for chunk of size 15 in edge IS_PART_OF
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 15 out of bounds for chunk of size 15 in edge IS_PART_OF
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 15 out of bounds for chunk of size 15 in edge IS_PART_OF
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 15 out of bounds for chunk of size 15 in edge IS_PART_OF
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 15 out of bounds for chunk of size 15 in edge IS_PART_OF
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 15 out of bounds for chunk of size 15 in edge IS_PART_OF
WARNING:graphiti_core.utils.maintenance.edge_operations:Source index 16 out of bounds for chunk of size 15 in edge IS_PART_OF
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 17 out of bounds for chunk of size 15 in edge CONTAINS_PURPOSE
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 18 out of bounds for chunk of size 15 in edge CONTAINS_PURPOSE
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 19 out of bounds for chunk of size 15 in edge CONTAINS_PURPOSE
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 20 out of bounds for chunk of size 15 in edge CONTAINS_PURPOSE
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 21 out of bounds for chunk of size 15 in edge CONTAINS_PURPOSE
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 22 out of bounds for chunk of size 15 in edge CONTAINS_PURPOSE
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 23 out of bounds for chunk of size 15 in edge CONTAINS_PURPOSE
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 24 out of bounds for chunk of size 15 in edge CONTAINS_PURPOSE
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 25 out of bounds for chunk of size 15 in edge CONTAINS_PURPOSE
WARNING:graphiti_core.utils.maintenance.edge_operations:Source index 16 out of bounds for chunk of size 15 in edge CONTAINS_PURPOSE
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 27 out of bounds for chunk of size 15 in edge CONTAINS_PURPOSE
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 28 out of bounds for chunk of size 15 in edge CONTAINS_PURPOSE
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 29 out of bounds for chunk of size 15 in edge CONTAINS_PURPOSE
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 30 out of bounds for chunk of size 15 in edge CONTAINS_PURPOSE
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [9] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0-1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [4] (valid range: 0-1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 248833.96100997925 ms
 done (249.2s)
  Project knowledge seeded successfully (659.9s total)
    OK project_overview: Seeded from CLAUDE.md

GuardKit initialized successfully!

Next steps:
  1. Seed system knowledge: guardkit graphiti seed-system
  2. Create a task: /task-create "Your first task"
  3. Work on it: /task-work TASK-XXX
  4. Complete it: /task-complete TASK-XXX
richardwoollcott@Richards-MBP vllm-profiling %