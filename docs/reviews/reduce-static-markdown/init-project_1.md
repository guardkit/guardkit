richardwoollcott@Richards-MBP vllm-profiling % guardkit init fastapi-python -n vllm-profiling --copy-graphiti-from ~/Projects/appmilla_github/guardkit

Initializing GuardKit in /Users/richardwoollcott/Projects/appmilla_github/model-profiling/vllm-profiling
  Project: vllm-profiling
  Template: fastapi-python

Step 1: Applying template...
INFO:guardkit.cli.init:Copied agent fastapi-database-specialist.md → /Users/richardwoollcott/Projects/appmilla_github/model-profiling/vllm-profiling/.claude/agents/fastapi-database-specialist.md
INFO:guardkit.cli.init:Copied agent fastapi-specialist.md → /Users/richardwoollcott/Projects/appmilla_github/model-profiling/vllm-profiling/.claude/agents/fastapi-specialist.md
INFO:guardkit.cli.init:Copied agent fastapi-testing-specialist.md → /Users/richardwoollcott/Projects/appmilla_github/model-profiling/vllm-profiling/.claude/agents/fastapi-testing-specialist.md
INFO:guardkit.cli.init:Copied 3 agent(s): fastapi-database-specialist.md, fastapi-specialist.md, fastapi-testing-specialist.md
INFO:guardkit.cli.init:Copied rule api/dependencies.md → /Users/richardwoollcott/Projects/appmilla_github/model-profiling/vllm-profiling/.claude/rules/api/dependencies.md
INFO:guardkit.cli.init:Copied rule api/routing.md → /Users/richardwoollcott/Projects/appmilla_github/model-profiling/vllm-profiling/.claude/rules/api/routing.md
INFO:guardkit.cli.init:Copied rule api/schemas.md → /Users/richardwoollcott/Projects/appmilla_github/model-profiling/vllm-profiling/.claude/rules/api/schemas.md
INFO:guardkit.cli.init:Copied rule code-style.md → /Users/richardwoollcott/Projects/appmilla_github/model-profiling/vllm-profiling/.claude/rules/code-style.md
INFO:guardkit.cli.init:Copied rule database/crud.md → /Users/richardwoollcott/Projects/appmilla_github/model-profiling/vllm-profiling/.claude/rules/database/crud.md
INFO:guardkit.cli.init:Copied rule database/migrations.md → /Users/richardwoollcott/Projects/appmilla_github/model-profiling/vllm-profiling/.claude/rules/database/migrations.md
INFO:guardkit.cli.init:Copied rule database/models.md → /Users/richardwoollcott/Projects/appmilla_github/model-profiling/vllm-profiling/.claude/rules/database/models.md
INFO:guardkit.cli.init:Copied rule guidance/database.md → /Users/richardwoollcott/Projects/appmilla_github/model-profiling/vllm-profiling/.claude/rules/guidance/database.md
INFO:guardkit.cli.init:Copied rule guidance/fastapi.md → /Users/richardwoollcott/Projects/appmilla_github/model-profiling/vllm-profiling/.claude/rules/guidance/fastapi.md
INFO:guardkit.cli.init:Copied rule guidance/testing.md → /Users/richardwoollcott/Projects/appmilla_github/model-profiling/vllm-profiling/.claude/rules/guidance/testing.md
INFO:guardkit.cli.init:Copied rule patterns/pydantic-constraints.md → /Users/richardwoollcott/Projects/appmilla_github/model-profiling/vllm-profiling/.claude/rules/patterns/pydantic-constraints.md
INFO:guardkit.cli.init:Copied rule testing.md → /Users/richardwoollcott/Projects/appmilla_github/model-profiling/vllm-profiling/.claude/rules/testing.md
INFO:guardkit.cli.init:Copied 12 rule(s)
INFO:guardkit.cli.init:Copied root CLAUDE.md → /Users/richardwoollcott/Projects/appmilla_github/model-profiling/vllm-profiling/CLAUDE.md
INFO:guardkit.cli.init:Copied .claude/CLAUDE.md → /Users/richardwoollcott/Projects/appmilla_github/model-profiling/vllm-profiling/.claude/CLAUDE.md
INFO:guardkit.cli.init:Copied CLAUDE.md: CLAUDE.md, .claude/CLAUDE.md
INFO:guardkit.cli.init:Copied manifest.json → /Users/richardwoollcott/Projects/appmilla_github/model-profiling/vllm-profiling/.claude/manifest.json
INFO:guardkit.cli.init:Copied manifest.json
INFO:guardkit.cli.init:Applied template 'fastapi-python' to /Users/richardwoollcott/Projects/appmilla_github/model-profiling/vllm-profiling
  Applied template: fastapi-python
INFO:guardkit.cli.init:Copied graphiti config with project_id 'vllm-profiling' to /Users/richardwoollcott/Projects/appmilla_github/model-profiling/vllm-profiling/.guardkit/graphiti.yaml
  Copied Graphiti config from /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/graphiti.yaml to
.guardkit/graphiti.yaml

