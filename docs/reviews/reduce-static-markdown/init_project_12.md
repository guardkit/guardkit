richardwoollcott@Richards-MBP vllm-profiling % guardkit init fastapi-python -n vllm-profiling --copy-graphiti-from ~/Projects/ap
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
  Copied Graphiti config from /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/graphiti.yaml to
.guardkit/graphiti.yaml

Step 2: Seeding project knowledge to Graphiti...
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
  Seeding episode 1/3...WARNING:graphiti_core.utils.maintenance.edge_operations:Target index -1 out of bounds for chunk of size 15 in edge IS_PART_OF_PROJECT
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index -1 out of bounds for chunk of size 15 in edge IS_PART_OF_PROJECT
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index -1 out of bounds for chunk of size 15 in edge IS_PART_OF_PROJECT
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index -1 out of bounds for chunk of size 15 in edge IS_PART_OF_FEATURE
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index -1 out of bounds for chunk of size 15 in edge CONTAINS_FILE
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index -1 out of bounds for chunk of size 15 in edge CONTAINS_FILE
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index -1 out of bounds for chunk of size 15 in edge IS_PART_OF_PROJECT
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index -1 out of bounds for chunk of size 15 in edge IS_PART_OF_PROJECT
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [8] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1, 5, 10, 20] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [6] (valid range: 0-1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [3, 26, 37, 45, 46] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2, 6] (valid range: 0-1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [11, 20] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [10, 11, 12, 23] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [3, 5] (valid range: 0-1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 253840.234041214 ms
 done (254.4s)
  Seeding episode 2/3...INFO:graphiti_core.graphiti:Completed add_episode in 107659.51895713806 ms
 done (108.1s)
  Seeding episode 3/3...WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 15 out of bounds for chunk of size 15 in edge CONTAINS_FILE
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 16 out of bounds for chunk of size 15 in edge CONTAINS_FILE
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 17 out of bounds for chunk of size 15 in edge CONTAINS_FILE
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0-1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [8] (valid range: 0-1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [40] (valid range: 0-1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [10] (valid range: 0-1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 248377.35295295715 ms
 done (248.8s)
  Project knowledge seeded successfully (611.3s total)
    OK project_overview: Seeded from CLAUDE.md

GuardKit initialized successfully!

Next steps:
  1. Seed system knowledge: guardkit graphiti seed-system
  2. Create a task: /task-create "Your first task"
  3. Work on it: /task-work TASK-XXX
  4. Complete it: /task-complete TASK-XXX
richardwoollcott@Richards-MBP vllm-profiling %