Step 2: Seeding project knowledge to Graphiti...
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'content' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'content' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'name' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'name' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'name' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'name' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'name' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'name' is already indexed
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:graphiti_core.graphiti:Completed add_episode in 46905.7891368866 ms
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:graphiti_core.graphiti:Completed add_episode in 79237.01500892639 ms
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Max pending queries exceeded

        MATCH (n:Entity)-[e:RELATES_TO]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'search_vector': [0.8180928230285645, -0.3056820034980774, -3.1608455181121826, -0.8809455633163452, 0.6314033269882202, -1.4858685731887817, 0.04485814645886421, 0.019639408215880394, -0.8694637417793274, 0.16430798172950745, -0.6121718287467957, 0.7835478186607361, 1.140513300895691, 0.32415372133255005, -0.573737621307373, -0.7866264581680298, 0.4865902066230774, -1.3385800123214722, -0.9489171504974365, -1.1249892711639404, -0.6477948427200317, -0.9014390110969543, 0.37010642886161804, -0.36322739720344543, 1.7089756727218628, 1.446396827697754, 1.0799309015274048, 0.06448408961296082, 0.26368263363838196, 0.9610093235969543, 1.1196995973587036, -0.2769685685634613, 0.06455186009407043, -0.4972175061702728, 0.18104374408721924, -0.5790082216262817, 0.5200841426849365, -0.4877893924713135, -0.20900771021842957, 0.37752577662467957, 0.005734668113291264, -0.4761173129081726, -0.13109274208545685, -0.9288330078125, 0.3601900041103363, -0.018500832840800285, -0.5678567290306091, -0.08985093235969543, 0.8140725493431091, -0.4479163587093353, 1.359001636505127, -0.5753030180931091, -0.13976691663265228, 0.4876062870025635, 0.2616245150566101, -0.9832907319068909, -0.1707332879304886, 0.855827808380127, -0.6338896155357361, -0.23762264847755432, 1.3249081373214722, 0.9028643369674683, -0.9808995723724365, 0.11094306409358978, 0.559485912322998, 0.10214143991470337, 0.24077831208705902, -0.28172391653060913, -0.36566612124443054, 0.21363112330436707, 0.837531566619873, 0.02010928839445114, 0.21853099763393402, -0.001678466796875, -0.8643583655357361, -0.0543670654296875, 0.37923476099967957, -0.8136435151100159, 0.029107486829161644, 0.47689640522003174, 1.1363166570663452, -0.038994282484054565, 0.9780560731887817, 0.48855769634246826, 1.460707664489746, 0.37827256321907043, -0.5372529625892639, 1.1619082689285278, -0.13902731239795685, 1.0603744983673096, 0.36461326479911804, 0.49705594778060913, 0.1056303158402443, 0.5455753207206726, -1.5755112171173096, 0.14346672594547272, 0.08537831157445908, -0.07267671823501587, -1.5939223766326904, -0.7942469120025635, -0.08025629073381424, -0.748664379119873, 0.18994140625, 1.0175997018814087, -0.17991727590560913, 0.09049808233976364, -0.15237247943878174, 0.04123104363679886, 0.8413301110267639, -0.22871847450733185, -0.7644617557525635, 0.24380314350128174, -1.186293601989746, 0.1688322126865387, 0.670051097869873, -0.9111902713775635, 2.117647171020508, -1.0139447450637817, -0.3895604610443115, 1.1125704050064087, -0.5291263461112976, -0.6846046447753906, 0.030443977564573288, 0.2110811173915863, 0.5811448097229004, 0.4524787366390228, -0.5165620446205139, 0.36380767822265625, 0.8011689782142639, 0.13503490388393402, -0.11372286081314087, -0.2726171016693115, -0.6502254605293274, 0.040130615234375, 1.512702465057373, 0.6598299741744995, -0.5739923119544983, -0.8157393336296082, 0.07895974814891815, 0.3816402554512024, -0.3610624372959137, 0.771721363067627, -0.4972032606601715, 0.7063778042793274, 0.05912421643733978, -1.1227335929870605, 0.2858312129974365, -0.30785953998565674, -2.018928050994873, 0.1334378868341446, -0.021189970895648003, 0.48472684621810913, -0.13758401572704315, -0.5637063384056091, -0.03431522101163864, -1.0826011896133423, -0.6689273715019226, 0.37204158306121826, -0.34979698061943054, 0.43250587582588196, -0.41240939497947693, 0.22368846833705902, -0.09224745631217957, 0.4763973355293274, -0.041816264390945435, -1.3048311471939087, 0.2741950452327728, 0.48191922903060913, 0.5131189823150635, -0.029356086626648903, -0.549811840057373, -0.2889763414859772, -0.05602836608886719, -0.38117530941963196, 0.4010225236415863, -0.42205810546875, 0.49856388568878174, -0.3887059688568115, 1.5113166570663452, 0.3322107791900635, 0.4095216691493988, -0.6410414576530457, 0.3676183223724365, -0.219329833984375, -1.033461570739746, -0.9182847142219543, -0.22748161852359772, -1.280388355255127, -0.7829410433769226, -1.0241806507110596, 0.23183520138263702, 0.5338924527168274, -1.0440458059310913, -1.2887753248214722, -1.0903750658035278, -0.7411103844642639, -0.22850395739078522, -0.9106732606887817, 0.46491914987564087, -0.6319081783294678, -0.6975672245025635, 0.09191805124282837, -1.3215762376785278, 0.39762744307518005, -0.40378838777542114, 1.1434326171875, -0.9984776973724365, 0.41066157817840576, -0.6161319613456726, 0.8932387232780457, 1.2800867557525635, -0.3451226055622101, -0.7985696196556091, -0.9488166570663452, 0.7462517023086548, -0.6736502051353455, -0.2191036492586136, 0.12824900448322296, -0.12012840807437897, 0.11465992778539658, -0.26397883892059326, -0.808342456817627, -0.15267226099967957, -1.2336138486862183, 0.9309037327766418, -0.06945531815290451, -0.9841523766517639, 0.32712599635124207, -0.4877678453922272, 0.1251581907272339, -0.1467464715242386, -1.6330996751785278, 0.8229325413703918, -0.48145338892936707, 0.2513159513473511, -0.19840015470981598, -0.6305577754974365, 1.2190515995025635, 0.09287217259407043, -0.5911120176315308, 0.0592041015625, -0.32511812448501587, 0.09926055371761322, 0.3255525529384613, -0.18721748888492584, 0.9464757442474365, 0.7600339651107788, -0.45496681332588196, 0.6276496648788452, 0.8361241817474365, -0.08307916671037674, 0.07288851588964462, -0.006907518953084946, 0.2741034924983978, 0.8627067804336548, -0.42704322934150696, -0.9992532134056091, -0.05766184255480766, -0.5287296175956726, -0.9687787294387817, -0.3843626081943512, -0.3078667223453522, 0.7287777066230774, -0.015438304282724857, 0.05550743639469147, 0.04777077957987785, -0.3222297132015228, -0.6746772527694702, 0.15947364270687103, -0.33917057514190674, -0.06338798254728317, 0.7478852868080139, 1.1378532648086548, 0.19388355314731598, -0.24444758892059326, -0.292248010635376, -0.4046655595302582, 1.106337547302246, -1.126784324645996, 0.380828857421875, -0.6869794130325317, -1.5856503248214722, 0.38481050729751587, 0.09184444695711136, -0.31224867701530457, 0.3727237582206726, 0.2621857225894928, 0.3773408830165863, -0.2200559675693512, -0.3058292269706726, 0.2593958377838135, 0.27338722348213196, -0.3975435197353363, 0.16163724660873413, 0.43010756373405457, 0.09404260665178299, 0.010487276129424572, 0.06511014699935913, 0.7513715028762817, -0.014459946192800999, 0.8897722959518433, 0.30915743112564087, 0.4846343994140625, 0.3358612060546875, -0.6512307524681091, -0.8764863610267639, -0.5618752837181091, 0.451416015625, 0.1349056512117386, 0.051221735775470734, -0.4979068636894226, -0.9300932288169861, -0.5748156309127808, 0.7174467444419861, -1.0149894952774048, 0.9417706727981567, 0.5959261655807495, 0.21286773681640625, -0.5460402369499207, 0.4269813001155853, -0.6831557154655457, -1.028923511505127, 0.04234403744339943, -0.804633617401123, 0.08477603644132614, 1.1776769161224365, -0.4150390625, 1.256089210510254, 0.679473876953125, -0.6639547944068909, 0.17507845163345337, 1.3581830263137817, 0.4787023067474365, -0.04400634765625, -0.7930189967155457, 0.9533476233482361, -0.9607579708099365, 0.717979907989502, -0.3619869351387024, -0.5452432036399841, 1.5104693174362183, 0.6162901520729065, 1.1036161184310913, -1.104912281036377, -0.062277402728796005, 0.8092471957206726, -1.577866554260254, 0.36083266139030457, 0.707099437713623, 0.536888599395752, 0.07904052734375, -0.631110668182373, -0.6274162530899048, -0.6012609004974365, -0.3548009395599365, 0.3907472491264343, -0.2049129754304886, 0.028911590576171875, 1.2291241884231567, -0.531928539276123, 0.10026101768016815, 0.04431668296456337, 0.18747486174106598, -0.5387788414955139, 0.664985179901123, 0.24831615388393402, 0.31385713815689087, 0.20077693462371826, 0.49865004420280457, 0.9063289761543274, -0.1519290655851364, 0.2191287726163864, -0.4232079088687897, 0.9676370024681091, 0.5169462561607361, 0.8097929358482361, -2.4019415378570557, 0.7600690126419067, -0.815162181854248, 1.5554450750350952, 0.42259934544563293, -0.3712925612926483, -0.07219022512435913, 0.08469974249601364, -0.34108150005340576, 0.2228851318359375, 0.09455905109643936, 0.5315874814987183, -0.26644203066825867, 1.1223574876785278, -0.5902602076530457, -0.659186840057373, -0.3707024157047272, 0.16021549701690674, -0.913933277130127, -0.6484267115592957, 1.0404986143112183, 0.5660573244094849, 0.47126320004463196, 1.1679974794387817, -1.0635340213775635, -0.7804897427558899, 0.6885555386543274, -0.5557717680931091, -0.6415871977806091, 0.701789379119873, -0.9319637417793274, -0.7257438898086548, 0.45326143503189087, 0.1052919253706932, 0.33739158511161804, 1.1008013486862183, 0.46920597553253174, -1.012336254119873, 0.12037389725446701, 0.782111644744873, 0.157989501953125, -0.021126242354512215, -0.31789711117744446, 0.701789379119873, 0.611198902130127, 0.35408470034599304, 0.2883552014827728, -0.23443065583705902, -0.3298160433769226, -0.5964499115943909, 0.8556554317474365, 0.8631950616836548, 0.356048583984375, -1.4015682935714722, -0.3552948534488678, 0.344684362411499, 0.9706636071205139, 0.29238396883010864, -0.027731502428650856, -0.6488395929336548, 0.6654698848724365, -0.5769563317298889, -0.7887447476387024, 0.16538463532924652, 0.539665699005127, -2.021627902984619, 0.8248506188392639, -0.765099048614502, 0.4463860094547272, 1.835585594177246, 0.2630184292793274, -0.39326387643814087, -1.4314682483673096, 0.9533296227455139, -0.07099825143814087, 0.538444995880127, -0.06718713790178299, -0.11993049085140228, 1.5424517393112183, 0.28147438168525696, 0.6437122225761414, -0.15579044818878174, 0.15530216693878174, -0.1139800101518631, 0.1037687435746193, -0.4879058301448822, -0.6204475164413452, 0.07076600193977356, 1.1045496463775635, -0.30632108449935913, 0.0798124447464943, -0.36392301321029663, 0.652045726776123, 0.6292437314987183, -0.583953857421875, -0.2512660324573517, 0.5561056733131409, -0.4906580448150635, 0.4200798571109772, -0.1611507683992386, 0.48790428042411804, -0.4301183223724365, 0.5286820530891418, 0.03538602963089943, -0.10722934454679489, 0.5216423273086548, -1.0225435495376587, -1.5862821340560913, -0.679694652557373, 0.9622371792793274, 0.29074546694755554, -0.26201316714286804, -0.08917780220508575, 0.6951545476913452, 0.07169836014509201, 0.699470043182373, -0.21240638196468353, 0.5249310731887817, 0.23866990208625793, -0.6421185731887817, 0.3883002698421478, 0.005512910895049572, 0.10930487513542175, 1.0425432920455933, 1.8309972286224365, 1.2513786554336548, 0.146392822265625, -0.48302146792411804, 0.480365514755249, -0.35816505551338196, 0.48780372738838196, 0.017706478014588356, -2.427964210510254, -1.1549898386001587, 0.6004638671875, 0.5947050452232361, 0.499969482421875, 0.7712366580963135, 0.5921505093574524, -0.6923971772193909, 0.4943138659000397, 0.7235538363456726, -0.4091455936431885, -0.5193804502487183, -0.8808306455612183, -0.6972683072090149, -0.2860407531261444, 0.3397791385650635, -0.5847697257995605, 0.25946044921875, 0.3435884416103363, 0.04086124151945114, 0.8479748964309692, 0.34381598234176636, 0.203582763671875, -0.7422987818717957, -1.149672508239746, -0.5341473817825317, 0.5804802179336548, 0.19849351048469543, -0.5037428736686707, 1.2761948108673096, -0.08805488049983978, 0.5877254605293274, -0.502489447593689, -0.7259916663169861, 0.5758110284805298, -0.17396096885204315, -0.3427303433418274, -1.245490550994873, 0.47024625539779663, -0.6470911502838135, -0.2960599958896637, -1.3594409227371216, 0.6789084076881409, -0.9644488096237183, 0.052544087171554565, -0.508293628692627, 0.34979113936424255, -1.0592544078826904, -0.34839943051338196, -0.20637422800064087, -0.9576918482780457, -0.032966166734695435, 0.20458266139030457, -0.5347423553466797, 0.8912712335586548, 0.33230769634246826, -0.014827054925262928, -0.030739279463887215, -0.2788216173648834, 0.285561740398407, 0.38802382349967957, 0.528327465057373, -0.4306910037994385, -0.023730110377073288, -0.03494829311966896, -0.0857759341597557, 0.2098604142665863, -0.026635563001036644, -0.3787590563297272, 0.536262035369873, 0.1735902726650238, -1.0200105905532837, 1.018928050994873, -0.8069628477096558, 0.7021986842155457, 0.012259090319275856, -0.568572998046875, 0.6683170199394226, 0.5490543246269226, -0.5196533203125, 0.7240439057350159, 0.05507570132613182, 0.4911319613456726, -0.20695585012435913, -0.21874865889549255, 0.6956643462181091, 0.1622440069913864, 0.5916963219642639, -0.3139073848724365, 0.26830336451530457, -0.4660518765449524, 0.33727309107780457, 0.0762544497847557, 0.6261955499649048, 0.8491929173469543, -0.03366829454898834, 0.280163049697876, -0.08587107807397842, 0.2983984053134918, -0.05321188643574715, 0.1805630922317505, -0.23694026470184326, 0.4465944766998291, -0.0296630859375, -0.5014935731887817, 0.514167308807373, 1.142075538635254, -0.09716078639030457, 0.7468100190162659, -0.057044535875320435, -1.0669662952423096, -0.8859719634056091, -0.40834179520606995, -0.3820011019706726, 0.759668231010437, 0.07279250025749207, 0.848991870880127, -0.3492014408111572, -1.0076230764389038, -0.42056095600128174, 0.5437220335006714, 1.213623046875, -0.24253396689891815, 0.48004868626594543, -0.04505740851163864, -1.1813102960586548, -1.008537769317627, 0.26622459292411804, -0.4502312242984772, -0.10800260305404663, 0.3220573961734772, 1.0033605098724365, 1.3249942064285278, -0.7225844264030457, -1.4781135320663452, 0.34912288188934326, 0.1030668392777443, -0.9638240933418274, 0.5049420595169067, 0.636162281036377, 1.4647575616836548, 0.24821870028972626, 1.9675723314285278, 2.402860641479492, 0.814208984375, -0.5377520322799683, 0.22008739411830902, -0.04759665206074715, 0.6685270667076111, -0.7126177549362183, -0.33375459909439087, -1.109877586364746, 0.10999253392219543, -0.2103091925382614, -0.7144129276275635, -0.6355555057525635, 0.6480569243431091, 0.011208927258849144, 0.3449282944202423, 0.3707616329193115, -0.8254313468933105, -0.799232006072998, 0.43657952547073364, 0.3158280849456787, 0.13245166838169098, -0.915656566619873, 0.13492539525032043, 0.6612440943717957, 1.3340705633163452, 0.6225733757019043, -0.46214205026626587, -0.3919713497161865, -0.11862541735172272, -0.32044532895088196, 0.3455965518951416, -0.08251234889030457, 0.2482360452413559, -0.5900376439094543, 0.863563060760498, -1.6655848026275635, -0.07609468698501587, -0.2257232666015625, -0.7757119536399841, -0.9641472101211548, -0.9581944942474365, -0.3122074007987976, -0.3444065749645233, -0.030160343274474144, -0.8858752250671387, -0.6968204379081726, -0.2181216925382614, 2.1035730838775635, 0.3504270613193512, 0.04428190365433693, 0.21162639558315277, 1.5779238939285278, -0.6406262516975403, 0.6190813779830933, 0.09425892680883408, 0.22057880461215973, 0.1628902703523636, -0.12826000154018402, -0.9949171543121338, 0.6398638486862183, 0.028022317215800285, 0.3456761837005615, -0.43669578433036804, 0.577125072479248, -0.3240266740322113, 0.3440821170806885, -0.3294103145599365, -0.7887752652168274, 1.390395164489746, -0.29213401675224304, -1.2130351066589355, 0.3373844027519226, 0.49828025698661804, 0.852790355682373, 1.1206485033035278, -1.0736587047576904, 1.2279843091964722, -1.1071059703826904, 0.4480559527873993, -0.665153980255127, -0.8742388486862183, 0.9368537664413452, -0.35670650005340576, -0.2119320183992386, 0.5439183712005615, 0.4985247254371643, -0.44505760073661804, -0.009250416420400143, -1.2825424671173096, -0.1640445441007614, -0.4001372754573822, 1.5689051151275635, -0.32310351729393005, -0.21920955181121826, 0.2517789900302887, 0.20676736533641815, 0.6193996667861938, -0.09152401238679886, 0.39368173480033875, -0.041512880474328995, -0.053001292049884796, -0.027803827077150345, 0.012000588700175285, 0.592353343963623, 0.007123161572962999, -0.1591464728116989, 1.4055606126785278, 0.608642578125, 0.593024730682373, -0.6507281064987183, 0.15922456979751587, 1.1785888671875, -0.7207605838775635, -0.8321245908737183, -1.239372730255127, 0.2801569700241089], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'edge_uuids': ['2d7d5b7a-c883-45f9-9964-fac0d64f8910'], 'group_ids': ['vllm-profiling__project_overview']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Max pending queries exceeded

        MATCH (n:Entity)-[e:RELATES_TO]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'search_vector': [-0.20157186686992645, 0.235884889960289, -3.1073288917541504, -0.8730207085609436, 0.6505875587463379, -2.192103862762451, -0.1721874475479126, 0.800810694694519, -1.1136300563812256, -0.6347365379333496, -0.032203309237957, 0.7509968876838684, 1.3630945682525635, 0.6308128833770752, -0.36309173703193665, -0.4365962743759155, -0.4924258291721344, -0.4075404703617096, 1.0484154224395752, -0.3849320113658905, -0.6319565773010254, -0.2449609637260437, 0.1000918447971344, 0.449462890625, 1.8791271448135376, 1.047693133354187, 0.7909226417541504, -0.1891232430934906, -0.4967433512210846, 0.5453956127166748, 0.491635262966156, -0.0884290412068367, -0.3786359429359436, -0.4408918023109436, -0.6797398328781128, -0.6737721562385559, 0.597406268119812, 0.13160379230976105, -0.3725934624671936, 1.5660109519958496, -0.2938697338104248, 0.4351944625377655, -0.768823504447937, 0.6948329210281372, -0.6413639783859253, -0.4500514566898346, -0.962588369846344, -0.0028113410808146, 0.543972909450531, 0.570468008518219, 0.478333979845047, 0.783383309841156, -0.07223274558782578, -0.5774042010307312, 1.7380021810531616, 0.033107940107584, 0.5175316333770752, 0.9126790165901184, -0.4611736536026001, -1.002208948135376, 1.258533239364624, 0.9113842248916626, -0.5039069652557373, 2.2786691188812256, 1.0958542823791504, -0.3804568350315094, -0.8886834979057312, 0.4035385549068451, 0.1453515887260437, 0.13862428069114685, 0.6793910264968872, -0.1268049031496048, 0.27956971526145935, 0.18670763075351715, 0.5442315936088562, 0.9571009874343872, -0.2451213151216507, 0.3654712438583374, -0.4042016863822937, 1.4558802843093872, 0.17163684964179993, 0.37834566831588745, -0.06035950034856796, -0.023899078369140625, 1.0139000415802002, 1.1843611001968384, 0.4982852041721344, 0.003943306859582663, -0.0100399199873209, 1.2524181604385376, -0.495817631483078, 0.0802249014377594, -0.10759299248456955, 0.385836660861969, -0.5448107123374939, 0.0255715511739254, 0.212509885430336, -0.12335205078125, -0.34284719824790955, -0.2163165807723999, -0.013188498094677925, -0.3012811541557312, 0.5289931297302246, 0.3185947835445404, 0.9226887822151184, 1.212634801864624, -0.4556238055229187, -0.012951805256307125, -0.2729191482067108, 0.27723148465156555, 0.19354502856731415, 1.0372750759124756, 1.1982421875, -0.258299320936203, -0.5758550763130188, -0.8234369158744812, 0.9827764630317688, -1.197870135307312, 0.0797119140625, 0.7659476399421692, -0.16574496030807495, -0.4383319616317749, 0.5724196434020996, 0.9374186396598816, -0.0313778817653656, 0.5061413049697876, -0.7021706104278564, 0.0960809588432312, 0.5504433512687683, -0.6272459626197815, -0.16269665956497192, -0.7709728479385376, -0.509219229221344, 0.06402637809515, 0.5081525444984436, 1.1056474447250366, -0.7126348614692688, -0.48754382133483887, -0.03483245521783829, 1.2052525281906128, -0.3065868616104126, 0.158934086561203, 0.1209673210978508, -0.18359608948230743, 0.11402148008346558, -1.3132920265197754, 1.484441876411438, -0.8929283618927002, -0.6702532172203064, 0.1589326411485672, -0.3104916512966156, 0.43025851249694824, -0.497683584690094, -0.2717357873916626, -0.10465313494205475, -0.5764683485031128, 0.1346522718667984, -0.25707826018333435, 0.0494181327521801, -0.210905522108078, 0.1893194317817688, 0.670474112033844, -0.2914283275604248, 0.6036260724067688, -0.4711478054523468, -1.285290002822876, 1.0168644189834595, -0.12158430367708206, -0.2789735198020935, 0.658267080783844, 0.1461283415555954, -0.664770245552063, -0.5735052227973938, -0.4266095757484436, 0.250730961561203, -0.4617520272731781, 0.0589243583381176, -0.103928342461586, 1.7959681749343872, -0.4562566876411438, 0.02704293467104435, -1.0458054542541504, 0.33088356256484985, 0.2134370356798172, -0.5119643211364746, 0.01834760420024395, -0.6428571343421936, -0.8219364881515503, -1.0000531673431396, 0.0073256720788776875, 0.334776371717453, 0.3996814489364624, -1.1259416341781616, -0.4868816137313843, 0.7299906611442566, -0.4643104076385498, -0.1439245343208313, -0.5020911693572998, 0.4120418131351471, -0.9196602702140808, -0.8753865361213684, -0.2193981409072876, -0.5489890575408936, 0.5780552625656128, -0.9400896430015564, 1.225452184677124, 0.1506754606962204, 0.7944458723068237, -0.19145093858242035, 0.8346877098083496, 1.5458287000656128, -1.1876976490020752, -0.2096056193113327, -0.02008928544819355, 0.5875563621520996, -0.8092970848083496, -0.4195004403591156, -0.326386958360672, -0.3325151801109314, 0.13997013866901398, 0.2052023708820343, 0.0581548772752285, 0.7285003662109375, -0.40503165125846863, 1.1208728551864624, 0.15500204265117645, -0.5851237177848816, -0.6914411187171936, -0.5971825122833252, -0.3155052661895752, -0.4870212972164154, -1.7705078125, 0.4107564389705658, 1.043468713760376, 0.17478179931640625, 0.072861447930336, 0.1860874742269516, 0.7270951271057129, 0.007246834691613913, -0.7220371961593628, -0.346893310546875, 0.8543859124183655, 0.22197450697422028, -0.096412293612957, -0.8464239239692688, -0.0394541434943676, -1.1099271774291992, -0.5617356300354004, 0.113600954413414, 1.2857840061187744, 0.5232456922531128, -0.5636102557182312, 0.3144385814666748, 0.62396240234375, 0.9058648943901062, -0.3437558114528656, 0.038301557302474976, -0.0396917425096035, 0.388154536485672, -1.0130659341812134, -1.4809802770614624, -0.1374424546957016, 0.9521135687828064, -0.4282291829586029, -0.2019624263048172, -0.0477643683552742, -0.2799515426158905, 0.6461966633796692, 0.137318953871727, -0.5971360206604004, -0.1070985347032547, 0.00896344892680645, 0.0805620476603508, -0.04686664417386055, 0.48773193359375, 0.2999921441078186, 0.41791316866874695, 1.164318323135376, -0.8884328007698059, 0.4503551721572876, -0.0397324338555336, -0.7711588740348816, -0.3682490885257721, 0.3404947817325592, -0.61181640625, 0.278626948595047, 0.6680172681808472, 0.9891648292541504, 0.6382257342338562, 0.3730989098548889, -0.1761707067489624, -0.7358630895614624, -0.1171613410115242, -0.5055251121520996, -0.1237596794962883, -0.179991215467453, 0.3342241644859314, 0.4238717257976532, 0.0917009636759758, -0.4633411169052124, -0.0350625179708004, -0.1204252690076828, 1.3529691696166992, 0.1027664914727211, -1.1122581958770752, -0.6064191460609436, -0.7306315302848816, -0.8191393613815308, 0.256715327501297, 0.232118159532547, -0.2400127649307251, 0.0710529163479805, -1.0824265480041504, 0.9761788249015808, -0.8295215368270874, 0.2789953351020813, -0.014422462321817875, 0.08314496278762817, 1.0635986328125, -0.4936581552028656, 0.0244925357401371, -0.7308524250984192, -0.8516438603401184, -0.9120105504989624, 0.6201767921447754, 0.4021075963973999, -0.4606606662273407, 1.2184187173843384, 1.0455148220062256, -0.3441024124622345, -0.0402228944003582, 0.4160853922367096, 0.3556751012802124, -1.176013708114624, -0.2881033718585968, 0.7735304832458496, 0.2450445294380188, 0.8560064435005188, -0.2507738471031189, 0.864019513130188, 2.0031330585479736, -0.1063363179564476, -0.12545521557331085, -0.5732134580612183, -0.4552183747291565, 0.1371837854385376, -1.2191162109375, 0.25644975900650024, 1.3149763345718384, 1.8169991970062256, -0.6247729063034058, 0.355496346950531, -0.15048286318778992, 0.2353341281414032, 0.398286372423172, 0.0828915536403656, 0.5450541377067566, -0.856875479221344, 0.9409586787223816, 0.36794933676719666, 0.8729567527770996, -0.4639885425567627, -0.0037827263586223125, -1.5350167751312256, 0.1613653302192688, 0.7127213478088379, 1.1381545066833496, 0.19436563551425934, 0.02097574807703495, -0.0183708555996418, 0.6507103443145752, -0.440367192029953, 0.38880592584609985, 0.48868343234062195, 0.2074497789144516, 0.2547692656517029, -1.202020525932312, -0.5438633561134338, -0.3779369592666626, 1.5048363208770752, -0.3897952139377594, -0.5209699273109436, -0.2590273916721344, 0.8352225422859192, 0.4607551097869873, -0.5118201375007629, -0.4541575014591217, 0.24716512858867645, 0.4881097674369812, 1.4452543258666992, -0.0012555803405120969, -0.0799502432346344, -0.6229683756828308, -0.48131707310676575, -0.5101304054260254, -0.5462086796760559, 0.5802617073059082, 0.30434009432792664, -0.5645577311515808, 0.698614239692688, -1.2506800889968872, 0.1041521355509758, 1.078380823135376, -0.4562145471572876, -0.016386553645133972, 0.21992310881614685, -0.15848463773727417, -0.9979364275932312, 0.9946376085281372, 0.0923055037856102, -0.1339787095785141, 0.42462158203125, 0.0022757393307983875, -1.4459519386291504, 0.3728797435760498, 0.7149609327316284, 0.6617664098739624, -0.7279815673828125, -0.8302931785583496, -0.8285057544708252, 0.03078497014939785, -0.1508999764919281, -0.30356162786483765, 0.45870548486709595, 0.0951806902885437, -0.8595773577690125, 1.1881742477416992, 0.8005719780921936, -0.0776011124253273, -1.1321556568145752, -0.14018648862838745, 0.3562549352645874, 0.114661805331707, 0.3127739429473877, -0.29307520389556885, -0.229095458984375, -0.10038105398416519, -0.3585779070854187, -0.179444819688797, 1.3346121311187744, -0.11909770965576172, -1.5287853479385376, 0.7334740161895752, 0.04634566605091095, -0.526422381401062, 1.0373274087905884, 0.425167977809906, 0.0898495614528656, -0.7838236689567566, 1.416387677192688, 0.8918006420135498, -0.4009406566619873, 0.3805992603302002, 0.01787894032895565, 2.193173408508301, -0.103325255215168, -0.05897994339466095, -0.4140625, 1.492931604385376, -0.2660653293132782, -0.2526404857635498, 0.520635724067688, -2.393368721008301, 1.47412109375, -0.10599154233932495, -0.4018961489200592, 0.2127620130777359, -0.7654709815979004, 0.5382726788520813, 1.164562463760376, -0.0661097913980484, -0.0300583615899086, 0.8995012640953064, -0.3001970648765564, 0.058514006435871124, 0.7123122215270996, 0.737188458442688, 0.221298947930336, -0.502685546875, 0.8879801630973816, -0.3835100531578064, 0.12323334068059921, -1.0622326135635376, -0.5878550410270691, -0.849187970161438, 0.06462442129850388, 0.5620582103729248, 0.16074153780937195, 0.0169826690107584, 0.2603142261505127, 0.0463838130235672, 0.8555123209953308, 0.4312300980091095, 0.820343017578125, -0.5017322301864624, -1.091924786567688, -0.2968285083770752, 0.270536869764328, -0.09996425360441208, 1.3022925853729248, 0.6441156268119812, 0.4316042959690094, 1.2061011791229248, -0.2921142578125, -0.1279318630695343, 0.9717029333114624, 1.1827915906906128, 0.9248744249343872, -2.1370441913604736, -0.6478627324104309, -0.2461068332195282, 0.398438960313797, -0.839291512966156, -0.1780366450548172, -0.12524178624153137, -1.1949026584625244, 0.24041765928268433, 0.1782015860080719, -0.16053816676139832, 0.8000255823135376, 0.2223474383354187, -0.4802100658416748, 0.146682009100914, -1.067193865776062, -0.5334835052490234, 1.191650390625, 0.7965494990348816, -0.7527233362197876, 0.5213662981987, -0.38294366002082825, 0.2702418863773346, -0.4274604320526123, -0.04844524711370468, -0.4995347857475281, -0.3717949390411377, -0.7378467321395874, 0.3997337818145752, 0.3959815502166748, -0.297151654958725, 0.7920386791229248, 0.5876842737197876, -1.1496232748031616, 0.4960806667804718, -0.0725155770778656, -0.9504162073135376, -0.5113990306854248, 0.3548213541507721, 0.8177838921546936, -0.1332758516073227, -0.813662588596344, 1.8007347583770752, -1.254266619682312, -0.0516415536403656, -0.0752120241522789, 0.178208127617836, -0.7265392541885376, 0.936343252658844, 0.17533940076828003, -0.4888741672039032, -1.2073218822479248, -0.09213220328092575, 0.0503278449177742, 0.4583972692489624, -1.3294038772583008, 0.2905418872833252, 0.17627207934856415, -0.04283323884010315, 0.4871738851070404, 0.1138494610786438, 0.386258065700531, -0.7762458324432373, -1.3174757957458496, 0.0788181871175766, -0.0439395010471344, -0.19588887691497803, -0.2629917562007904, 0.7105799913406372, 0.661587655544281, -0.16175846755504608, -1.072293996810913, -0.1952747106552124, -0.899594247341156, 0.5441167950630188, -0.00962248258292675, -0.7349591851234436, 0.5850365161895752, 0.13406771421432495, -1.1012136936187744, -0.284481942653656, 0.052759625017642975, 0.09297288954257965, -0.0747738778591156, -0.3965541422367096, 0.3707653284072876, 0.384458988904953, 0.0417829230427742, -0.616787850856781, 0.114699587225914, 0.0426781065762043, 0.00959123857319355, 0.1529729962348938, 0.1040053591132164, 1.1282320022583008, 0.5206080675125122, -0.3548816442489624, 0.9931262731552124, -0.1207057386636734, 0.026509420946240425, -0.7998453974723816, -0.1914847195148468, 0.9678693413734436, 0.466580331325531, -0.3953595757484436, -0.2131260484457016, -0.5482521057128906, -0.7574811577796936, 0.865170419216156, 0.3654349148273468, -0.8347429633140564, -0.5292198657989502, 0.0497334785759449, -1.038818359375, 0.5049922466278076, 0.293215811252594, 1.6161412000656128, -0.2670200765132904, -1.0348539352416992, -0.28697213530540466, -0.23548853397369385, 0.6600211262702942, -0.6727207899093628, 0.4196283221244812, -2.4038784503936768, -1.8467378616333008, -0.461367666721344, 0.0976271852850914, -1.143054723739624, -0.5557715892791748, 0.9170735478401184, 0.681698739528656, 1.3625720739364624, -0.06657518446445465, 0.0990309938788414, -0.7439778447151184, -0.1032424196600914, -0.854800283908844, -0.3024844229221344, 0.38929376006126404, 0.993902325630188, -0.0508364737033844, 1.1150308847427368, 1.683477520942688, 1.7766927480697632, -0.5702571868896484, 0.3039071261882782, -0.95305997133255, -0.1185804083943367, -0.897943377494812, -1.2220052480697632, -0.7342151403427124, -0.444216787815094, 0.1080460324883461, 0.032778240740299225, 0.382662832736969, -0.1001310795545578, -0.325070321559906, -0.09495344758033752, 0.17910802364349365, -1.211786150932312, -0.7446579933166504, -0.3405340313911438, 0.1438046395778656, 0.3900393545627594, 0.0559227354824543, 0.22015216946601868, 0.929864764213562, 0.7348014116287231, 0.7763904333114624, -0.3395618200302124, -0.9412434697151184, -0.3162434995174408, -0.4383602738380432, 0.2477395236492157, -1.146716833114624, 0.07231976091861725, -0.181198850274086, 0.1441519558429718, -1.3094656467437744, -0.8403727412223816, -0.5863211750984192, -0.906005859375, -1.4189192056655884, 0.8813872337341309, -0.8332112431526184, -0.1815221905708313, 0.0607663094997406, 0.6731044054031372, -0.2651287317276001, -2.071475028991699, 1.0027669668197632, -0.182814821600914, 0.2852405309677124, -0.8119855523109436, 0.3612322211265564, -0.13441503047943115, 0.5124562382698059, 0.5163130760192871, 0.4073435366153717, -0.1138857901096344, 0.7952038049697876, -0.7824946641921997, 0.352749764919281, -0.6766735315322876, 0.3079230785369873, -0.248628169298172, 1.2657499313354492, 0.5520862340927124, -1.1724504232406616, 0.170442134141922, 0.6099780797958374, 1.147197961807251, -0.3784136176109314, -1.1582118272781372, -0.16011828184127808, -0.2788936197757721, -0.662389874458313, 0.17163141071796417, -1.399158239364624, 1.5736171007156372, -0.649286150932312, 0.1370907723903656, 0.22244226932525635, -0.8274739384651184, -0.045326415449380875, -0.1900532990694046, 0.0963250994682312, 0.37304407358169556, 0.2098054438829422, -0.30122774839401245, -0.6270316243171692, -0.5360398292541504, 0.650518536567688, 0.6598103642463684, 0.3119528591632843, -0.4152148962020874, 0.1407848596572876, -0.45736920833587646, 0.7447161078453064, 0.9286760687828064, -0.7058396339416504, -1.256115198135376, -0.20423412322998047, -0.7690299153327942, -0.3236483633518219, -0.1082538440823555, 1.441534161567688, 0.5497516393661499, 0.21339325606822968, 1.8621652126312256, -0.26576849818229675, -0.24094226956367493, -0.6537039875984192, -0.010402134619653225, 0.439912348985672, -0.30066099762916565, -0.5961870551109314, -0.855462908744812, -0.274382084608078], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['vllm-profiling__project_overview']}
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
WARNING:guardkit.knowledge.graphiti_client:Episode creation request failed: Max pending queries exceeded
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Max pending queries exceeded

        MATCH (n:Entity)-[e:RELATES_TO]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'search_vector': [1.2831851243972778, 0.4312474727630615, -2.473173141479492, -0.5392186641693115, 1.5525619983673096, -1.347886085510254, -1.5826658010482788, -0.3909966051578522, -0.5650526881217957, 0.40411555767059326, -0.8060517907142639, 0.9161161780357361, 1.5779813528060913, 0.4676513671875, -1.2693301439285278, -0.3149440884590149, 0.5917268395423889, -0.97454833984375, -0.12046903371810913, -0.9335201382637024, -0.2520231306552887, -1.1737993955612183, 0.6334383487701416, -0.26162540912628174, 2.3723394870758057, 1.182509422302246, 0.7353013157844543, 0.2276701033115387, -0.2453828752040863, 0.4204065799713135, 1.069145679473877, -0.7147360444068909, 0.4754571318626404, -0.5970372557640076, -1.0878992080688477, -0.45687687397003174, 0.08022308349609375, 0.2879387438297272, -0.27401912212371826, 1.1926556825637817, 0.5251967310905457, -0.9576057195663452, -0.45958754420280457, 0.2911628186702728, -0.29621124267578125, -0.21447642147541046, 0.5229671597480774, 0.3435417711734772, 0.19198518991470337, -0.28304335474967957, 0.9172183871269226, 0.6571691036224365, -0.38518479466438293, 0.7293342351913452, 1.140625, -0.7604836821556091, -0.5192009210586548, 0.7051732540130615, 0.35072237253189087, -0.5038847327232361, 1.4331485033035278, -0.17748305201530457, -1.109877586364746, 0.8278548121452332, -0.003131137229502201, -0.831367015838623, -0.5104890465736389, -0.2575863003730774, -0.3328803479671478, -0.2998262345790863, 0.2715696394443512, 0.08625344932079315, -0.24564899504184723, -0.039011113345623016, -0.5270906090736389, -0.5051521062850952, -0.039604075253009796, -0.708305835723877, 0.11142326891422272, 0.5838946104049683, 1.123276710510254, 0.6790053248405457, 0.7713120579719543, 0.04412662237882614, 2.239358425140381, -0.8385224938392639, -0.45703125, 0.5497526526451111, -0.13454662263393402, 0.06847605854272842, 0.1306942254304886, 0.5663056969642639, 0.16805492341518402, 0.5968618988990784, -1.652846336364746, 0.34634533524513245, 0.1442084014415741, 0.37897446751594543, -0.4694178104400635, -0.8457174897193909, -0.010980942286550999, -0.950080394744873, 0.3017793595790863, -0.16192089021205902, 0.2254459112882614, 0.3834192752838135, -0.3925390839576721, -0.0665372982621193, -0.6276729702949524, -0.05879301205277443, -0.3554103970527649, 0.260498046875, -1.2182258367538452, 0.29350998997688293, -0.17706298828125, -0.33226463198661804, 1.4623448848724365, -1.598517894744873, -0.6208442449569702, 1.7957260608673096, -0.5266261100769043, -1.067064881324768, 0.8697509765625, 0.41480210423469543, -0.12526927888393402, 1.0624667406082153, -0.4630916714668274, -0.7575593590736389, 0.5984963774681091, -0.615325927734375, 0.4248558580875397, 0.248202383518219, -0.4394616484642029, -0.3622775375843048, 1.4925249814987183, 1.0942095518112183, -0.7287794947624207, -0.27793973684310913, 0.63250732421875, 0.8094841241836548, -0.26521211862564087, 0.7300594449043274, -0.050514668226242065, -0.1801273077726364, -0.35154813528060913, 0.08153096586465836, 0.749687671661377, -0.10713779181241989, -0.3977912366390228, -0.16220451891422272, -0.12477380782365799, 0.801154613494873, 0.2970491349697113, -0.4765409529209137, -0.12733548879623413, -1.6263211965560913, -1.155388355255127, -0.03869988024234772, -0.23582907021045685, 0.39509132504463196, 0.27285587787628174, 0.5974466800689697, -0.2088470458984375, 0.5937230587005615, -0.23811250925064087, -0.29907989501953125, -0.1338375359773636, 0.9333854913711548, 0.8617374300956726, 0.37611299753189087, -1.1187851428985596, -0.30404213070869446, -0.34111830592155457, -0.18296903371810913, 0.39457961916923523, -0.3273346722126007, 0.1064484566450119, -1.0648910999298096, 1.409064769744873, -0.17691758275032043, 0.9909380674362183, -0.219309464097023, 0.3520902693271637, 0.20419849455356598, -1.0581629276275635, -0.8956657648086548, 0.030467314645648003, -0.6690642237663269, -0.7958095669746399, -0.7700159549713135, 0.6368035674095154, 0.370808869600296, -1.5236098766326904, -0.7989802360534668, -0.3727928698062897, -0.24817702174186707, -0.20441211760044098, -0.136311873793602, -0.02212703973054886, -0.9898896813392639, -0.4468492269515991, 0.42578843235969543, -1.3241689205169678, 1.1344784498214722, -1.1636316776275635, 0.6098130345344543, -0.7467399835586548, -0.011204439215362072, -1.12353515625, 1.206169605255127, 1.514091968536377, -0.7622213959693909, -0.7141938805580139, 0.00907987728714943, 0.15176212787628174, -0.3338587284088135, -0.41757988929748535, -0.6304994225502014, -0.23800121247768402, 0.07399255782365799, -0.6322021484375, -0.06103336066007614, -0.1668916642665863, -0.26209843158721924, 1.049057960510254, -0.5176329016685486, -0.8330436944961548, -0.07246556133031845, -0.5978716611862183, -0.6850828528404236, -0.3074699938297272, -0.6660676598548889, 1.1398351192474365, -0.02248169481754303, -0.14402860403060913, -0.2845458984375, -0.1523195207118988, 1.5641227960586548, -0.5566500425338745, 0.17447437345981598, -0.12770192325115204, -0.1187806949019432, -0.1492094099521637, 0.4972776472568512, -0.5349013209342957, 0.3379889130592346, -0.2027982771396637, -1.1040362119674683, 0.279071569442749, 0.8670008182525635, -0.6938377618789673, 0.020872199907898903, 0.5012063384056091, 0.5289198756217957, 1.182013988494873, -0.6481108069419861, -0.8718405365943909, -0.2714390456676483, 0.5260077118873596, -0.10260728001594543, -0.2247709333896637, -0.7836564183235168, 0.723884105682373, -0.9738069176673889, 0.4448888301849365, 0.016965080052614212, -0.47261855006217957, 0.07787906378507614, 0.13887472450733185, 0.028726017102599144, -0.19102926552295685, 1.4981043338775635, 0.027023091912269592, -0.29349473118782043, 0.5684347748756409, -0.33751723170280457, 0.20042867958545685, -0.45354148745536804, -0.6455338597297668, 0.026209214702248573, -1.084716796875, -1.4766486883163452, -0.115020751953125, 0.20012900233268738, -0.4247185289859772, 1.1589858531951904, 0.07784675061702728, 0.35313504934310913, 0.5586529970169067, -0.8228023648262024, 0.21139705181121826, -0.009427239187061787, -0.08356431126594543, 0.2864200472831726, -0.27041447162628174, -0.1451326310634613, 1.294907569885254, 0.7452607750892639, 0.9424115419387817, -0.4133695662021637, 0.26339811086654663, 0.20809847116470337, 0.5056942105293274, 0.16912841796875, 0.06615851819515228, -1.4943417310714722, -0.5676987767219543, 0.5775792598724365, 0.6174460053443909, -0.16822725534439087, -1.1214240789413452, -1.2886604070663452, -0.0894775390625, 1.3048741817474365, -0.9512580633163452, 0.8120719790458679, 0.39908847212791443, 0.07184197008609772, 0.32258516550064087, 0.361083984375, 0.10490328073501587, -1.0332893133163452, 0.5319698452949524, -0.7182329893112183, 1.1297177076339722, 1.365220069885254, 0.46627628803253174, 0.9240937829017639, 0.28807786107063293, -0.5287367701530457, 0.2689720690250397, 0.1203397884964943, 1.2164090871810913, -0.025400610640645027, 0.6838864684104919, 0.920769214630127, -0.44174015522003174, -0.1838199347257614, -0.34579646587371826, 0.8540196418762207, 0.9577187895774841, 0.5535493493080139, -0.0010752958478406072, -0.602698802947998, 0.07675530016422272, -0.579352855682373, -1.8307530879974365, -0.38629329204559326, 0.8602268099784851, 1.1927706003189087, 0.15273509919643402, -0.43110206723213196, -0.3162877559661865, -0.6625653505325317, 0.6921674013137817, -1.0786941051483154, 0.5551811456680298, -1.315443992614746, 1.1002700328826904, -0.305419921875, 0.9698199033737183, 0.3573785722255707, 0.11103372275829315, -1.1828738451004028, 0.3331904709339142, 0.036605104804039, 0.6522782444953918, 0.4780848026275635, 0.7038107514381409, 0.9277774691581726, -0.29590919613838196, -0.25541236996650696, -0.049581415951251984, 0.5995698571205139, 0.1371549665927887, 0.24582447111606598, -1.8439511060714722, 0.839361310005188, -0.7800443172454834, 0.2860143184661865, 1.1719467639923096, -0.3601433336734772, 0.4628394544124603, -0.37688490748405457, 0.05092351511120796, -0.5634909272193909, -0.09903133660554886, 0.48134735226631165, 0.572470486164093, 0.7026187777519226, -0.6623678803443909, 0.05602847784757614, -0.7752541899681091, -0.3255184292793274, 0.04062529280781746, 0.022478889673948288, 0.6900203824043274, 0.29078584909439087, 0.21045999228954315, 0.6441973447799683, -0.932013988494873, -0.6989494562149048, 0.5197823643684387, 0.463367223739624, -0.31874892115592957, -0.11122961342334747, -0.6271030306816101, -0.9173009395599365, 0.5412561893463135, 0.02493465691804886, 0.16248635947704315, 0.5325819849967957, 0.49755859375, -0.9509744048118591, -0.37222468852996826, 0.40613511204719543, 0.5143647789955139, 0.46048152446746826, -0.37419307231903076, -0.2196780890226364, 0.5290401577949524, 0.16025318205356598, 0.6941555142402649, 0.11514371633529663, -0.20547664165496826, -0.17520366609096527, 0.8166719079017639, 1.095168113708496, 0.45926621556282043, -1.4379308223724365, 0.03633151203393936, 0.3819634020328522, 0.2719977796077728, -0.013211418874561787, 0.0715516060590744, 0.12165428698062897, 0.5173842310905457, -0.08412259817123413, -0.2583308517932892, 0.6438203454017639, 0.3723539412021637, -1.787468433380127, -0.06332308053970337, -0.1721622198820114, -0.04232967644929886, 2.351045608520508, 1.470832347869873, -0.6153761744499207, -0.9814022183418274, 1.4694106578826904, 0.9262605309486389, 0.4001105725765228, 0.10435396432876587, 0.3081939220428467, 1.2119427919387817, -0.17786362767219543, 0.8566984534263611, -0.6598618626594543, 0.5982612371444702, 0.15204934775829315, 0.39061424136161804, -0.26761043071746826, -0.9905790686607361, 0.3047521114349365, 0.9050723910331726, -0.9915340542793274, -0.2713443636894226, -0.062295351177453995, 0.3056550920009613, 0.4822423458099365, -0.3305179476737976, -1.2070528268814087, 0.6288182735443115, -0.5711023807525635, 0.3063175082206726, -0.40903517603874207, 0.12024733424186707, -0.5917143225669861, 0.3595607876777649, -0.4033257067203522, -0.0726318359375, -0.1191190853714943, -1.161506175994873, -0.525922417640686, 0.19886913895606995, 0.9870390295982361, 0.42661017179489136, 0.13864673674106598, 0.4147913455963135, 1.2919921875, 0.6611005067825317, 0.684013843536377, 0.6931942105293274, 0.3511316776275635, 0.0941009521484375, -0.6612440943717957, -0.18198169767856598, -0.39639192819595337, 0.6268386840820312, 0.705970287322998, 1.2171630859375, 1.4697840213775635, -0.31011873483657837, -0.3485143184661865, 1.0201919078826904, -0.9946576356887817, 0.243072509765625, 0.10045399516820908, -2.5868566036224365, -0.8833402991294861, 0.38439223170280457, 0.029993394389748573, -0.21341121196746826, 0.40477439761161804, 0.8327924013137817, -0.7435410618782043, 0.06992519646883011, -0.099322110414505, -0.49852439761161804, 0.6544620394706726, -0.0736299380660057, -0.8919534087181091, -0.02285003662109375, 0.11716505885124207, -0.4560887813568115, 0.26844337582588196, 0.6268087029457092, -0.5685676336288452, 0.1290195733308792, 0.49845078587532043, 0.6715303063392639, -0.6555997133255005, -0.7988999485969543, -0.9807559847831726, 0.3117891252040863, -0.5158332586288452, -0.6349913477897644, 1.3196231126785278, 0.042525798082351685, 0.5947983860969543, 0.6949516534805298, -0.6709379553794861, 0.049962662160396576, 0.4524931013584137, -0.1559968888759613, -0.3617212772369385, 0.5277485847473145, 0.30994370579719543, -0.12873750925064087, -1.5332318544387817, 0.4567691683769226, -1.138930320739746, 0.2988855838775635, -0.4979678988456726, -0.17372243106365204, -0.7949178218841553, 0.14826516807079315, -0.1579374372959137, -0.665276050567627, 0.01124482974410057, 0.5410371422767639, -0.974311351776123, 1.353400707244873, -0.10623925924301147, -0.6868321895599365, -0.33528944849967957, -0.07623829692602158, 0.7587154507637024, -0.10315524786710739, 0.9725808501243591, -0.4218013882637024, -0.9128776788711548, 0.21729592978954315, -0.3671444058418274, 0.553596019744873, -0.28582045435905457, -0.23135197162628174, 0.20737053453922272, -1.056015968322754, -0.6822456121444702, 0.3931058943271637, -0.884270191192627, 0.43615004420280457, 0.22598221898078918, -0.5457860231399536, 0.44777005910873413, -0.5590533018112183, -0.8243049383163452, 0.3330762982368469, -0.4086860120296478, 0.5907790064811707, 0.0008980245911516249, -0.2885681688785553, 0.4068244397640228, -0.876258373260498, 0.2974638044834137, -0.041658248752355576, -0.35936063528060913, -0.004168342333287001, -0.4138399064540863, 0.5934556126594543, -0.15582454204559326, 1.1733111143112183, -0.1325468122959137, -0.09106804430484772, 0.49881991744041443, -0.16985096037387848, 0.6249542236328125, -0.14739271998405457, -1.0790656805038452, 0.12539610266685486, 0.14303767681121826, -0.8320814967155457, -0.38000646233558655, -0.13067805767059326, -0.4748319685459137, 0.9779645204544067, -0.5804811120033264, -0.13703469932079315, -0.2454618513584137, -0.890026330947876, -1.1706039905548096, 0.7452789545059204, 0.24080051481723785, 0.9298131465911865, -0.0759672299027443, -1.6186236143112183, 0.2353425920009613, 0.6452762484550476, 1.3373736143112183, -0.38345158100128174, -0.053731583058834076, -1.447265625, -0.6067325472831726, -1.9407743215560913, -0.25890395045280457, -0.13031005859375, 0.3851282596588135, 0.751823902130127, 0.8743250370025635, 0.3929012417793274, -0.09560798108577728, -0.8478090167045593, -0.07348363846540451, -0.4574836194515228, 0.09014174342155457, -0.11288025975227356, 0.21718911826610565, 0.7919059991836548, 0.01798870973289013, 1.5879336595535278, 1.6228457689285278, 1.032829761505127, -0.19070523977279663, -0.5787245631217957, 0.2593032717704773, -0.19692903757095337, -1.1891372203826904, 0.16077019274234772, -0.4047061800956726, 0.4650537967681885, -0.7291008234024048, -0.18866819143295288, 0.39476820826530457, -0.003168442752212286, -0.21464627981185913, -0.13131847977638245, 0.22279806435108185, -0.07772378623485565, -1.3631376028060913, 0.6535069942474365, -0.07475011795759201, 0.15801642835140228, 0.5747501254081726, -0.3630252182483673, 0.11834716796875, 0.6528050899505615, 0.8126364350318909, -0.8458772301673889, -0.3844960033893585, 0.2961511015892029, 0.9635312557220459, 0.6633515954017639, 0.8687412142753601, 0.19062446057796478, -1.5880630016326904, 0.02476411685347557, -0.09921085089445114, -0.4945337772369385, -0.34270521998405457, -0.9067526459693909, -0.39905861020088196, 0.044676389545202255, -0.5598138570785522, -0.30389404296875, 0.14427633583545685, 0.36431884765625, -0.684441089630127, -0.35126182436943054, 1.33352792263031, 0.11177040636539459, 0.8147762417793274, 0.3113959729671478, 1.3315716981887817, -1.3478788137435913, -0.008115880191326141, 0.03021823614835739, 0.2938102185726166, 0.09293454885482788, -0.09502096474170685, -0.968390941619873, 0.2035091668367386, 0.5782470703125, 1.2471277713775635, -0.22291027009487152, 1.010268211364746, 0.2590691149234772, -0.10700899362564087, -0.4475438594818115, -0.08645091205835342, 1.5578254461288452, 0.5747941136360168, -0.9544085264205933, 0.6954399347305298, 1.1147640943527222, -0.06349451094865799, 0.4158360958099365, -0.1801973283290863, 1.5514706373214722, -0.9427759647369385, 0.20494528114795685, -1.1407111883163452, -0.823239266872406, 0.6272331476211548, 0.8482378721237183, -0.843376636505127, -0.4940522611141205, 0.3873111605644226, -0.8661391139030457, -0.20436321198940277, -0.9894624352455139, 0.02488618716597557, -0.23851102590560913, 0.40865910053253174, -0.9458295106887817, -0.3861730098724365, -1.01416015625, 0.5086023807525635, -0.5224178433418274, -0.026546701788902283, -0.39862239360809326, -0.2759116590023041, 0.47333839535713196, 0.986335277557373, 0.31591796875, -0.07979000359773636, 0.5864832401275635, -1.0050551891326904, 1.5668658018112183, 0.580810546875, 0.8228400945663452, -0.5858207941055298, 0.7004861235618591, 0.9742539525032043, -0.48732084035873413, -0.6884550452232361, -0.6565982699394226, 0.3674051761627197], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'edge_uuids': ['371fae8e-19a1-407b-b75c-9ecedf5c0851'], 'group_ids': ['vllm-profiling__project_overview']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Max pending queries exceeded

        MATCH (n:Entity)-[e:RELATES_TO]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'search_vector': [1.1610478162765503, 0.9193987250328064, -2.1728515625, -0.6258021593093872, 0.4951956570148468, -1.3980422019958496, -1.3239513635635376, -0.28424182534217834, -0.8303378820419312, 0.5506156086921692, -0.30409759283065796, 0.2014712393283844, 1.565158486366272, -0.3703112006187439, -0.759488046169281, -0.9225115180015564, 1.1524200439453125, -0.6130131483078003, -0.6639811396598816, -0.5645403265953064, 0.4278942346572876, -0.6753917932510376, -0.2596828043460846, -0.06744275987148285, 1.1396324634552002, 0.6657700538635254, -0.4732171893119812, -0.142759770154953, -0.13129588961601257, 0.6807824969291687, 1.270263671875, -0.328677237033844, -0.2860456109046936, -0.9579932689666748, -0.1537599116563797, -0.7654760479927063, 0.7012619972229004, -0.1079610213637352, -0.5908362865447998, 0.9472060203552246, -0.7710949182510376, -0.917236328125, 0.20447757840156555, 0.1062069833278656, 0.21493348479270935, -0.0440179742872715, 0.0759698748588562, 0.131132572889328, -0.4180748462677002, 0.2367146760225296, 0.84222412109375, -0.191544309258461, 0.0536506287753582, -0.17301104962825775, 0.6104387640953064, -0.9672967791557312, -0.0423380546271801, -0.36271196603775024, 0.31506529450416565, -0.47529083490371704, 1.2483375072479248, 0.87750643491745, -0.8184102177619934, 1.394031286239624, 0.7511277198791504, -0.7478063702583313, -0.7670433521270752, -0.5338919758796692, -0.9133482575416565, 0.3119412362575531, 0.1271856427192688, 0.06921786069869995, -0.0834263414144516, -0.22191402316093445, -1.0900297164916992, -0.146773561835289, 0.7548014521598816, -1.6338587999343872, 0.5698769688606262, 0.5795687437057495, 1.1427088975906372, 1.2170497179031372, 0.788332998752594, -0.1037386953830719, 0.9705897569656372, -0.7422165870666504, -0.455354243516922, 0.5726434588432312, -1.0294712781906128, 1.0067516565322876, -0.1925746351480484, 0.0706583634018898, 0.7577892541885376, 0.5247337818145752, -1.2985025644302368, 0.787203848361969, -0.26718902587890625, -0.1421697735786438, -0.2195826917886734, -0.2634103000164032, -0.3567446768283844, -0.0454813651740551, 0.03277587890625, -0.1395060271024704, 0.15028926730155945, 0.7706007957458496, -0.00788007490336895, 0.0659760981798172, 0.4141409695148468, 0.5249953269958496, -0.3581484854221344, 0.0634424090385437, -0.8739943504333496, -0.081108458340168, -0.07818204164505005, -1.2497326135635376, 0.8391374945640564, -0.9845494031906128, 0.4429263174533844, 1.017645001411438, -0.2114497572183609, -1.560666799545288, 0.0753464475274086, 0.4409295916557312, -0.1295492947101593, 0.24504852294921875, -0.4047386646270752, -0.7823893427848816, 0.33635401725769043, -0.6540265679359436, 0.5135730504989624, -0.4307592511177063, -0.8111165165901184, -0.08448787033557892, 1.0693188905715942, 0.6946207880973816, -0.3952113687992096, -0.560247540473938, 0.42263394594192505, 0.3243226408958435, -0.23443730175495148, -0.14154052734375, -0.6127806305885315, -0.0505044125020504, 0.4895891547203064, 0.1395670622587204, 0.500616192817688, 0.03656768798828125, -0.1321294903755188, -0.2131514847278595, 0.0734892338514328, 0.4438418447971344, 0.4128635823726654, -0.1395903080701828, 0.04285140335559845, -1.4705636501312256, -1.1459496021270752, -0.17813782393932343, 0.2863275408744812, 0.3966843783855438, -0.4188319742679596, 0.1438554972410202, -0.0817616805434227, 0.5547717809677124, -0.8979870080947876, -0.8741862177848816, -0.1648951917886734, 1.1750662326812744, 0.6164434552192688, 0.318208247423172, 0.2876441478729248, -0.6312989592552185, -0.2390805184841156, -0.0681966170668602, 0.7315848469734192, -0.882693350315094, 0.8782173991203308, -0.3574073314666748, 1.0417015552520752, -0.061123620718717575, 0.8003045916557312, -0.6949114203453064, -0.0857253298163414, 0.23775790631771088, -0.4747401773929596, 0.04094042256474495, 0.0556894950568676, -0.450105220079422, -1.5280529260635376, -0.41926902532577515, 0.7744663953781128, 0.9601062536239624, -0.993475079536438, -0.9430977702140808, -1.3429594039916992, -1.0231257677078247, 0.4488154947757721, -0.1849292516708374, -0.1086542010307312, -1.1786295175552368, -0.3102765679359436, -0.12462091445922852, -2.063778877258301, 0.4412180483341217, -1.3833472728729248, 0.5195265412330627, -0.3393409252166748, 0.578188955783844, -0.561126708984375, 1.0640432834625244, 1.0573091506958008, -0.3037501871585846, 0.18421559035778046, 0.621829092502594, -0.0686674565076828, -0.7471575140953064, -0.5968947410583496, -0.257264643907547, -0.3770480751991272, -0.6461414098739624, -0.4495406448841095, 0.330015629529953, 0.07714187353849411, -0.0591437928378582, 1.2092052698135376, -0.5630289912223816, 0.02146402932703495, -0.0506577268242836, -0.515953779220581, 0.069939024746418, 0.32779622077941895, -1.2549525499343872, 0.4304613471031189, 0.08234487473964691, 0.4334571361541748, -0.0621817447245121, -0.31866219639778137, 0.9786900281906128, -0.363160640001297, 0.24885377287864685, -0.6821521520614624, 0.0672273188829422, -0.33006250858306885, 1.203497052192688, 0.08837927132844925, 0.1142563596367836, 0.16855911910533905, -0.7625841498374939, 0.9864614605903625, 0.9853515625, -1.0882539749145508, 0.1687629371881485, 0.5938909649848938, 0.14999116957187653, 0.8471505045890808, 0.0329560786485672, -1.1170915365219116, -0.018859680742025375, -0.0882146954536438, -0.7114524841308594, -0.7278468012809753, -0.2567371129989624, 0.4539882242679596, -0.3986060619354248, -0.1710306853055954, -0.4710330069065094, -0.0303635373711586, -0.5300467610359192, 0.566561758518219, -0.031684510409832, -0.572259783744812, 0.5031970739364624, 0.2579520046710968, 0.2270100861787796, 0.35318538546562195, -0.3732852041721344, -0.0119919553399086, -0.3772226870059967, -0.507440447807312, 0.2381526380777359, -0.6675792932510376, -1.8318220376968384, -0.0563514344394207, 0.3136233389377594, -1.0270124673843384, 0.1011962890625, 0.7483651041984558, 0.17002469301223755, -0.754092276096344, -0.4747081995010376, -0.651675283908844, -0.1069655641913414, -0.2372872531414032, -0.2123064249753952, -0.3531239926815033, 0.12045351415872574, 1.4920015335083008, 0.198243647813797, 0.7373315691947937, -0.5966913104057312, 0.772771954536438, 0.6139264702796936, 1.006642460823059, 0.50885009765625, 0.7609456181526184, -1.3235909938812256, -0.39306640625, -0.2077745646238327, 1.0010579824447632, 0.41779837012290955, -1.1297781467437744, -0.1844482421875, -0.9910365343093872, 1.2098592519760132, -1.0825958251953125, 1.6092935800552368, -0.1576429158449173, 0.2043282687664032, -0.2179812490940094, 0.8094831109046936, -0.4805704653263092, -1.0149332284927368, 0.04323432594537735, -0.7948070764541626, 0.3829389214515686, 0.5094749927520752, 0.06315649300813675, 0.084059938788414, 0.9056628942489624, -0.8274187445640564, 1.1399906873703003, 0.2322453111410141, 0.7291783094406128, 0.1030665785074234, 0.261202871799469, 0.749081552028656, 0.5753962397575378, 0.8522542119026184, 0.11132685095071793, 0.2576671838760376, 0.6557936668395996, 0.110786072909832, 0.30920374393463135, -0.8359491229057312, -0.16062627732753754, -0.4559406042098999, -1.3989309072494507, -0.0910920649766922, 1.2050447463989258, 0.6156122088432312, 0.4431072473526001, -0.6263660192489624, -1.0957961082458496, -0.738772451877594, 1.020251989364624, -0.0374610535800457, 0.861578106880188, -0.4395497739315033, 1.0425890684127808, -0.1460077166557312, 0.4590541422367096, -0.5980437397956848, 0.6081078052520752, -0.8015456199645996, 0.5719790458679199, 0.6322959065437317, 1.3274797201156616, 0.11021514236927032, 0.438961923122406, 0.37218040227890015, -0.7795195579528809, -0.3073381781578064, -0.1541631817817688, 1.109515905380249, -0.1149226576089859, 0.1528952419757843, -1.909893274307251, 0.1439005583524704, -1.2617347240447998, -0.0945390984416008, 0.5678483843803406, -0.6528549194335938, 0.42022705078125, 1.0758056640625, -0.21878468990325928, -0.7036946415901184, 0.4067477285861969, 0.5746314525604248, 0.4720306396484375, 1.3898576498031616, -1.0512346029281616, -0.4617542028427124, -0.5096595287322998, 0.0060831704176962376, -0.0562613345682621, -0.453887939453125, 0.36391085386276245, 0.19203431904315948, 0.2060416042804718, 0.660986065864563, -0.8808942437171936, -0.5173209309577942, 0.4382322430610657, -0.0228416807949543, -0.646246075630188, 0.4473193883895874, -0.3922736644744873, -1.1164376735687256, 0.7806309461593628, -0.06921504437923431, -0.370849609375, 0.6277901530265808, 0.2620522677898407, -0.4337274432182312, 0.06615084409713745, 0.7659745216369629, 0.3097570538520813, 0.057716004550457, -0.243666872382164, 0.33068475127220154, 0.9495936632156372, 0.17824918031692505, 0.00686327600851655, 0.30470821261405945, -0.9133998155593872, 0.3301769495010376, 0.5089808702468872, 0.8353318572044373, -0.1350649893283844, -1.2195754051208496, 0.2524581253528595, 0.199189692735672, 0.6905118227005005, -0.0406370609998703, 0.78265380859375, -0.668091893196106, 0.3002094030380249, 0.1221328005194664, -0.3017926812171936, 0.3796590268611908, 0.5095294713973999, -1.8829984664916992, 0.2389003187417984, -0.7083285450935364, -0.3318990170955658, 2.4501023292541504, 0.6774277687072754, -0.9564732313156128, -1.0595353841781616, 0.9123448133468628, 0.738095223903656, 0.06608308851718903, 0.14317186176776886, 0.3455272912979126, 1.7838541269302368, 0.1617082804441452, 1.548620343208313, -0.7302478551864624, 0.2240193635225296, 0.375882089138031, 0.567874014377594, -0.058967225253582, -1.3078962564468384, 0.4354422390460968, 0.3996792733669281, -0.973394513130188, -0.890130877494812, 0.24178314208984375, 0.759219229221344, 0.4364682137966156, -0.4996163547039032, -0.2684544026851654, 0.939569354057312, -0.5550275444984436, -0.267549067735672, -0.11109324544668198, 0.0424993596971035, -1.0479212999343872, 0.1388077437877655, -0.2847667932510376, -0.15072377026081085, 1.2557779550552368, -0.3587544858455658, -1.1155134439468384, -0.4860578179359436, 1.2705543041229248, -0.0705370232462883, -0.03681144118309021, -0.1608378142118454, 1.0673537254333496, 0.8494582176208496, 0.814081072807312, 0.24616532027721405, 0.6173328161239624, 0.0048675537109375, -1.104198694229126, 0.3545343279838562, 0.5037406086921692, 0.8155372142791748, 1.3116483688354492, 1.0898561477661133, 1.2817615270614624, -0.087608702480793, -0.3117552399635315, 0.5404183268547058, -0.7764573097229004, 0.5630137324333191, 0.972101092338562, -1.748302698135376, -1.1289818286895752, 0.7164844274520874, -0.0863778218626976, -0.3995426595211029, 0.3857458233833313, 0.2985498309135437, -0.562982439994812, 1.3229050636291504, 0.1725841760635376, -0.7699497938156128, 0.6950160264968872, -0.2672540545463562, -0.348330557346344, 0.0031680152751505375, 0.1007952019572258, -0.6021728515625, 0.22427332401275635, 1.1234508752822876, -0.2115238755941391, 0.2970639169216156, -0.1911163330078125, -0.3084338903427124, -0.742397129535675, -0.3051946759223938, -0.5292914509773254, -0.06917285919189453, 0.36962780356407166, -0.1114494651556015, 0.5796595811843872, 0.327237069606781, 0.9504539966583252, 0.8146246075630188, -0.6556047797203064, 0.3059041202068329, -0.09705998003482819, 0.3609466552734375, -0.7107805609703064, 0.2699120044708252, 0.5098876953125, 0.5699999928474426, -1.3991349935531616, 0.7235063910484314, -1.1196656227111816, 0.1940075159072876, -0.8182750940322876, 0.587222158908844, -0.3875659704208374, -0.345549076795578, -0.7616780400276184, -0.1778331995010376, 0.0384993776679039, 0.6938782930374146, -0.6743178367614746, 1.0000464916229248, -0.1292630136013031, 0.2648838460445404, -0.4428565502166748, -0.4512697756290436, -0.1198519766330719, -0.306033194065094, 1.1318591833114624, -0.33648115396499634, -0.9556128978729248, -0.5772937536239624, 0.0035008022096008062, 0.4261227548122406, 0.208815798163414, 0.5230189561843872, 0.9906238317489624, -1.0969709157943726, -0.32753172516822815, 0.6950392723083496, -1.2601027488708496, 0.611121416091919, -0.1412462443113327, 0.1559876948595047, 0.4702662527561188, -0.12670625746250153, -0.6354090571403503, 0.815216064453125, -0.0863843634724617, 0.41987237334251404, -0.363525390625, -0.0842764750123024, 0.3084891140460968, -0.1473977267742157, 0.4291178286075592, 0.291322261095047, -0.128662109375, -0.1247304305434227, -1.1199544668197632, 0.4928632378578186, 0.1041150763630867, 1.029796838760376, 0.06528327614068985, 0.27240389585494995, 0.412020742893219, -0.1342141330242157, -0.005604153499007225, -0.356294184923172, -0.2794102132320404, 0.4299432635307312, 0.5405738353729248, -0.3216988742351532, 0.1614648699760437, 0.3795885443687439, -0.5292561650276184, 1.295293927192688, -0.2487524151802063, -0.26297640800476074, -0.0628095343708992, 0.066269651055336, -0.9276820421218872, 0.5669453740119934, 0.1484411358833313, 0.0788254514336586, -0.32655152678489685, -1.3184291124343872, -0.05006592720746994, 0.5419562458992004, 0.9566417932510376, -0.39044779539108276, -0.518804669380188, -1.359014630317688, -0.0978182852268219, -1.2392491102218628, 0.5153815746307373, -0.0983123779296875, 0.293211430311203, 0.3055623471736908, 0.9010587334632874, 1.6298595666885376, -0.7255972027778625, -1.1594325304031372, -0.02393304742872715, 0.1081593856215477, -0.3215477466583252, 0.3184741735458374, 0.2236909419298172, 0.57012939453125, -0.0904083251953125, 1.7998511791229248, 1.3444417715072632, 0.37664830684661865, -0.3088030219078064, 0.02808489091694355, 0.5639561414718628, 0.012112571857869625, -1.0231351852416992, -0.5813533067703247, -1.0871872901916504, 0.015032087452709675, -0.556033194065094, -0.6667655110359192, -0.16223934292793274, 0.9224399328231812, 0.2079264372587204, -0.2180103063583374, 0.0724717527627945, -0.0495649054646492, -0.707675039768219, 0.2914908230304718, 1.025402307510376, -1.0028860569000244, 0.2018003910779953, 0.9802013635635376, 0.9123651385307312, 1.4554269313812256, 1.003406286239624, -0.5252860188484192, -0.2965749204158783, -0.23756226897239685, 0.6829833984375, 0.2938784658908844, 0.01068987138569355, -0.0497051402926445, -1.199651837348938, 0.1584276407957077, -0.5835425853729248, -0.4163469672203064, 0.40600457787513733, -1.029296875, -0.8253435492515564, -0.32864612340927124, -1.0255126953125, -0.0500880666077137, -0.08935546875, 0.1900227814912796, -0.787225604057312, -0.1819610595703125, 1.5231294631958008, -0.0406486876308918, -0.1234922856092453, 0.005359933711588383, 1.3587239980697632, -0.9547075629234314, 0.5064444541931152, 0.14989107847213745, 0.196504145860672, 0.3304363489151001, -0.243287593126297, -1.1164900064468384, 0.3465031087398529, 0.3920840322971344, -0.03931862860918045, -0.332826167345047, 0.703579843044281, -0.1563778817653656, -0.18429674208164215, -0.512844979763031, -0.5262654423713684, 1.220220685005188, 0.315458744764328, -1.0401611328125, 0.132081538438797, 0.4883735179901123, -0.12076400220394135, 0.6854844093322754, -1.0382051467895508, 1.2351888418197632, -1.3085066080093384, 0.2886148989200592, 0.1516105979681015, -0.8892444372177124, 0.6539684534072876, 0.0093674436211586, -0.3195706307888031, -0.7080716490745544, 0.14114034175872803, -1.003912091255188, 0.04498291015625, -0.7504185438156128, -0.02437262237071991, -0.6586390733718872, 0.2890123724937439, -0.1127660870552063, 0.1221284419298172, -0.3701535165309906, 0.7753034234046936, 0.716913104057312, -0.7610996961593628, 0.552978515625, 0.12823741137981415, -0.6422249674797058, 0.8592877984046936, -0.4754987359046936, -0.7608235478401184, 0.7533831000328064, 0.7427222728729248, 1.6058349609375, 0.443267822265625, 0.350588858127594, -0.4896298348903656, 0.983029305934906, 0.3394528329372406, -0.5070083141326904, -1.1196753978729248, -0.9853980541229248, 0.1380411833524704], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'edge_uuids': ['0b203e00-ae17-4973-9001-c6e766a5703f'], 'group_ids': ['vllm-profiling__project_overview']}
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'content' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'name' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'name' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'name' is already indexed
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:graphiti_core.graphiti:Completed add_episode in 35876.83629989624 ms
INFO:guardkit.knowledge.seed_role_constraints:Seeded role constraint: role_constraint_player_feature-build
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:graphiti_core.graphiti:Completed add_episode in 20904.239892959595 ms
INFO:guardkit.knowledge.seed_role_constraints:Seeded role constraint: role_constraint_coach_feature-build
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'uuid' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'content' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'name' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'name' is already indexed
INFO:graphiti_core.driver.falkordb_driver:Index already exists: Attribute 'name' is already indexed
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:graphiti_core.graphiti:Completed add_episode in 59268.746852874756 ms
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:graphiti_core.graphiti:Completed add_episode in 65408.926010131836 ms
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8000/v1/chat/completions "HTTP/1.1 200 OK"
INFO:httpx:HTTP Request: POST http://promaxgb10-41b1:8001/v1/embeddings "HTTP/1.1 200 OK"
INFO:graphiti_core.graphiti:Completed add_episode in 33964.67208862305 ms
  Project knowledge seeded successfully
    OK project_overview: Seeded from CLAUDE.md
    OK role_constraints: Seeded Player and Coach constraints
    OK implementation_modes: Seeded 3 modes

Step 2.5: Syncing template content to Graphiti...
INFO:guardkit.knowledge.graphiti_client:Graphiti factory: async loop running in thread, created client but deferred connection
  Warning: Template sync returned incomplete results

GuardKit initialized successfully!

Next steps:
  1. Create a task: /task-create "Your first task"
  2. Work on it: /task-work TASK-XXX
  3. Complete it: /task-complete TASK-XXX
richardwoollcott@Richards-MBP vllm-profiling %