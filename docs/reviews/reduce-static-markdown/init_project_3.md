richardwoollcott@Richards-MBP vllm-profiling % guardkit init fastapi-python -n vllm-profiling --copy-graphiti-from ~/Projects/appmilla_github/guardkit
Initializing GuardKit in /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling
  Project: vllm-profiling
  Template: fastapi-python

Step 1: Applying template...
INFO:guardkit.cli.init:Copied agent fastapi-database-specialist.md → /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/agents/fastapi-database-specialist.md
INFO:guardkit.cli.init:Copied agent fastapi-specialist.md → /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/agents/fastapi-specialist.md
INFO:guardkit.cli.init:Copied agent fastapi-testing-specialist.md → /Users/richardwoollcott/Projects/appmilla_github/vllm-profiling/.claude/agents/fastapi-testing-specialist.md
INFO:guardkit.cli.init:Copied 3 agent(s): fastapi-database-specialist.md, fastapi-specialist.md, fastapi-testing-specialist.md
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
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
  Seeding episode 1/8...WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [3] (valid range: 0-0 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 74636.06119155884 ms
 done (74.6s)
  Seeding episode 2/8...INFO:graphiti_core.graphiti:Completed add_episode in 69261.68298721313 ms
 done (69.3s)
  Seeding episode 3/8...INFO:graphiti_core.graphiti:Completed add_episode in 17816.652059555054 ms
 done (17.8s)
  Seeding episode 4/8...WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [7] (valid range: 0-1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 73394.22798156738 ms
 done (73.4s)
INFO:guardkit.knowledge.seed_role_constraints:Seeded role constraint: role_constraint_player_feature-build
  Seeding episode 5/8...INFO:graphiti_core.graphiti:Completed add_episode in 11903.3842086792 ms
 done (11.9s)
INFO:guardkit.knowledge.seed_role_constraints:Seeded role constraint: role_constraint_coach_feature-build
  Seeding episode 6/8...INFO:graphiti_core.graphiti:Completed add_episode in 51525.90012550354 ms
 done (51.5s)
  Seeding episode 7/8...WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [7] (valid range: 0-0 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 54415.523052215576 ms
 done (54.4s)
  Seeding episode 8/8...WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 48074.18894767761 ms
 done (48.1s)
  Project knowledge seeded successfully (401.0s total)
    OK project_overview: Seeded from CLAUDE.md
    OK role_constraints: Seeded Player and Coach constraints
    OK implementation_modes: Seeded 3 modes

Step 2.5: Syncing template content to Graphiti...
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index -1 out of bounds for chunk of size 15 in edge IS_USED_IN
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index -1 out of bounds for chunk of size 15 in edge IS_USED_IN
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index -1 out of bounds for chunk of size 15 in edge IS_USED_IN
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index -1 out of bounds for chunk of size 15 in edge IS_USED_IN
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index -1 out of bounds for chunk of size 15 in edge IS_USED_IN
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index -1 out of bounds for chunk of size 15 in edge IS_USED_IN
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index -1 out of bounds for chunk of size 15 in edge IS_USED_IN
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index -1 out of bounds for chunk of size 15 in edge IS_USED_IN
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index -1 out of bounds for chunk of size 15 in edge IS_USED_IN
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index -1 out of bounds for chunk of size 15 in edge IS_USED_IN
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index -1 out of bounds for chunk of size 15 in edge IS_USED_IN
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index -1 out of bounds for chunk of size 15 in edge IS_USED_IN
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index -1 out of bounds for chunk of size 15 in edge IS_USED_IN
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index -1 out of bounds for chunk of size 15 in edge IS_SOURCE_OF
WARNING:graphiti_core.utils.maintenance.edge_operations:Source index -1 out of bounds for chunk of size 15 in edge IS_ASSIGNED_TO_PROJECT
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1, 2] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1, 2] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1, 3] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1, 2, 0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 1, 3, 8, 9] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 96191.20407104492 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced template 'fastapi-python'
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 140998.09217453003 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced agent 'fastapi-database-specialist'
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 153431.44488334656 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced agent 'fastapi-specialist'
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0-1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 141925.47583580017 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced agent 'fastapi-testing-specialist'
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Python | Code | Style | Naming | Conventions | rule | specifies | Pydantic | schemas | use | PascalCase | type | suffix)', 'limit': 20, 'routing_': 'r', 'edge_uuids': ['f5230e01-9259-43a3-9e39-839497d3f1a1'], 'group_ids': ['rules']}
WARNING:guardkit.knowledge.graphiti_client:Transient FalkorDB error (attempt 1/3), retrying in 2s: Query timed out
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Python | Code | Style | Naming | Conventions | rule | specifies | Service | classes | use | PascalCase | Service | suffix)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Python | Code | Style | Naming | Conventions | rule | specifies | Functions | use | snake_case)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Python | Code | Style | Naming | Conventions | includes | rule | SQLAlchemy | models | use | PascalCase | singular | naming)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Standard | file | names | per | feature | part | Python | Code | Style | Naming | Conventions | rule | set)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
WARNING:guardkit.knowledge.graphiti_client:Transient FalkorDB error (attempt 2/3), retrying in 4s: Query timed out
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (API | Versioning | section | included | Python | Code | Style | Naming | Conventions | rule)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Python | Code | Style | Naming | Conventions | rule | specifies | SQLAlchemy | models | use | PascalCase | singular | naming | exemplified | Product | model)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Python | Code | Style | Naming | Conventions | rule | specifies | Pydantic | schemas | use | PascalCase | type | suffix | exemplified | UserPublic | schema)', 'limit': 20, 'routing_': 'r', 'edge_uuids': ['7ec8ff4a-1635-48b0-b97a-92967ede9eab'], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Python | Code | Style | Naming | Conventions | rule | specifies | service | classes | use | PascalCase | Service | suffix | exemplified | EmailService | class)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (code | style | rule | specifies | standard | file | names | per | feature | use | snake_case | config | py | one | file)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
WARNING:guardkit.knowledge.graphiti_client:Episode creation failed: Query timed out
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'code-style'
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Package | names | e | g | src | users | src | products | follow | snake_case | convention | per | Python | code | style | rules)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1, 5, 7] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 140460.15286445618 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'testing'
INFO:openai._base_client:Retrying request to /chat/completions in 0.409454 seconds
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [9] (valid range: 0-0 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 866877.9759407043 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'migrations'
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
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

{'query': ' (FastAPI | endpoints | use | UserCreate | schema | create | users | via | CRUD | methods)', 'limit': 20, 'routing_': 'r', 'group_ids': ['rules']}
WARNING:guardkit.knowledge.graphiti_client:Transient FalkorDB error (attempt 1/3), retrying in 2s: Query timed out
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
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

{'query': ' (CRUDUser | inherits | from | Base | CRUD | Class | using | specific | User | types)', 'limit': 20, 'routing_': 'r', 'group_ids': ['rules']}
WARNING:guardkit.knowledge.graphiti_client:Transient FalkorDB error (attempt 2/3), retrying in 4s: Query timed out
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
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

{'query': ' (CRUDBase | uses | AsyncSession | database | operations)', 'limit': 20, 'routing_': 'r', 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
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

{'query': ' (Best | Practices | includes | using | generic | base | class | CRUDBase | common | CRUD | operations)', 'limit': 20, 'routing_': 'r', 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (CRUD | Best | Practices | section | appears | rules | path_patterns | including | crud | py | repository | py)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
WARNING:guardkit.knowledge.graphiti_client:Episode creation failed: Query timed out
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'crud'
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Creating | New | CRUD | section | appears | rules | path_patterns | including | crud | py | repository | py)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Base | CRUD | Class | section | appears | rules | path_patterns | including | crud | py | repository | py)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (fastapi | python_crud | rule | created | template_sync)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
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

{'query': ' (Alembic | used | apply | migrations | using | alembic | upgrade | head | command)', 'limit': 20, 'routing_': 'r', 'group_ids': ['rules']}
WARNING:guardkit.knowledge.graphiti_client:Transient FalkorDB error (attempt 1/3), retrying in 2s: Query timed out
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
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

{'query': ' (alembic | revision | autogenerate | used | after | defining | new | model | generate | migration | files)', 'limit': 20, 'routing_': 'r', 'group_ids': ['rules']}
INFO:graphiti_core.graphiti:Completed add_episode in 205632.25293159485 ms
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'models'
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Pydantic | Field | Constraint | Patterns | includes | User | Input | Schemas | recommended | use | case | strict | constraints)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
WARNING:guardkit.knowledge.graphiti_client:Transient FalkorDB error (attempt 1/3), retrying in 2s: Query timed out
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Configuration | Values | example | uses | ge | le | constraints | application | settings | like | max_connections | constrain | valid | ranges)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Constraint | Decision | Matrix | includes | max_length | example | constraint | should | used | string | fields | names)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (FastAPI | uses | BaseModel | from | Pydantic | defining | constraints | schemas)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
WARNING:guardkit.knowledge.graphiti_client:Transient FalkorDB error (attempt 2/3), retrying in 4s: Query timed out
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Settings | User | input | use | strict | constraints | configuration | values)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Pydantic | Field | Constraint | Patterns | recommends | using | strict | constraints | database | ID | references | which | includes | product_id)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (retry_attempts | used | example | configuration | values | where | constraints | ge | 0 | le | 10 | appropriate | Pydantic | Field | Constraint | Patterns)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (When | Constraints | Appropriate | includes | UserCreate | which | uses | strict | Field | constraints | user | provided | input | like | name | price | quantity | sku)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Settings | uses | strict | constraints | FastAPI | configuration | values)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Pydantic | Field | Constraint | Patterns | includes | Constraint | Decision | Matrix | reference | table | deciding | when | use | strict | constraints)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Configuration | Values | should | use | strict | constraints | fields | like | quantities | retry_attempts | timeout_seconds)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Prices | use | strict | constraints | ge | 0 | because | business | rules)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
WARNING:guardkit.knowledge.graphiti_client:Episode creation failed: Query timed out
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'pydantic-constraints'
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Quantities | use | strict | constraints | ge | 0 | because | business | rules)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Common | Anti | Patterns | include | over | constraining | health | checks | use | SQLAlchemy | pool | metrics)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (AppSettings | example | configuration | schema | using | strict | constraints | values | like | timeout_seconds | retry_attempts)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Testing | Specialist | Agent | integrates | schemas | rules | validate | test | responses)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
WARNING:guardkit.knowledge.graphiti_client:Transient FalkorDB error (attempt 1/3), retrying in 2s: Query timed out
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Testing | Specialist | Agent | used | test | fixtures | defined | conftest | py)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
WARNING:guardkit.knowledge.graphiti_client:Transient FalkorDB error (attempt 2/3), retrying in 4s: Query timed out
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Testing | Specialist | Agent | integrates | database | CRUD | rules | test | database | operations)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
WARNING:guardkit.knowledge.graphiti_client:Episode creation failed: Query timed out
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'testing'
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Testing | Specialist | Agent | integrates | API | routing | rules | test | endpoints)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Testing | Specialist | Agent | references | uses | patterns | defined | claude | rules | testing | md)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (FastAPI | Specialist | Agent | integrates | rules | defined | api | schemas | md | Pydantic | schema | patterns)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
WARNING:guardkit.knowledge.graphiti_client:Transient FalkorDB error (attempt 1/3), retrying in 2s: Query timed out
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (FastAPI | Specialist | Agent | integrates | rules | defined | api | dependencies | md | dependency | injection | patterns)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (FastAPI | Specialist | Agent | integrates | rules | defined | database | crud | md | database | operations)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (FastAPI | Specialist | Agent | references | claude | rules | api | schemas | md)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
WARNING:guardkit.knowledge.graphiti_client:Transient FalkorDB error (attempt 2/3), retrying in 4s: Query timed out
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (FastAPI | Specialist | Agent | references | claude | rules | api | routing | md)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (FastAPI | Specialist | Agent | references | claude | rules | api | dependencies | md)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Query timed out
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (API | Endpoint | includes | proper | Route | Definition | using | FastAPI’s | routing | patterns)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
WARNING:guardkit.knowledge.graphiti_client:Episode creation failed: Query timed out
WARNING:guardkit.knowledge.graphiti_client:Graphiti disabled after 3 consecutive failures -- continuing without knowledge graph context
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'fastapi'
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'database'
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'routing'
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'schemas'
INFO:guardkit.knowledge.template_sync:[Graphiti] Synced rule 'dependencies'
INFO:guardkit.knowledge.template_sync:[Graphiti] Template sync complete: 1 template, 3 agents, 12 rules synced (6759.4s)
  Template content synced to Graphiti
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Sync | I | O | must | never | used | async | routes | FastAPI)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.

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

{'search_vector': [0.21964234113693237, 0.8390368819236755, -3.225234270095825, -1.4380176067352295, 0.050951842218637466, -0.2587529122829437, 1.1327309608459473, -0.17266845703125, -0.7286352515220642, -0.6827123761177063, 0.7783154249191284, 0.32613280415534973, 1.312441349029541, 0.7528016567230225, -1.1597851514816284, -0.020520323887467384, -0.06721802055835724, 0.15752097964286804, -1.0755175352096558, -0.00673675537109375, -0.9941112995147705, -0.14750976860523224, 0.4958520531654358, -0.0035632324870675802, 0.34717345237731934, 0.43570372462272644, 0.8364062309265137, -1.4286718368530273, -0.28392577171325684, -0.4295678734779358, 0.25555816292762756, 0.6675097942352295, -0.058024290949106216, -0.8036425709724426, -0.6837084889411926, -0.24956023693084717, 1.3125195503234863, 0.3181433081626892, -0.1522464007139206, 0.6386547684669495, 0.4432513415813446, 0.7594616413116455, -0.7563751339912415, -1.1282238960266113, -0.5352829098701477, -0.018926849588751793, 0.6338446140289307, -0.47110655903816223, 0.15854796767234802, -1.2144079208374023, 1.4479882717132568, -0.05349411070346832, -0.1445581018924713, -0.6786910891532898, 1.2662206888198853, 0.5038354396820068, 2.0576171875, 0.023438720032572746, 0.9520410299301147, -0.9720605611801147, 0.9829687476158142, 0.9270898699760437, -0.5954492092132568, 2.0770702362060547, 0.016032714396715164, -0.4541271924972534, -0.876904308795929, 0.16199828684329987, -0.7657412886619568, 0.5844042897224426, -0.11101211607456207, 0.0022189330775290728, 0.5054858326911926, 1.209173560142517, 0.21024474501609802, -0.08583170175552368, 0.2587932348251343, -0.879711925983429, 0.16831298172473907, 0.7442065477371216, -0.26858824491500854, -0.09502258151769638, 0.9206295609474182, 0.602783203125, 1.0327246189117432, 0.5178821086883545, -0.0924530029296875, -0.06524559110403061, -0.5354896187782288, 0.9715991020202637, -0.26947999000549316, -0.11668212711811066, 0.41590332984924316, 0.35947754979133606, -1.4824414253234863, 0.7316625714302063, -0.2232431024312973, 0.4715815782546997, -0.2454107701778412, 0.3643237352371216, -0.39172255992889404, -0.2771490514278412, -0.4414331018924713, -0.24436798691749573, -0.24719971418380737, -0.35798826813697815, 0.35541993379592896, 0.11697997897863388, 0.13241729140281677, -0.8794409036636353, -0.2911364734172821, 0.8542121648788452, -0.9503027200698853, 0.1425463855266571, -0.20087645947933197, -1.3252344131469727, 0.9134899973869324, -0.24940551817417145, 0.10217712074518204, -0.3243606686592102, -0.4230932593345642, -0.39253175258636475, 0.7128124833106995, 0.512251615524292, 0.04880737140774727, 1.1214648485183716, -1.531894564628601, -0.49476319551467896, 0.3531247079372406, -1.4147411584854126, 0.9497290253639221, -0.4670117199420929, -1.3466967344284058, 0.7531836032867432, 0.8147740364074707, 0.5264904499053955, -0.1429373174905777, -0.7345995903015137, 0.7279883027076721, 0.39720213413238525, 0.03593628108501434, 0.3327203392982483, -0.04405269771814346, -0.8495947122573853, -0.17046326398849487, -0.6076953411102295, 0.6564294695854187, -0.06840270757675171, -0.5056906342506409, -0.0021746826823800802, -0.6252100467681885, 0.9870898723602295, 0.389892578125, 0.34677672386169434, 0.542647123336792, -0.3855969309806824, -0.2551293969154358, 0.0028894043061882257, 0.4023205637931824, -0.01760433241724968, 1.3584131002426147, 0.4558666944503784, -0.17384155094623566, -0.08223968744277954, -0.0012152099516242743, -0.6484411358833313, 0.027358397841453552, 1.4244824647903442, -0.3271292746067047, 0.7846606373786926, -0.5040746927261353, -0.43577879667282104, -1.0466967821121216, -0.6707763671875, 0.7243518233299255, 1.4960546493530273, 1.5255322456359863, -0.27875107526779175, 1.0718060731887817, -0.6712304949760437, 0.41697150468826294, -1.140566349029541, 0.48154664039611816, 0.2415759265422821, -0.6302087306976318, 0.34724608063697815, -0.6237228512763977, -0.6789087057113647, -1.7622851133346558, -0.6143652200698853, 0.9387280344963074, 0.949999988079071, -0.7764953374862671, -0.02504470758140087, -1.5820703506469727, -1.0371484756469727, 0.08506637811660767, 0.2610095143318176, 0.3848620653152466, -1.0364062786102295, -0.7065991163253784, -0.18143188953399658, -1.1694238185882568, 0.66558837890625, -0.8784570097923279, 0.9925644397735596, -0.4809585511684418, 0.7206616401672363, -0.2585003674030304, -0.2982977330684662, 1.3820312023162842, 0.19618865847587585, 0.03264098986983299, 0.9670605659484863, -0.5801830887794495, -1.1771289110183716, -0.5724615454673767, -0.2876361012458801, -0.4346383810043335, 0.2722119092941284, 0.0679486095905304, 0.36770570278167725, 0.2943951487541199, -0.1634393334388733, 0.5234750509262085, 0.2469077855348587, -0.5887671113014221, 0.12282106280326843, -0.28515616059303284, 0.23054169118404388, 0.5879626274108887, -1.4984570741653442, 0.5639599561691284, -0.5270373821258545, 0.5017906427383423, -0.11714111268520355, 0.8393261432647705, 0.6500219702720642, 0.13797058165073395, -0.6855084300041199, -0.44689881801605225, 0.7699756026268005, -0.13911743462085724, 0.42032578587532043, -0.5130566358566284, -0.72149658203125, -0.8277148604393005, -1.004421353340149, -0.19549621641635895, 1.406191349029541, -0.07693702727556229, -0.2937634289264679, -0.015582275576889515, -0.09871459752321243, 0.4849792420864105, -0.8180245161056519, -0.3082042336463928, -0.8302331566810608, -0.1773083508014679, -0.08790405094623566, 0.3167163133621216, -0.1625683605670929, 0.12157364189624786, -0.453665167093277, 0.3928149342536926, -1.5525391101837158, -0.1801593005657196, 0.5563931465148926, 0.7405163645744324, -0.31747740507125854, -0.2775634825229645, 0.4584301710128784, 0.17874878644943237, 0.40852537751197815, -0.230865940451622, 0.8099328875541687, 0.10771667212247849, -1.1175097227096558, -0.20639710128307343, 1.371914029121399, -0.45314452052116394, -1.218808650970459, -0.39533448219299316, 0.07541137933731079, 0.250762939453125, -0.14351749420166016, -0.07335571199655533, -0.005363769363611937, 0.09528762847185135, 0.3386791944503784, 0.5835888385772705, -0.19833709299564362, -0.8382696509361267, 0.7526623606681824, 0.4759942591190338, -0.9022265672683716, 0.6280438303947449, -0.07251953333616257, 0.7430639863014221, 0.4155292510986328, 0.48939454555511475, 0.732798159122467, 1.1480615139007568, 0.9660693407058716, 0.4003736972808838, -0.6180102825164795, -1.091202974319458, -0.519181489944458, 1.1732275485992432, 0.7656054496765137, -0.9664648175239563, -0.552219569683075, -0.679186224937439, 0.7559906244277954, 0.3058883547782898, 0.6108459234237671, 0.5175585746765137, 0.14170409739017487, -0.017763977870345116, 0.25793638825416565, 0.6224706768989563, 0.22999267280101776, -1.0312793254852295, -0.08588775992393494, 0.1445288062095642, 1.8583056926727295, -0.5830261707305908, 0.4575488269329071, 0.0026345825754106045, -0.34194090962409973, 0.9313318133354187, 0.22003173828125, 1.5447949171066284, -0.25123536586761475, -0.8499487042427063, 1.1035254001617432, 0.33294877409935, 0.07310973852872849, -1.5019726753234863, 0.2605236768722534, 1.5446288585662842, -1.0424220561981201, 0.9394241571426392, -1.7913280725479126, -0.3019372522830963, -0.15809936821460724, -0.8940478563308716, -1.195644497871399, 0.3638867139816284, 0.776157557964325, -0.11505371332168579, 0.0660482794046402, -0.019888611510396004, 0.1138928234577179, 0.2792736887931824, 0.25011229515075684, 0.09171726554632187, 0.2894934117794037, 0.07174015045166016, 0.03811096027493477, 0.015919798985123634, 0.31535398960113525, -0.6848046779632568, -0.812243640422821, 0.49390748143196106, 0.7624316215515137, 0.14219848811626434, -0.06125549226999283, 0.24891403317451477, -0.1493658423423767, -0.19010010361671448, 0.039653319865465164, 0.1581140160560608, 0.4731518626213074, 0.4932922422885895, 0.33049988746643066, -0.27522581815719604, -0.40078461170196533, -0.2164269983768463, 0.7786914110183716, 0.760333240032196, -0.047303467988967896, -0.45235198736190796, 0.09323974698781967, 0.4171508848667145, 0.7322686910629272, 0.6260610818862915, 0.7496728301048279, -0.3735327124595642, 1.1784228086471558, -0.09920410066843033, -0.5912231206893921, -0.875683605670929, -0.13154937326908112, 0.6026626825332642, -0.12326141446828842, -0.11291717737913132, 0.6034662127494812, 1.1297998428344727, 1.5385351181030273, -0.027236327528953552, -1.6139062643051147, -0.02100830152630806, -0.6400341987609863, -0.4643595814704895, -0.16121764481067657, -1.4071776866912842, -0.47662353515625, 0.8984176516532898, 0.07344238460063934, 0.4674414098262787, 0.1438269019126892, -0.61602783203125, -0.3061767518520355, 1.1335937976837158, -0.4081762731075287, 0.7060278058052063, 0.494627982378006, -0.4107043445110321, 0.2348822057247162, 0.3201965391635895, 1.0769970417022705, -0.45788055658340454, 0.06743407994508743, -0.5082617402076721, 0.12787476181983948, 0.7169213891029358, -0.33064696192741394, -0.3174709379673004, -1.7241259813308716, 0.6838122606277466, 1.0776832103729248, 0.5291802883148193, -0.669219970703125, -0.1935722380876541, -0.8651745319366455, -0.630200207233429, 0.6677466034889221, -0.2396228015422821, 0.9238354563713074, 0.2949902415275574, -0.787341296672821, -0.2971220314502716, -0.8480371236801147, 0.17306335270404816, 1.5997852087020874, 0.8077057003974915, -1.3151366710662842, -1.6238476037979126, 0.5237280130386353, -0.5206775069236755, 1.041015625, 0.7535644769668579, 0.6886767745018005, 1.5804883241653442, -0.4463842809200287, -0.09064728021621704, -0.007836303673684597, -0.18412719666957855, 0.41738036274909973, -0.115631103515625, -0.5575646758079529, -1.357763648033142, 0.056257933378219604, 0.5705517530441284, 0.5054803490638733, -0.7097241282463074, 0.6193673610687256, 0.9999706745147705, 0.9026952981948853, -0.29393064975738525, 0.2759423851966858, 0.4432675242424011, -0.2426464855670929, -0.35130858421325684, 0.22184662520885468, -0.051839448511600494, 0.7866314649581909, -0.29588377475738525, 1.2238452434539795, -0.7249017357826233, 0.06682250648736954, 0.17929992079734802, -0.3570345342159271, -0.2048974633216858, 0.667742908000946, 0.4817822277545929, -0.29156553745269775, 0.8496679663658142, -0.018342284485697746, 0.17633667588233948, -0.10882812738418579, 0.8465039134025574, -0.35475340485572815, -0.005314941518008709, -0.5023974776268005, 0.523207426071167, 0.061259154230356216, -0.31541016697883606, 0.7061834931373596, -0.42457276582717896, 1.106967806816101, -0.21865808963775635, -0.593336820602417, 0.5053735375404358, -0.21860961616039276, 0.3334912061691284, -1.057275414466858, -0.5486352443695068, 0.2469213902950287, 0.6943274140357971, 1.108701229095459, -0.2850292921066284, 0.27701446413993835, 0.851240873336792, -0.9537219405174255, 0.5742248296737671, -0.7852441668510437, -1.1265380382537842, -0.4077911376953125, 0.33702605962753296, 0.5832592844963074, -0.32334718108177185, -0.7060302495956421, -0.7674536108970642, 0.3772122263908386, 1.328212857246399, -0.9538183808326721, -0.15587829053401947, 0.8744226098060608, 0.030861053615808487, 0.7018115520477295, -1.006679654121399, 0.10817108303308487, 0.01385498046875, -1.5625, -0.8934765458106995, 1.1529687643051147, 0.34175291657447815, -0.22270141541957855, 0.4657890200614929, -0.7629528641700745, -0.06520141661167145, -0.1907464563846588, -0.6956518292427063, -0.18359924852848053, 0.057869262993335724, 0.44584542512893677, -0.27325379848480225, -1.7017358541488647, 0.5853124856948853, 0.5564514398574829, 0.0011975098168477416, -1.0214990377426147, -0.37908753752708435, -0.30305421352386475, -0.5680615305900574, -0.7120556831359863, -0.3361779749393463, -1.3696850538253784, -0.5166662335395813, 0.08897720277309418, 1.3455029726028442, 0.7533886432647705, 0.30056822299957275, -0.2250213623046875, -0.6228570342063904, 0.21583496034145355, 0.12391479313373566, 1.3291516304016113, 0.9310547113418579, -1.2872754335403442, 0.024208756163716316, 0.4571765065193176, 0.21849609911441803, -0.33199891448020935, 0.25842103362083435, -0.13609741628170013, -0.6623409986495972, -0.391134649515152, -0.33524107933044434, -0.6338952779769897, 0.9347417950630188, 0.883329451084137, 0.30840086936950684, -0.32267579436302185, -0.7108911275863647, 0.9097851514816284, 0.3652166724205017, -0.23366455733776093, 0.32942748069763184, -0.01583007723093033, 0.29908812046051025, -0.005339355673640966, -0.07955200225114822, 0.40628722310066223, -0.4713571071624756, 0.6765918135643005, -0.47980713844299316, -0.7213989496231079, 0.6042516827583313, -0.5887695550918579, 0.8660690188407898, -0.6442883014678955, -0.6692187786102295, 2.2774219512939453, 0.09183288365602493, 1.4376367330551147, -0.3952600061893463, 0.07978851348161697, 0.46384337544441223, -0.07857269048690796, 0.0933239758014679, -0.29945313930511475, 0.3090045154094696, -1.507714867591858, 0.22285155951976776, 0.07449951022863388, 0.38936904072761536, -1.1345752477645874, -1.171044945716858, -0.5278418064117432, 0.9861700534820557, -0.061903685331344604, -0.585375964641571, -0.15367431938648224, -0.7843513488769531, -0.5718103051185608, 0.5715362429618835, 1.110327124595642, -0.8057971000671387, 0.2896479666233063, -1.7716991901397705, -0.24742615222930908, -1.0832812786102295, 0.05444785952568054, -0.19999168813228607, 0.7320556640625, -0.40711426734924316, 0.19769920408725739, 0.4323400855064392, 0.41202330589294434, -0.18511474132537842, -0.47350364923477173, 0.5030359029769897, -0.7017324566841125, 1.3448235988616943, 0.15320739150047302, 1.1983104944229126, -0.4713708460330963, 2.0506250858306885, 0.4264208972454071, 0.17543242871761322, -0.6933691501617432, -0.7981152534484863, -0.4881835877895355, -0.087621308863163, -0.1506640613079071, -1.0213159322738647, -1.361142635345459, -0.35683900117874146, 0.41128799319267273, -0.39813232421875, -0.014927978627383709, 0.6172174215316772, 0.25259068608283997, 0.8506396412849426, 0.39167115092277527, -1.2509912252426147, 0.1319047510623932, 0.10194854438304901, 0.0645129382610321, -0.06315414607524872, -0.4745773375034332, 0.729522705078125, -0.5294628739356995, 1.7507812976837158, -0.4494006335735321, 0.794628918170929, -0.6795300245285034, 1.0958203077316284, -0.6968048214912415, 0.5905486941337585, 0.19244995713233948, -0.3370477259159088, -0.5328295826911926, 0.1090545654296875, -0.6528955101966858, 0.4061560034751892, -0.7838451862335205, -0.0050854492001235485, -0.3114941418170929, -0.4537036120891571, -0.8691650629043579, 0.5966455340385437, 0.3948529064655304, 0.04660949856042862, 0.0009478759602643549, -0.5767480731010437, 0.533416748046875, -0.3096081614494324, 0.3015063405036926, 0.4947381615638733, 0.10265380889177322, -0.08683715760707855, -0.48883056640625, 0.9152075052261353, 0.23322997987270355, 0.4899602234363556, -0.7373571991920471, -1.2174609899520874, 0.8426074385643005, -0.2287338227033615, -0.10544433444738388, 0.6620544195175171, -0.0527426153421402, -0.5293310284614563, -0.7119140625, 0.3840450942516327, 0.8104704022407532, 0.4757769703865051, 0.005354003980755806, -1.3820996284484863, -0.5002343654632568, 0.5931665301322937, -0.36836424469947815, 1.3663171529769897, -1.328066349029541, 1.022119164466858, -1.24169921875, -0.5311047434806824, -0.42869386076927185, -1.0876001119613647, 1.097568392753601, -0.07048263400793076, -0.2557987570762634, -1.2733831405639648, -1.228359341621399, -0.6961779594421387, -0.8022509813308716, -1.0569336414337158, -0.24231475591659546, -0.38553711771965027, -0.11479370296001434, 0.006130561698228121, 0.6852253675460815, -0.4925060570240021, 0.40422606468200684, 0.5157104730606079, -0.5134216547012329, 0.3168676793575287, -0.32841432094573975, -0.5522997975349426, -0.050703734159469604, -0.07765312492847443, 0.47559699416160583, 0.7310425043106079, 0.43083131313323975, 2.379580020904541, 0.23350341618061066, 0.7936673164367676, -0.008073730394244194, -0.04950668290257454, 0.0664144903421402, -0.7023889422416687, -0.7980371117591858, -0.8033007979393005, -0.14541535079479218], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.

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

{'search_vector': [-0.14514364302158356, 1.1986979246139526, -2.64453125, -0.646289050579071, 1.5957682132720947, -1.40771484375, 0.3733276426792145, -1.1458170413970947, 0.21333108842372894, -0.3427897095680237, 1.8806315660476685, -0.22607269883155823, 1.0480306148529053, -0.0021728514693677425, 0.13270772993564606, 0.25263264775276184, 0.80267333984375, -1.0497883558273315, -0.6396331787109375, -0.22314758598804474, -0.059597525745630264, 0.309133917093277, -0.2920125424861908, 0.2854370176792145, 0.777386486530304, -0.38399454951286316, 0.5274088382720947, 0.16272176802158356, -1.1885905265808105, -0.23389586806297302, 1.6872152090072632, -0.16085204482078552, -0.4160151183605194, -0.7606588006019592, -0.23488768935203552, -0.42384541034698486, 0.849395215511322, -0.23392334580421448, -0.6894449591636658, 0.2510579526424408, -0.436792254447937, -0.32997435331344604, 0.5937825441360474, 0.11239827424287796, 0.8952392339706421, -1.0079752206802368, 0.5336222052574158, -0.11039123684167862, 0.5630045533180237, -1.62060546875, 0.2104644775390625, -0.62408447265625, -0.306396484375, -1.1042969226837158, 0.5791910886764526, 0.1661783903837204, -0.26591795682907104, 1.6360026597976685, -1.3297525644302368, 0.40037232637405396, 1.1742513179779053, 0.5683349370956421, -0.48875123262405396, 1.7944010496139526, 1.0867187976837158, 0.09830863028764725, -1.0719115734100342, 0.4144901633262634, -0.5795247554779053, -0.8628092408180237, 0.40404000878334045, -0.5644978880882263, 1.1082112789154053, 0.11492360383272171, -0.15399780869483948, 0.5266662836074829, -0.25230535864830017, -1.1620768308639526, -0.38098958134651184, 0.4860087037086487, -0.451562762260437, -0.16110433638095856, 0.4018915891647339, -0.8701578974723816, 0.20293782651424408, 0.3570515811443329, -0.36982014775276184, 0.27341511845588684, -0.7690144777297974, 1.2648030519485474, -0.2696492373943329, -0.10801022499799728, 0.1365310698747635, -0.1125284805893898, -0.8827759027481079, 0.5968862175941467, -0.915417492389679, 0.7185506224632263, -1.1556071043014526, -0.09966227412223816, -0.03437093272805214, 0.8102701902389526, 0.4381065368652344, 0.32670897245407104, 0.8332356810569763, -0.2703994810581207, 0.5249099731445312, 0.9309356808662415, 0.9473469853401184, -0.21858316659927368, -0.11325886845588684, 0.6391153931617737, -0.06624756008386612, -0.6428467035293579, 0.41976216435432434, -0.47712454199790955, 0.7982340455055237, 0.3720020353794098, 0.7944743037223816, 1.3732746839523315, -0.626293957233429, -0.681427001953125, -0.4050150513648987, 0.8624349236488342, 0.6480387449264526, -0.09297892451286316, -0.9539072513580322, 0.8406972289085388, 0.20250244438648224, -0.42080891132354736, -0.7993977665901184, -2.1895833015441895, -1.1710611581802368, -0.01999104768037796, -0.5587117671966553, -0.05709126964211464, -1.4730143547058105, -0.38177692890167236, 0.4566813111305237, 0.8375569581985474, 0.72894287109375, -0.1911468505859375, 0.42337238788604736, -0.04839477688074112, -0.7838587164878845, -0.30373433232307434, 1.1798176765441895, -0.23017577826976776, 0.1632232666015625, 0.1477857530117035, -0.38805344700813293, 1.3394856452941895, 0.17356668412685394, 1.3570637702941895, -0.14163818955421448, 0.14694824814796448, -0.00743815116584301, 0.07857004553079605, 1.2024739980697632, -0.35610759258270264, 0.8130859136581421, -0.38108113408088684, -0.3638707399368286, 0.7329915165901184, 0.01104125939309597, -0.4410563111305237, 0.7796875238418579, 0.7920069098472595, 0.33294981718063354, 1.4862630367279053, -1.1337565183639526, -0.6635071039199829, 0.616809070110321, 0.208811953663826, 1.0871745347976685, -0.6476501226425171, 0.4206990599632263, -0.1040242537856102, 0.7637532353401184, -0.5414876341819763, -0.04798024520277977, -1.3590983152389526, 0.17023327946662903, 0.4705037474632263, -0.8570149540901184, 0.20328572392463684, -0.310302734375, -0.2673278748989105, -0.3058675229549408, -1.9634114503860474, 1.1983317136764526, 0.5140787959098816, -0.8789957761764526, 0.1721089631319046, -0.7010090947151184, -0.08497314155101776, 0.7762206792831421, -0.2110392302274704, 0.7768229246139526, -0.22252807021141052, 0.3684428036212921, -0.31485798954963684, -0.45657551288604736, 0.5211832523345947, -0.2957356870174408, -0.2956298887729645, 0.5758301019668579, -0.031005859375, -0.7503906488418579, 0.3270711302757263, 1.6569743156433105, -0.0809733048081398, -1.4787434339523315, 0.006343587301671505, -0.37468260526657104, -0.2290852814912796, -0.02190806157886982, 0.07489827275276184, -0.3236450254917145, 0.34522297978401184, 0.7020711302757263, -1.2235026359558105, 0.2662821412086487, -1.069672703742981, -0.47800928354263306, 0.38176754117012024, -1.411230444908142, -1.267333984375, -0.49664103984832764, 0.5064290165901184, -0.32243043184280396, -0.7928507328033447, 0.146739199757576, 0.4649861752986908, 0.02854207344353199, -0.3390950560569763, 0.5699808597564697, 1.1426351070404053, 0.15161743760108948, -0.9388509392738342, -0.3396260440349579, -0.46724802255630493, -0.6242431402206421, 0.6650227904319763, -1.9103515148162842, -0.3408854305744171, -0.41736653447151184, -0.5844767093658447, -0.3519134521484375, 0.6710164546966553, -0.16473388671875, -0.2669779360294342, 0.4176991879940033, 0.2794942259788513, 0.10895995795726776, 0.09651590883731842, 0.7954264283180237, 0.47440797090530396, 0.630566418170929, -1.306640625, 0.3371073305606842, -0.24164022505283356, -0.18426920473575592, -0.4206400513648987, -0.2757324278354645, -0.052814483642578125, 0.34286803007125854, 1.1378173828125, -0.488790899515152, -0.9319986701011658, 0.4766433835029602, -0.01652119867503643, 0.9312662482261658, 0.6438924074172974, 0.7663838863372803, -0.08941040188074112, 0.005444335751235485, -0.02010294608771801, -0.04279785230755806, 1.3112629652023315, -0.7908610105514526, -1.301171898841858, -0.8055582642555237, -0.08191121369600296, -0.33511149883270264, 0.743603527545929, 0.11678466945886612, 0.17108561098575592, 0.4975138306617737, -0.21872279047966003, 1.7404948472976685, -0.1709599792957306, -0.8316568732261658, 0.3636332154273987, -0.06883341819047928, 0.15448099374771118, 0.9313802123069763, -0.7998860478401184, 0.4918456971645355, -0.8155985474586487, -0.094635009765625, 0.617919921875, 1.260009765625, 0.3435312807559967, -0.0244776401668787, 0.19054336845874786, 0.7554224729537964, -0.3810587525367737, 0.5621622800827026, 1.0394856929779053, -0.06886393576860428, 0.806079089641571, -0.6401204466819763, -0.10365486145019531, -0.0064331055618822575, 0.2833821475505829, 0.8736979365348816, 0.5610433220863342, 0.48295897245407104, 1.6574870347976685, -0.23944905400276184, -0.12595418095588684, -0.5560384392738342, 0.02167103998363018, 0.6867431402206421, 0.29000625014305115, -0.8231567144393921, 0.02406616136431694, 0.4365040957927704, 0.45919087529182434, 0.0396219901740551, -0.5224587917327881, -0.1205647811293602, -1.7447590827941895, -0.8077392578125, 0.1795247346162796, 1.4151692390441895, 1.018701195716858, 0.889599621295929, 0.4728744626045227, 0.6083536744117737, -1.4552408456802368, 1.0832926034927368, -1.9978516101837158, -0.7375631928443909, 0.13539734482765198, 0.7511777281761169, 0.09687907248735428, 0.9510253667831421, 0.08922271430492401, -0.6266682744026184, 0.48184001445770264, -0.586474597454071, 0.07272135466337204, 0.5204437375068665, -0.2466176301240921, 0.7039347290992737, 0.6841145753860474, -0.5072491765022278, 0.3133544921875, 0.8921874761581421, 0.10700175166130066, 0.5569986701011658, -0.06985677033662796, 0.08704833686351776, 0.011395263485610485, 0.16405436396598816, -0.2623697817325592, -0.47859495878219604, -0.69110107421875, 0.7989542484283447, -1.3367513418197632, -0.49408671259880066, 0.639416515827179, -0.17946776747703552, 0.684173583984375, -1.5251953601837158, -0.7882039546966553, -1.2216390371322632, 0.4461832642555237, 0.6087239384651184, 0.27377521991729736, 0.3784169554710388, 0.9493245482444763, 0.17984212934970856, -0.15395355224609375, -0.7636963129043579, 0.0961507186293602, -0.2855183780193329, 0.3059377074241638, 0.3924824893474579, -2.052474021911621, -0.14682413637638092, 0.9247922301292419, 0.03747660294175148, -0.160664364695549, 0.9849446415901184, -0.4215657413005829, -0.0579071044921875, 1.480096459388733, -0.772417426109314, -1.1332213878631592, -0.0920867919921875, -1.1919108629226685, 0.14002838730812073, -0.02833658829331398, -1.1571614742279053, -1.0074747800827026, 0.20260213315486908, -0.08912523835897446, 0.20285552740097046, 0.18653157353401184, -0.5102747678756714, -0.34427592158317566, 0.44383010268211365, -0.22321167588233948, 0.7791666388511658, -0.04208577424287796, -0.18144531548023224, -0.8914469480514526, -0.05985107272863388, 0.13097737729549408, 0.6823405027389526, -0.0004962921375408769, 0.30386048555374146, 1.1141927242279053, 0.24504750967025757, 0.89532470703125, -0.07764485478401184, -0.7894205451011658, -0.21946920454502106, 0.7787923216819763, 0.6433187127113342, -0.4508097469806671, -0.37619680166244507, -0.5513346195220947, -0.4122467041015625, 0.23557943105697632, 0.9451578855514526, 0.5051406621932983, 0.8644043207168579, 0.6027964353561401, -0.7638509273529053, 0.15295003354549408, -0.46605223417282104, 1.9097005128860474, 0.9709554314613342, 0.3104960024356842, -0.5469930171966553, -0.13740666210651398, 0.4326680600643158, 0.1892392486333847, 0.1751302033662796, 0.3681192994117737, 0.9329264163970947, 0.09061025083065033, -0.062299855053424835, 0.3853312134742737, 0.5662679076194763, 0.6693440675735474, 0.7995442748069763, 0.41048991680145264, -1.6145182847976685, 0.23321838676929474, -0.17619222402572632, 0.7092732787132263, 1.2238444089889526, 0.5699564814567566, 0.9007650017738342, 1.0156575441360474, -1.7057942152023315, 0.2542071044445038, 0.6132090091705322, 0.46892088651657104, 0.11826375126838684, 0.4047139585018158, -1.140966773033142, 0.3739379942417145, -0.5731608271598816, 0.6985158324241638, -0.07566019892692566, -0.507617175579071, -0.5028076171875, -0.8243245482444763, -0.08286946266889572, -0.10355326533317566, 0.21937765181064606, -0.7942301630973816, 0.20744730532169342, 0.026730060577392578, 0.19921875, -0.12389526516199112, -0.31606751680374146, 1.2747721672058105, 0.6156423091888428, -0.3262288272380829, -0.02165120467543602, 0.3540852963924408, -0.8152831792831421, -0.397787481546402, 0.09440205991268158, 0.6988607048988342, -0.557263195514679, -1.3047648668289185, 0.859893798828125, -0.02330525778234005, 0.18833822011947632, -1.0300456285476685, 0.14141133427619934, -0.2037353515625, 0.13257955014705658, -0.23114013671875, -0.142578125, 0.49235838651657104, 0.3990641236305237, -0.28834331035614014, 0.9591308832168579, -0.29702556133270264, 0.21530558168888092, 0.3947184383869171, -0.727276623249054, -0.5347320437431335, 0.012638982385396957, -0.9759521484375, -1.293773889541626, -0.18512573838233948, 0.5188832879066467, 0.5157226324081421, 0.09571126103401184, -0.27707621455192566, -0.006175740621984005, 0.44326069951057434, -1.2162353992462158, -0.5392506718635559, -0.10693969577550888, -0.2617391049861908, -0.32801106572151184, 0.7653238773345947, 1.6216471195220947, 0.71728515625, 0.37318775057792664, -0.22763265669345856, 0.22797037661075592, 0.5282369256019592, -0.5469909906387329, -0.37497252225875854, -0.5252360105514526, -0.02527465857565403, 0.01563517190515995, -0.8906657099723816, 0.6522867679595947, -1.704003930091858, -0.26996511220932007, -0.5859090089797974, 0.2667602598667145, -0.46663233637809753, -0.23250630497932434, 0.4587300717830658, 0.7594970464706421, -0.8658284544944763, 0.8310384154319763, 0.09597168117761612, -0.33057913184165955, 0.02987365797162056, 0.5347198843955994, -0.973803699016571, -0.19551798701286316, -0.011430867947638035, 0.324044793844223, 0.5434793829917908, -0.4884847104549408, -0.959667980670929, 0.05581258237361908, 0.4489339292049408, 0.528076171875, -0.2623657286167145, -0.04912211000919342, 0.11924692988395691, -1.1868164539337158, -0.42302244901657104, 0.735156238079071, -0.6151041388511658, 0.8560435175895691, 1.1075520515441895, 0.2516011595726013, 0.21148274838924408, -1.091833472251892, -0.9634063839912415, 0.20876871049404144, -0.719775378704071, -0.45250651240348816, 0.04044291004538536, -0.21751098334789276, -1.1293131113052368, -0.5594645142555237, 0.5846954584121704, -0.2858479917049408, -0.6193827390670776, -0.2411137968301773, 0.132762148976326, -0.6019937992095947, -0.2072550505399704, 0.4707438051700592, -0.2662109434604645, -0.8599283695220947, 0.8390258550643921, 0.8792175054550171, 0.7815755009651184, -0.08444010466337204, -1.0968343019485474, 1.3775715827941895, 0.15706786513328552, -0.4478098452091217, -0.38630980253219604, -0.02545878104865551, -0.5045545697212219, 0.4410659670829773, -0.6289957761764526, 0.41475626826286316, -0.24454829096794128, -0.6037343144416809, -1.2555582523345947, 0.949267566204071, -0.29277342557907104, 0.721630871295929, -0.6769856810569763, -0.7066568732261658, 0.38363850116729736, 0.37432047724723816, 0.5258381962776184, 0.6498433351516724, 0.4204142391681671, -0.32842713594436646, -1.7263346910476685, -1.7620768547058105, 0.2313232421875, -0.32260334491729736, -0.077392578125, 0.0752410888671875, 0.8220062255859375, 1.865136742591858, -0.34842732548713684, -0.9630492925643921, 0.15959371626377106, 0.3553425967693329, -0.5794769525527954, 0.10672963410615921, 1.2129557132720947, 0.3237141966819763, 0.39230015873908997, 1.6136068105697632, 1.1593912839889526, 0.8160809874534607, -0.03323974460363388, 0.8102701902389526, -0.07768147438764572, 0.6215006709098816, -0.4035237729549408, -0.7097818851470947, 0.17301635444164276, 0.7805257439613342, 0.26660358905792236, 0.1725311279296875, 0.500628650188446, 1.2859050035476685, -0.430938720703125, 0.44566041231155396, -0.3560038208961487, -0.9593770503997803, 0.24943441152572632, 0.3885335326194763, -0.703356921672821, -1.3880534172058105, -0.7881429195404053, 1.0612956285476685, 0.13697916269302368, 0.6360712647438049, 0.7006515264511108, -1.0013681650161743, -0.21723225712776184, 0.5154019594192505, -0.4220621883869171, 1.658300757408142, 0.31558889150619507, -0.9986327886581421, -0.4953755736351013, -0.7976725101470947, -0.6669413447380066, -0.2669921815395355, -0.7664255499839783, -0.02064971998333931, -0.49541932344436646, 0.1127217635512352, 0.14326375722885132, -0.1778971403837204, -0.19683837890625, -0.8699930906295776, 0.3717387020587921, -0.38845622539520264, 0.7041218876838684, 0.06049194186925888, 0.9613199830055237, 0.7877522706985474, 1.2802571058273315, 0.05302734300494194, 0.13682454824447632, 0.41451823711395264, 0.255081444978714, 0.7945638298988342, -0.34315186738967896, -1.0806925296783447, 0.5177001953125, -1.1192057132720947, 0.5457852482795715, -0.3268880248069763, 0.0945027694106102, -0.6877034306526184, -0.4937906861305237, -0.3516082763671875, -0.19789530336856842, 0.8435160517692566, 0.45415446162223816, -0.9372476935386658, -0.12425537407398224, 0.20363005995750427, -0.3627278506755829, 0.9019693732261658, -0.5834798216819763, -0.005082194227725267, -0.5999674201011658, 0.134765625, -0.1638590544462204, -1.2222005128860474, 0.5974771976470947, -0.6100992560386658, -0.4700927734375, -0.3332509398460388, -1.3444010019302368, -1.390478491783142, -0.07565511018037796, -0.3856908082962036, -0.4620000123977661, -0.8942301273345947, 1.2206217050552368, -0.6320750117301941, 0.15152181684970856, -0.19979654252529144, 0.6125264763832092, 0.925402820110321, -0.8244059085845947, 0.4022516906261444, -0.4338785707950592, -1.049829125404358, 0.5856608152389526, -0.5188730955123901, 0.2705037295818329, -0.38817036151885986, 0.4599263370037079, 1.8511393070220947, -0.6173990964889526, 0.5409200191497803, -0.7587071657180786, 0.9395182132720947, -0.37715962529182434, 0.30733439326286316, -0.3556111752986908, -0.9665730595588684, -0.6602010130882263], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (HTTPException | used | request | validation | error | responses)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (FastAPI | uses | async | patterns | database | operations | prevent | blocking | event | loop)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (CRUD | Operations | implemented | using | service | layer | patterns)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Pydantic | schemas | should | used | background | tasks | inappropriately | — | background | tasks | follow | separate | patterns)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (API | integrates | Database | Operations | via | CRUD | operations | from | database | rules)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.

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

{'search_vector': [0.20828819274902344, 1.32391357421875, -2.717041015625, -1.26202392578125, 0.755874752998352, -1.326202392578125, 0.2595481872558594, 0.06243133544921875, -0.3601493835449219, -0.8187103271484375, 0.5821456909179688, 0.03249168395996094, 2.0714111328125, 0.3168296813964844, 0.2705061435699463, 0.6154718399047852, -0.08190727233886719, -0.411895751953125, -0.9180221557617188, 0.9501419067382812, -0.21059894561767578, 0.16484451293945312, -0.49764251708984375, -0.20105266571044922, 1.1846885681152344, 0.12705612182617188, 0.7842025756835938, 0.1187591552734375, -1.664886474609375, -1.2988739013671875, 1.31976318359375, 0.09172821044921875, 0.2799243927001953, -1.1913528442382812, 0.3277702331542969, -0.8163318634033203, 0.838287353515625, 0.2822456359863281, -0.17798900604248047, 0.015338897705078125, -0.08485031127929688, 0.43674659729003906, 0.05778980255126953, -0.26605987548828125, 0.22931408882141113, -0.06230354309082031, 1.247344970703125, -0.28600192070007324, 0.6864385604858398, -1.6379871368408203, -0.41625213623046875, -0.24457359313964844, 0.04013633728027344, -1.3199462890625, 1.3429412841796875, -0.025339126586914062, 0.7270374298095703, 0.869171142578125, -0.1198577880859375, 0.1019287109375, 0.5809402465820312, -0.4390373229980469, 0.44671058654785156, 2.0576171875, 1.36419677734375, 0.8584833145141602, -0.7684059143066406, 0.9247112274169922, -1.0099105834960938, -0.21109390258789062, -0.05587577819824219, -0.24505615234375, 1.0243501663208008, 0.0462188720703125, 0.09716987609863281, 0.48553466796875, -0.013645976781845093, -0.7541732788085938, -1.052886962890625, 0.5727195739746094, -0.3987712860107422, 0.7323265075683594, 0.8128204345703125, -0.36934852600097656, 0.13776826858520508, 0.012058258056640625, -0.4754321575164795, -0.5269355773925781, -1.17041015625, 0.6110038757324219, 0.3588581085205078, -0.19584989547729492, 0.6200652122497559, -0.5173797607421875, -0.6541366577148438, -0.23688733577728271, -0.9181826114654541, 0.9751663208007812, -1.265869140625, -0.5749893188476562, -0.2571382522583008, 0.7537841796875, 1.1593475341796875, -0.5541038513183594, 0.2603602409362793, 0.24843978881835938, -0.26949310302734375, 0.2082977294921875, 0.9241676330566406, -0.6753616333007812, -0.2971372604370117, 0.2759361267089844, -0.1239776611328125, -0.9677062034606934, -0.2145071029663086, -1.260406494140625, 1.0484466552734375, 0.045719146728515625, 0.7010090351104736, 0.25458526611328125, -0.627838134765625, -0.980712890625, 0.22286319732666016, 1.30828857421875, 0.3224496841430664, -0.10881280899047852, -1.037872314453125, 0.32717132568359375, 0.5396957397460938, -1.47222900390625, -0.06741809844970703, -1.51141357421875, -1.1446475982666016, -0.042263031005859375, -0.4623680114746094, -0.16593170166015625, -0.950408935546875, -1.0074710845947266, 0.26988935470581055, 0.579620361328125, 0.21781158447265625, 0.44347381591796875, -0.04295539855957031, -0.6461868286132812, -0.44920921325683594, -0.93511962890625, 0.6033077239990234, -0.12791991233825684, 0.5108833312988281, -0.15484964847564697, -0.707122802734375, 0.897125244140625, 0.18820571899414062, 1.601776123046875, -0.2241373062133789, -0.23626279830932617, 0.41881072521209717, 0.06561279296875, 1.456268310546875, -0.8047637939453125, 0.98480224609375, -0.42501401901245117, -0.6803512573242188, 0.797576904296875, 0.633758544921875, -0.20468354225158691, -0.36652660369873047, 0.15660572052001953, -0.02385711669921875, 1.997802734375, -0.3401551842689514, -0.8991928100585938, -1.1255950927734375, -0.3012576997280121, 1.0242233276367188, -0.10654067993164062, -0.19634389877319336, -0.44107532501220703, 0.8481903076171875, -0.34529852867126465, -0.4253530502319336, -1.0567398071289062, 0.28524017333984375, 0.23264122009277344, -0.3922567367553711, 0.7133522033691406, -0.27649688720703125, -0.142913818359375, -1.1365966796875, -1.104461669921875, 0.3088111877441406, 0.5140066146850586, -0.1421051025390625, 0.15297460556030273, -0.7676849365234375, -0.2894744873046875, 0.6935348510742188, -0.13103485107421875, 0.6197509765625, -0.44274139404296875, 0.14922046661376953, 0.4302482604980469, -0.8061332702636719, -0.19083404541015625, 0.7018060684204102, 0.0112457275390625, 0.2822756767272949, 0.13415050506591797, -0.056629180908203125, 0.19382476806640625, 1.5018692016601562, 0.8141326904296875, -0.7246904373168945, 0.2357025146484375, 0.07782173156738281, 0.2503795623779297, -0.1649761199951172, -0.6078948974609375, -0.2860565185546875, 0.229400634765625, 1.317169189453125, 0.20042800903320312, 0.7540435791015625, -1.299346923828125, -0.07440823316574097, -0.686798095703125, -1.5329742431640625, -0.3925285339355469, -0.5172882080078125, 0.5697593688964844, 0.13051795959472656, -0.774222195148468, -0.1768970489501953, -0.1388254165649414, 0.49540090560913086, -0.14565300941467285, 0.18610572814941406, 1.5796356201171875, 0.15627574920654297, -0.8111648559570312, -0.4617794454097748, -0.700775146484375, -0.6037826538085938, 0.6841888427734375, -1.1873397827148438, -0.5328187942504883, -0.20977401733398438, -0.6159210205078125, -0.24288833141326904, 2.00714111328125, 0.3862895965576172, 0.1923530101776123, -0.057437896728515625, 0.3714561462402344, -0.547393798828125, -0.5505790710449219, 0.027451038360595703, -0.2989654541015625, 0.792510986328125, -0.2934757471084595, 1.25732421875, 0.4593048095703125, -0.2012491226196289, 0.03128242492675781, 0.027315616607666016, -0.7482948303222656, 0.8875503540039062, 0.7651505470275879, 0.06683731079101562, -0.4534454345703125, 0.27175331115722656, 0.1907205581665039, -0.4712028503417969, 0.04350566864013672, 0.29656699299812317, 0.8712692260742188, -0.30118560791015625, -0.05640292167663574, -0.046593666076660156, 1.047332763671875, -0.7219772338867188, -1.52490234375, -0.8794898986816406, 0.0959024429321289, -0.18758583068847656, 0.688446044921875, -0.6539726257324219, -0.3400380611419678, 0.6315536499023438, 0.5564241409301758, 1.80078125, -0.2746410369873047, -1.2380218505859375, 0.5760536193847656, -0.05492830276489258, 0.23299407958984375, 0.784149169921875, -0.36894989013671875, 0.898529052734375, -0.003147125244140625, 0.41668033599853516, -0.03602170944213867, 1.380218505859375, -0.007627964019775391, 0.12152767181396484, 0.399871826171875, 0.46959686279296875, -0.39542388916015625, 1.380584716796875, 0.33643484115600586, -0.06972455978393555, 0.17353248596191406, -0.49988365173339844, 0.294921875, -0.5402259826660156, 0.7594833374023438, 0.7734794616699219, 0.8085193634033203, 1.0422935485839844, 0.6071395874023438, -0.4170910716056824, -0.9060592651367188, -0.6450996398925781, -0.0455169677734375, 0.031368255615234375, 0.35846805572509766, -1.1112518310546875, 0.26848793029785156, 0.3330268859863281, 0.3620796203613281, 0.15179061889648438, -0.6398448944091797, 0.3139643669128418, -1.0117263793945312, -0.4040139317512512, 0.6396827697753906, 0.53509521484375, 0.2475118637084961, -0.42238903045654297, 0.5406703948974609, 1.082427978515625, -1.730987548828125, 1.4667816162109375, -1.910675048828125, -0.6760940551757812, 0.030055999755859375, 0.19684791564941406, 0.11588191986083984, 0.9941864013671875, 0.1816091537475586, -0.49600982666015625, 0.8851318359375, -0.2539710998535156, -0.6582317352294922, -0.3404855728149414, -0.36811065673828125, 1.0377655029296875, 0.5035128593444824, -0.05330848693847656, 1.1552886962890625, 1.1702804565429688, -0.023777008056640625, 0.19823837280273438, -0.28214597702026367, -0.2754554748535156, 0.18999290466308594, -0.23699188232421875, 0.3418237268924713, 0.5039215087890625, 0.5312595367431641, -0.18212127685546875, -1.0319671630859375, -1.12786865234375, 1.369354248046875, -0.44269561767578125, 0.08621668815612793, -1.1308135986328125, -0.5693607330322266, -0.8694648742675781, 0.2059798240661621, 1.15008544921875, 1.1473846435546875, 0.19482660293579102, 0.48053741455078125, 0.4702873229980469, -0.946441650390625, 0.6887016296386719, 0.88092041015625, 0.10426914691925049, 0.2861776351928711, 0.6594066619873047, -1.2345428466796875, -0.10722589492797852, 0.7085819244384766, 0.3794059753417969, 0.03541374206542969, -0.24908447265625, -0.2043476104736328, -0.15970611572265625, 1.6454315185546875, -0.6339626312255859, -1.0761566162109375, -0.1857280731201172, -1.50567626953125, 0.41634678840637207, -0.582916259765625, -1.2659912109375, -0.7396354675292969, 1.0276565551757812, -0.017429351806640625, 0.44618988037109375, 0.3072776794433594, -0.11963176727294922, -0.09037017822265625, 0.5567378997802734, 0.023866653442382812, 0.2771434783935547, -0.419342041015625, -0.938751220703125, -0.38855576515197754, 0.22867584228515625, 0.497775137424469, 0.9884452819824219, 0.7089896202087402, -0.6397552490234375, -0.3975977897644043, 0.1496448516845703, 0.8835182189941406, -0.790374755859375, -1.8873291015625, -0.36067724227905273, 0.6807956695556641, 0.9911994934082031, -1.055450439453125, -0.6386337280273438, -0.78790283203125, 0.5010088682174683, 0.8504314422607422, 0.03503894805908203, 0.6175150871276855, 0.32030677795410156, 0.0840296745300293, -0.7436871528625488, -0.08194732666015625, 0.6273040771484375, 2.348419189453125, 0.22383785247802734, -0.0674281120300293, -0.7972989082336426, 0.03128546476364136, 0.2003631591796875, -0.29338693618774414, 0.010869979858398438, 0.8870487213134766, 1.4818115234375, -0.20845401287078857, -0.48858320713043213, 0.711212158203125, 0.8063802719116211, 0.14340782165527344, 0.323209285736084, 0.1085968017578125, -1.5714111328125, -0.26642894744873047, 0.6476287841796875, 0.32761383056640625, 1.0038681030273438, -0.1717548370361328, 0.8559980392456055, 1.38885498046875, -0.814697265625, -0.3833770751953125, 0.4967050552368164, 0.4339876174926758, 0.7394309043884277, 1.2227020263671875, -0.26821577548980713, 0.7093353271484375, -0.040892601013183594, 0.7381744384765625, -0.4427757263183594, -0.31731104850769043, -0.4482307434082031, -1.2061309814453125, 0.25496673583984375, -0.005967617034912109, 0.5579719543457031, -0.4236488342285156, 1.0371780395507812, -0.63470458984375, 0.4071941375732422, -0.26580047607421875, 0.503692626953125, 0.8207855224609375, 0.16005277633666992, 0.1531963348388672, -0.12750911712646484, -0.6635589599609375, -0.4390548765659332, -0.11704444885253906, -0.26117706298828125, 0.3185330033302307, -0.26860809326171875, -0.6957855224609375, 0.15682411193847656, 0.050240516662597656, 0.4421539306640625, -0.5996747016906738, -0.6050224304199219, 0.6370444297790527, 0.8741302490234375, 0.04421806335449219, 0.551006555557251, -0.05513763427734375, 0.79473876953125, -0.4630413055419922, 0.7844047546386719, 0.27495574951171875, -0.6093788146972656, -0.1337604522705078, -0.5732231140136719, -0.8561363220214844, -0.23717117309570312, -1.461395263671875, -1.31103515625, 0.07098197937011719, 0.6703224182128906, 0.09142065048217773, 1.010833740234375, 0.06392574310302734, -0.7153701782226562, 0.47452354431152344, -1.009552001953125, 0.34769439697265625, 0.3721923828125, -0.6673427224159241, -1.0311908721923828, 0.9951324462890625, 1.478668212890625, 0.2139110565185547, 0.7693557739257812, 0.558964729309082, -0.38999366760253906, 0.0346527099609375, -0.3128662109375, -0.0940096378326416, -0.1786346435546875, 0.5945110321044922, 0.48444557189941406, -0.4618377685546875, 1.0929908752441406, -0.8820686340332031, -0.06194114685058594, -0.8232192993164062, 0.6121139526367188, -0.1452350616455078, 0.3716917037963867, 0.7104759216308594, 0.07925987243652344, -0.7863693237304688, 0.8023147583007812, 0.7713804244995117, 0.5912723541259766, 0.2844734191894531, -0.7409858703613281, -1.0564813613891602, 0.2509956359863281, -0.12000465393066406, -0.183319091796875, 0.78009033203125, 0.46198272705078125, -1.63653564453125, 0.5881508588790894, -0.017608165740966797, 0.4111213684082031, -0.2585182189941406, 0.195529043674469, 0.090301513671875, -0.3269624710083008, -0.9945068359375, 0.4526726007461548, -0.9026470184326172, 0.4357490539550781, -0.1742558479309082, 0.2347041368484497, -0.031925201416015625, -0.8394699096679688, 0.06260108947753906, -0.12201309204101562, -0.4119224548339844, 0.026698589324951172, -0.15662527084350586, 0.33318138122558594, -1.0204277038574219, 0.6721954345703125, 0.0590362548828125, -0.18152952194213867, 0.484527587890625, -0.6124496459960938, 0.2927112579345703, -0.5027313232421875, -1.036346435546875, 1.1663665771484375, -0.3138759136199951, -0.36566364765167236, 0.9116020202636719, -0.3693656921386719, 0.0040683746337890625, -0.12781429290771484, -0.4840717315673828, 1.346588134765625, -0.3404808044433594, -0.9777984619140625, -0.29543304443359375, 0.6376113891601562, -0.933868408203125, 0.3265724182128906, -0.8243217468261719, -0.5496864318847656, 0.002750396728515625, -1.391448974609375, -1.4010009765625, 0.4653453826904297, -0.957366943359375, -0.5484962463378906, -1.0702972412109375, -0.7681198120117188, -0.27905750274658203, 0.25095367431640625, -0.43114662170410156, -0.2293558120727539, 0.8613548278808594, -0.1817607879638672, -1.2385330200195312, -1.424285888671875, 0.5287361145019531, 0.06542587280273438, -0.1410810351371765, 0.8814716339111328, 1.4835205078125, 1.4155256748199463, 0.605224609375, -0.3562350273132324, 0.7429389953613281, 1.1016845703125, -0.3362255096435547, -0.43069833517074585, 0.17664337158203125, 0.31991004943847656, 0.12500381469726562, 2.23638916015625, 1.105072021484375, 0.4228363037109375, 0.08540117740631104, -0.2563152313232422, -0.7857666015625, 0.44993019104003906, -0.4271841049194336, -1.0493812561035156, 0.506744384765625, -0.03459930419921875, -0.24795913696289062, 0.22139549255371094, -0.21001434326171875, 0.7701797485351562, 0.19536781311035156, 0.743621826171875, 0.4956321716308594, -1.2230377197265625, -0.1370433270931244, 0.20920944213867188, 0.287078857421875, -1.293701171875, -0.9338066577911377, 0.8060092926025391, -0.222808837890625, 1.183746337890625, 0.2810788154602051, -0.15090179443359375, -0.40053224563598633, 0.2862701416015625, 0.3427114486694336, 0.6089820861816406, 0.9615478515625, -0.6756246089935303, -0.88092041015625, -0.17331886291503906, -0.4825553894042969, 0.00554656982421875, -0.293731689453125, -0.7483062744140625, -0.9153404235839844, -0.3201172351837158, 0.08525466918945312, 1.2393341064453125, 0.014035224914550781, -0.4984149932861328, 0.007515430450439453, -0.6469345092773438, 0.19139862060546875, -0.40277767181396484, 0.9796457290649414, 0.560643196105957, 0.7606277465820312, -0.7486038208007812, 0.24543380737304688, 0.09459686279296875, -0.26859283447265625, 0.5001735687255859, -1.2222900390625, -1.4329071044921875, 0.6333580017089844, -0.3396940231323242, 0.052303314208984375, 0.5633335113525391, 0.6551971435546875, -0.37430667877197266, -1.1415481567382812, 0.45647430419921875, -0.3174552917480469, 0.3425769805908203, 0.5198287963867188, -1.5662841796875, -0.7199859619140625, 0.9412078857421875, -0.42008399963378906, 0.5926036834716797, -0.43926239013671875, -0.4204096794128418, -0.702545166015625, 0.3812103271484375, -0.5585308074951172, -0.8910515308380127, 1.185516357421875, -0.7973289489746094, 0.0032825469970703125, -0.6971511840820312, -1.3792724609375, -1.665069580078125, 0.7918853759765625, -0.761383056640625, -0.45648956298828125, -0.6986465454101562, 0.4711761474609375, -1.0142059326171875, 0.07478523254394531, -0.27062034606933594, 0.8460540771484375, 1.1139373779296875, -0.37968873977661133, 0.4126396179199219, -1.1535224914550781, -1.8697509765625, 0.21213531494140625, 0.2667388916015625, 0.2622833251953125, -0.4143019914627075, 1.0019683837890625, 2.37213134765625, 0.23618698120117188, 1.1855888366699219, -0.731903076171875, -0.17612075805664062, -0.49146080017089844, 0.4011344909667969, -0.735015869140625, -0.5451064109802246, -0.8480224609375], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (FastAPI | used | implementing | API | endpoints)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.

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

{'search_vector': [0.38629150390625, 1.0286544561386108, -2.650341749191284, -0.679339587688446, 1.0173332691192627, -1.454309105873108, 1.3128845691680908, -0.43152618408203125, 0.5378051996231079, -0.8388282656669617, 1.2809479236602783, 0.3993986248970032, 1.935766577720642, 1.0618164539337158, 0.06594429165124893, 0.4573379456996918, -0.1266578733921051, -0.513903021812439, -0.9200506210327148, -0.362081915140152, -0.0035644532181322575, 0.2776992917060852, -0.563153088092804, 0.7072387933731079, 1.1251510381698608, 0.4386840760707855, 0.600238025188446, 0.18948975205421448, -1.5695679187774658, -0.49017030000686646, 1.2934410572052002, 0.8457123041152954, 0.04997415468096733, -1.6659667491912842, -0.151927188038826, -0.6093841791152954, 0.21404094994068146, 0.12791308760643005, -0.1300811767578125, 0.522412121295929, -0.6727828979492188, 1.1870498657226562, 0.905181884765625, -0.11803436279296875, 0.600555419921875, -0.694854736328125, 0.9062774777412415, 0.14053449034690857, 0.2926446795463562, -1.4436523914337158, -0.14278563857078552, -0.7583175897598267, 0.774029552936554, -1.421960473060608, 1.259912133216858, 0.7572876214981079, 0.35175246000289917, 1.135351538658142, 0.04296417161822319, 0.03508567810058594, 0.958544909954071, 0.5068893432617188, 0.18144455552101135, 1.3805420398712158, 0.26203614473342896, 0.1956993043422699, -0.8922058343887329, 1.1826355457305908, -0.507153332233429, 0.3555557131767273, 0.6796463131904602, -0.09351196140050888, 0.7525185346603394, 0.04937248304486275, 0.18623046576976776, 1.4124267101287842, -0.4604431092739105, -0.5179107785224915, -0.4546428620815277, 0.7563560605049133, -0.977185070514679, 0.19566306471824646, 0.06930236518383026, -0.11234436184167862, 0.8579780459403992, -0.45602187514305115, -0.7261638641357422, -0.3636733889579773, -0.9420501589775085, 1.284143090248108, 0.7073631286621094, -0.34923094511032104, 0.4235168397426605, -0.3925414979457855, -1.2992645502090454, 0.7675125002861023, -0.1695709228515625, 0.5420257449150085, -1.198156714439392, 0.05805664137005806, 0.3155197203159332, 0.9146591424942017, 0.5532470941543579, -0.3505615293979645, 0.3968093991279602, -0.5441665649414062, -0.5862953066825867, -0.16124963760375977, 0.18128128349781036, 0.030333328992128372, 0.5912734866142273, 0.3734123110771179, -0.349569708108902, -0.8671935796737671, -0.571704089641571, -0.6014159917831421, 0.8450469970703125, -0.529736340045929, -0.2308807373046875, 0.031259726732969284, -0.8730224370956421, -0.4786186218261719, -1.379241943359375, 0.6238769292831421, 0.3461553454399109, 0.2310325652360916, -0.9998825192451477, 0.8331825137138367, 0.3820556700229645, -1.5570557117462158, -0.21341857314109802, -1.2373778820037842, -0.7934433221817017, 0.7134857177734375, 0.6634140014648438, -0.12758179008960724, -0.44391173124313354, -0.49314576387405396, 1.455468773841858, -0.14496764540672302, 0.8281173706054688, 0.6708042025566101, -0.5335296392440796, -0.331512451171875, -0.9251922369003296, -0.380227655172348, 0.6136520504951477, -0.01867222785949707, 0.42046815156936646, 0.1568431854248047, 0.08429994434118271, 1.0457763671875, 0.06592559814453125, 1.1402587890625, 0.041622161865234375, -0.6260830163955688, 0.2965148985385895, 0.345968633890152, 0.828381359577179, 0.7959686517715454, 1.314208984375, -0.4408279359340668, -0.752551257610321, 0.5215545892715454, -0.908679187297821, -0.717803955078125, 0.7101104855537415, 1.2729003429412842, 0.2503795623779297, 1.367089867591858, -1.0825927257537842, -0.9214393496513367, -0.3338607847690582, -0.7484833002090454, 0.8344177007675171, -0.0033355713821947575, -0.3147262632846832, -0.6174125671386719, 0.9262142181396484, -0.48177871108055115, -0.10882110893726349, -1.278955101966858, -0.08939971774816513, 1.1191742420196533, -0.871569812297821, 0.14175263047218323, -0.5067413449287415, 0.575732409954071, -0.6354385614395142, -1.179376244544983, 0.7465049624443054, 0.014141845516860485, -0.6987268328666687, 0.2664436399936676, -1.1476929187774658, -0.4008544981479645, 0.9036010503768921, -0.3181656002998352, 0.814013659954071, -0.49944305419921875, 0.03168068081140518, 0.07229824364185333, -1.0211608409881592, -0.21176795661449432, 0.008755492977797985, 0.223255917429924, 0.8952058553695679, -0.100305937230587, -0.5859901309013367, 0.21605949103832245, 2.023510694503784, 0.22456054389476776, -0.729504406452179, -0.27924346923828125, 0.14776058495044708, 0.11036548763513565, -0.268759161233902, 0.638824462890625, 0.43229979276657104, 0.37867966294288635, 0.7818359136581421, -0.5135074853897095, -0.07720641791820526, -0.7067421078681946, -0.2171192169189453, -0.4084228575229645, -0.41457176208496094, -0.4415268003940582, -0.6922973394393921, -0.11833753436803818, -0.8019508123397827, -1.409814476966858, -0.2218780517578125, -0.461691290140152, 0.46587830781936646, 0.482492059469223, 0.2614250183105469, 2.144580125808716, 0.19291344285011292, -1.0789616107940674, -0.904156506061554, -0.5117540955543518, -0.648211658000946, 0.6876281499862671, -0.5815704464912415, -0.4256591796875, -0.5278030633926392, -0.4464477598667145, -0.31494140625, 0.5660034418106079, -0.07669830322265625, 0.014068603515625, -0.2613334655761719, 0.366476446390152, 0.2191116362810135, -0.8783340454101562, 0.606555163860321, 0.19211426377296448, 0.815887451171875, -0.5143375396728516, 1.099462866783142, -0.15681305527687073, -0.07367630302906036, -0.26798707246780396, 0.4380806088447571, -0.7203003168106079, 0.28088149428367615, 0.7281402349472046, -0.3709564208984375, -0.4898206293582916, -0.05684814602136612, -0.02354583702981472, 0.2293318808078766, 0.6647918820381165, 0.6104354858398438, 0.5318467020988464, 0.07008972018957138, -0.2918083071708679, -0.09011230617761612, 1.245208740234375, -0.9151214361190796, -0.5368286371231079, -0.9430953860282898, 0.4924684464931488, 0.3816467225551605, 1.452233910560608, -0.29754677414894104, 0.20519408583641052, 0.895031750202179, -0.28171539306640625, 0.775935173034668, 0.15377196669578552, -1.0567176342010498, 0.6507568359375, -0.11731262505054474, 0.3039398193359375, 0.797686755657196, -0.14782142639160156, 0.5325596928596497, -0.15450438857078552, 0.5295501947402954, 0.929705798625946, 0.63165283203125, 0.1742212474346161, -0.3098037838935852, -0.02085266076028347, 0.5775144696235657, -0.4565978944301605, 0.2730155885219574, 0.8021179437637329, 0.5465545654296875, 0.11845092475414276, -0.34029847383499146, 0.29180794954299927, -0.5326706171035767, 1.216339111328125, 0.3782753050327301, 0.7463051080703735, 0.752519965171814, 0.459197998046875, -0.45558175444602966, 0.086761474609375, -0.024419594556093216, 0.42555075883865356, -0.641593337059021, 0.04412841796875, -0.5147231817245483, 0.3047012388706207, -0.009646606631577015, -0.349557489156723, 0.18121032416820526, -0.11381454765796661, 1.279138207435608, -1.2686233520507812, -0.7173736691474915, -0.12139587104320526, 0.8824203610420227, 0.7016937136650085, -0.23998641967773438, 0.31319159269332886, 0.8791106939315796, -1.6674072742462158, 1.576086401939392, -2.3395018577575684, -0.8102855682373047, 0.6897567510604858, 0.37103843688964844, -0.17142944037914276, 0.8621155023574829, 0.6057575345039368, -0.569018542766571, 0.41457366943359375, -0.9567168951034546, -0.617510974407196, 0.3921829164028168, -0.845806896686554, 0.7217548489570618, 0.3016250729560852, 0.09149322658777237, -0.1183929443359375, 0.8476154208183289, -0.0045562745071947575, 0.14334258437156677, -0.10643768310546875, -0.3697624206542969, 0.5639495849609375, 0.316497802734375, -0.473898321390152, 0.3150634765625, -0.09902191162109375, 0.8956451416015625, -1.025146484375, -0.2757202088832855, 0.28000277280807495, -0.17055968940258026, 0.10220928490161896, -1.2023193836212158, -0.19511719048023224, -0.1937210112810135, 0.3544982969760895, 0.8371833562850952, -0.4713501036167145, 0.38766488432884216, 0.6952911615371704, -0.07737674564123154, -0.04725036770105362, 0.24422073364257812, 0.29306715726852417, -0.11827240139245987, -0.03973503038287163, 0.6542304754257202, -1.4745880365371704, 0.07059554755687714, 0.47734832763671875, 0.883197009563446, -0.567675769329071, 0.34751588106155396, -0.04748687893152237, -0.15916137397289276, 1.59796142578125, -1.210168480873108, -1.1074546575546265, -0.39504241943359375, -1.643896460533142, 0.391815185546875, 0.07012252509593964, -1.006414771080017, -0.6572507619857788, 0.7236675024032593, -0.4658645689487457, 0.13932304084300995, 0.15191078186035156, -0.09525299072265625, -0.4094696044921875, 0.15091553330421448, 0.17950133979320526, 1.315405249595642, 0.9891906976699829, -0.13226470351219177, -0.9968932867050171, -0.8539810180664062, 0.84033203125, 0.7871307134628296, 0.5526906847953796, -0.5900284051895142, 0.4444311261177063, 0.4826217591762543, 0.947399914264679, -0.29514235258102417, -0.7778900265693665, -0.1203228011727333, 0.17120972275733948, 0.8367579579353333, -0.6577644348144531, -0.18247222900390625, -0.7504638433456421, 0.7077010869979858, 1.1626465320587158, 0.22178497910499573, 0.776599109172821, 0.9006866216659546, -0.14558105170726776, -0.538064181804657, 0.41707152128219604, -0.3953292965888977, 2.357470750808716, 0.7074960470199585, 0.19160234928131104, -0.32540130615234375, 0.0738426223397255, -0.550488293170929, 0.5474700927734375, -0.034658052027225494, 0.163787841796875, 0.9479934573173523, -0.5928322076797485, -0.48835259675979614, 0.89190673828125, 0.5540435910224915, 0.916302502155304, 0.56585693359375, 0.10991211235523224, -1.44659423828125, 0.09973537921905518, -0.08227310329675674, 0.37885475158691406, 1.0854980945587158, -0.24045772850513458, 0.8780761957168579, 0.5743301510810852, -0.804553210735321, 0.2590537965297699, 0.3101547360420227, 0.015724945813417435, -0.04853362962603569, 0.7017528414726257, -0.15314331650733948, 0.4984433054924011, 0.7311538457870483, 1.2212646007537842, -0.3334510922431946, -0.22789879143238068, -0.5784675478935242, -0.6259613037109375, -0.502331554889679, 0.42107391357421875, 0.36795860528945923, -0.763378918170929, 0.11471786350011826, 0.7142120599746704, 0.392434686422348, -0.04816284030675888, 0.6450790166854858, 0.8254501223564148, 0.4625038206577301, -0.111419677734375, 0.3661155700683594, 0.6509460210800171, -0.7984069585800171, -0.5613601803779602, -0.41876524686813354, -0.12071476131677628, -0.532958984375, -1.581994652748108, 0.41545557975769043, 0.6420873403549194, 0.49955978989601135, -0.41841182112693787, 0.386993408203125, -0.07440872490406036, -0.0023040771484375, -0.108551025390625, 0.5186309814453125, 0.33083876967430115, 0.830657958984375, -0.6630851626396179, 1.1207764148712158, -0.7061370611190796, -0.658245861530304, -0.33371275663375854, -1.105493187904358, -0.3475818634033203, -0.23504944145679474, -0.9855896234512329, -1.001379370689392, -0.378549188375473, -0.30621832609176636, 0.11855163425207138, -0.4282112121582031, -0.05403337627649307, -0.849560558795929, -0.27437248826026917, -1.370263695716858, -0.8730407953262329, 0.27065593004226685, -0.6467865109443665, -0.17110224068164825, 0.15008850395679474, 1.302636742591858, 0.8260849118232727, 0.8679725527763367, 0.12647095322608948, 0.0047013284638524055, 0.29774779081344604, -0.48836517333984375, -0.404135137796402, -0.700427234172821, -0.017995452508330345, 0.15451660752296448, -1.0403693914413452, 0.9112548828125, -0.32876816391944885, -0.2593059539794922, -1.2513427734375, -0.1281593292951584, 0.3096412718296051, -0.03635096549987793, -0.01967468298971653, -0.307626336812973, -0.771899402141571, 0.31215667724609375, 0.8522399663925171, 0.663525402545929, -0.12235260009765625, -0.10261459648609161, -1.2910034656524658, -0.09645538032054901, -0.3944900631904602, -0.1776658147573471, 1.0338256359100342, 0.26800841093063354, -0.7731689214706421, -0.490413099527359, 0.5627769827842712, 0.3004646301269531, 0.13747939467430115, 0.14826354384422302, -0.3875885009765625, -0.7469749450683594, -0.69927978515625, 0.09257087856531143, -0.9896484613418579, 0.48636168241500854, 0.7701660394668579, 0.638751208782196, -0.4432220458984375, -0.6813446283340454, 0.2546981871128082, 0.01157226599752903, -1.004673719406128, -0.8711959719657898, 0.07735519111156464, -0.44880372285842896, -0.6751629114151001, 0.3358932435512543, 0.24869804084300995, -0.8722168207168579, -0.7319091558456421, -0.5982605218887329, -0.5479675531387329, -0.8756023645401001, -0.168293759226799, 0.762249767780304, -0.8885437250137329, -0.49776917695999146, 1.6283690929412842, 0.06627960503101349, 0.6905383467674255, -0.8810264468193054, -0.761737048625946, 0.8247436285018921, -0.581957995891571, -0.47119140625, 0.2638710141181946, -0.08911285549402237, -0.8786819577217102, 1.1749145984649658, 0.00171661376953125, -0.4261581301689148, 0.22633972764015198, -0.6002441644668579, -0.931811511516571, 0.6076690554618835, -0.8408142328262329, 0.45641785860061646, -0.48746147751808167, -0.36692506074905396, -0.6312240362167358, 0.377981573343277, 0.35374754667282104, -0.01840820349752903, 0.5559623837471008, -0.876904308795929, -0.6296585202217102, -1.3036377429962158, 0.7375640869140625, -0.6937011480331421, 0.5207855105400085, 0.19188079237937927, 0.6833595037460327, 1.285925269126892, 0.859222412109375, 0.12293090671300888, 0.14526978135108948, 0.6581741571426392, -0.17465820908546448, 0.7621036767959595, 1.276098608970642, 0.8130159378051758, -0.5893779993057251, 1.4946777820587158, 1.0990111827850342, 0.83135986328125, 0.24497680366039276, 0.5299785733222961, -0.4103897213935852, 0.949206531047821, -0.4848426878452301, -0.8616393804550171, -0.5014495849609375, 0.10763559490442276, -0.45149001479148865, 0.05772705003619194, -0.4986099302768707, 1.3270263671875, 0.4623054563999176, 0.33697929978370667, -0.09206046909093857, -0.7026370763778687, 0.0337861068546772, -0.12343291938304901, -0.47461891174316406, -1.1431305408477783, -1.5214354991912842, 0.23797912895679474, 0.5090698003768921, 0.775195300579071, -0.03201599046587944, -0.8783615231513977, -0.399697870016098, 0.11833381652832031, -0.23074035346508026, 0.505950927734375, -0.13485947251319885, -0.37415504455566406, 0.676622748374939, -0.5404834747314453, -0.18745574355125427, -0.5131927728652954, -0.3414764404296875, -0.4753662049770355, -0.18808288872241974, -0.8994537591934204, -0.9201324582099915, 0.45536231994628906, -0.05795135349035263, -1.1101257801055908, -0.5290511846542358, -0.4303256869316101, 0.5788360834121704, -0.551135241985321, 1.1116943359375, 1.049774169921875, 1.003851294517517, 0.3173980712890625, 0.01716461218893528, 0.6656845211982727, 0.07957877963781357, 0.4248046875, -0.24316444993019104, -0.7020263671875, 0.394387811422348, -0.704925537109375, 0.24580001831054688, 0.20140381157398224, -0.693920910358429, -0.8384407162666321, -0.797808825969696, -0.17973022162914276, -0.15147705376148224, 0.2548538148403168, 0.2102401703596115, -0.760345458984375, 0.0011789321433752775, -0.28637999296188354, -0.7157500982284546, 0.615155041217804, -0.41669923067092896, 0.5087906122207642, -1.0161330699920654, 0.2904312014579773, -0.34382933378219604, -0.63641357421875, 0.7520805597305298, -0.852221667766571, 0.1905231475830078, -1.211816430091858, -1.3744385242462158, -1.8138916492462158, 0.04010619968175888, -0.33040085434913635, -0.331063836812973, -0.9474853277206421, 0.8143860101699829, 0.02229003980755806, 0.25189208984375, 0.20119933784008026, 0.2943481504917145, 0.6836029291152954, -0.2414112091064453, 0.4446571469306946, -0.9793701171875, -1.932348608970642, 0.4016967713832855, 0.491018682718277, 0.832489013671875, -0.4448188841342926, 0.12591925263404846, 2.2492918968200684, -0.2268955260515213, 0.955395519733429, 0.11375713348388672, -0.3381805419921875, -0.37434691190719604, 0.454171746969223, -0.961346447467804, -0.024211883544921875, -0.957019031047821], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (FastAPI | integrates | schemas | defined | API | rules)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.

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

{'search_vector': [0.6475352048873901, 1.344012975692749, -2.850210428237915, -1.0801626443862915, 1.6564377546310425, -0.022416334599256516, -0.66556316614151, 0.6292912364006042, 0.3311251103878021, -0.9673039317131042, 0.4262789189815521, 0.5745943784713745, 1.000089168548584, 0.02104656584560871, 0.07860624045133591, -0.5327659249305725, 1.199725866317749, -0.948073148727417, -0.30587533116340637, -0.21521231532096863, -0.4571075439453125, -0.8363365530967712, -1.059326171875, -0.811303973197937, 2.477313756942749, 0.07860154658555984, 0.03348013013601303, 0.5140193104743958, -2.021183967590332, 0.12514320015907288, -0.30695754289627075, -0.3333716094493866, 1.0035446882247925, -0.052440937608480453, 0.05159818381071091, -0.4587543308734894, -0.7483955025672913, -0.22601787745952606, -0.6644169688224792, -0.3201387822628021, -0.251251220703125, -0.6258568167686462, 0.21807979047298431, 0.05689268931746483, 0.7790104746818542, 0.083740234375, 0.8647390604019165, 0.37197640538215637, 0.9399977326393127, -1.4241286516189575, 0.783982515335083, -1.192119836807251, 0.06397423148155212, -0.5244985818862915, 1.3621920347213745, 0.77398681640625, -0.529738187789917, 1.1619967222213745, -0.823486328125, -0.7846491932868958, 0.6848707795143127, 1.277681827545166, 0.12970440089702606, 0.931107759475708, 1.2070876359939575, -0.2686016261577606, -1.3369140625, 0.8571214079856873, -0.7806678414344788, -0.26097458600997925, 0.9979975819587708, 0.24482139945030212, -0.3052379786968231, 0.6883639097213745, -1.208646297454834, -0.14765578508377075, 0.2846544682979584, -1.304762601852417, 0.2965792119503021, 0.633697509765625, -0.32175934314727783, -0.520094633102417, -0.2835835814476013, -1.2161208391189575, 0.2994243800640106, 0.5037654042243958, -0.5623121857643127, 1.1156216859817505, -1.1314791440963745, 1.1856595277786255, 1.015164852142334, -0.40062829852104187, 0.6506535410881042, 0.46000906825065613, -2.048959493637085, 0.8241999745368958, -0.042010966688394547, 0.8634690642356873, -0.4481107294559479, -0.292877197265625, -0.369839072227478, 0.013916015625, -0.06361271440982819, -0.23411795496940613, 0.1995473951101303, 0.9746856689453125, -0.46730393171310425, 1.371168851852417, 0.1483694165945053, -0.31519025564193726, -0.8202420473098755, 1.5003567934036255, -0.560988187789917, -0.391754150390625, 0.19651442766189575, -0.25471848249435425, 1.062349796295166, 0.3221733272075653, 0.06602125614881516, 1.29296875, 0.46639543771743774, -0.66943359375, -0.11725088208913803, 1.3114670515060425, -0.033247727900743484, -0.24012638628482819, -0.21094748377799988, 0.1713022142648697, 0.37655404210090637, -1.1562875509262085, -0.49003130197525024, -0.9288235902786255, -0.5361140370368958, -1.1309157609939575, 0.8965829610824585, -0.1601938158273697, -0.3469918966293335, -0.33517691493034363, -0.5591524839401245, -0.3804180324077606, 0.7199437022209167, -0.14508995413780212, 0.07576458156108856, -0.8367732167243958, 0.9093299508094788, -0.19666935503482819, 0.6790114045143127, 0.2786325216293335, -0.2749469578266144, 0.1644521802663803, -0.7383375763893127, 1.1659029722213745, 0.48507454991340637, 0.11333230882883072, 0.7758601307868958, -0.6725792288780212, -0.12384737282991409, -0.15623591840267181, 0.03067486174404621, 1.2857009172439575, 1.663499116897583, 0.4393979609012604, -0.18378975987434387, 1.686176061630249, 0.2419656664133072, -0.32327741384506226, -0.5546165108680725, 0.9411245584487915, 0.3440381586551666, 1.05029296875, -0.4339059591293335, -0.08534152805805206, 0.5649508237838745, -0.4089255630970001, 0.11328594386577606, 0.14038555324077606, 1.3553372621536255, -0.7221726775169373, -0.10028780251741409, -0.31777718663215637, 0.024979224428534508, -1.1043606996536255, 0.4826190769672394, 0.7029677033424377, -0.43963417410850525, -0.25881722569465637, 0.6122835874557495, -0.29988449811935425, -1.599384069442749, -2.233698844909668, -0.23507925868034363, 0.3097299337387085, -0.632981538772583, -0.31990769505500793, -1.543720006942749, -0.4517070949077606, 1.0103384256362915, -0.9158841371536255, 0.902268648147583, -0.3064950704574585, 0.8570462465286255, 0.39705950021743774, -0.2711416482925415, 0.03048236481845379, -1.1468600034713745, 0.6159949898719788, -0.5948157906532288, -0.17982658743858337, -0.38422685861587524, 0.14289738237857819, 1.3097018003463745, -0.08367685228586197, -1.0886794328689575, 0.4871614873409271, -0.6010319590568542, -0.20533165335655212, -0.15546828508377075, -0.41013747453689575, -1.106644868850708, -0.5031926035881042, 1.46875, 0.05404839292168617, 0.30377197265625, -0.507568359375, -0.7565213441848755, 0.19443805515766144, -1.3325852155685425, 0.3684844970703125, -0.253173828125, -0.2210458666086197, 0.2105492800474167, -0.9836238026618958, 0.6014920473098755, 0.017465444281697273, 0.5613497495651245, 0.6756662130355835, -0.09327110648155212, 0.7093223929405212, 0.14166142046451569, 0.38385480642318726, 0.22412227094173431, 1.844651460647583, -0.9673356413841248, 0.16425029933452606, -1.113863468170166, -0.6519423127174377, -0.23623782396316528, -1.5818434953689575, 0.04944786801934242, 0.040325459092855453, -0.9864783883094788, -0.2700752913951874, 0.945418119430542, -0.44276779890060425, 0.07912034541368484, -1.2141494750976562, 0.025776349008083344, 0.13001778721809387, -0.01747424714267254, -0.1614614576101303, 0.262847900390625, 0.13007061183452606, 0.5218552947044373, -0.7577937245368958, -0.5382596254348755, -1.3730844259262085, 0.2915884256362915, 0.2957933843135834, 0.3154226541519165, -0.025435227900743484, 0.30356070399284363, 0.07918607443571091, -0.36372610926628113, -0.08427546918392181, 1.1868239641189575, -0.4583646357059479, 0.08353834599256516, 0.18166688084602356, 0.03955899924039841, 1.0760451555252075, -0.45820146799087524, -0.6653102040290833, -0.34115836024284363, 0.6288405060768127, 0.35088640451431274, 0.41764479875564575, 0.9040151834487915, 0.11594332009553909, 0.2930532693862915, -0.41254836320877075, 1.080491304397583, -0.6001704335212708, -1.6824105978012085, 0.5882720947265625, 0.24008414149284363, 0.6185490489006042, 1.1995943784713745, -0.47211164236068726, 1.0871018171310425, -1.0997971296310425, -0.3963176906108856, -0.07054490596055984, 0.6180372834205627, 0.6227135062217712, -0.1778717041015625, -0.5365330576896667, 1.8135892152786255, -0.2551645040512085, -0.0007981520611792803, -0.10981163382530212, -1.1957632303237915, -0.20997561514377594, -0.3795072138309479, 1.611666202545166, -0.6679969429969788, 1.328519344329834, 1.118070125579834, 0.11321581155061722, 0.547410249710083, 0.17273184657096863, 0.32906869053840637, -0.636704683303833, 0.15026737749576569, -0.04357381910085678, 0.7356778383255005, -0.32602399587631226, -0.24431316554546356, 0.41452261805534363, 0.21068866550922394, -0.5873647928237915, 0.192280113697052, -0.15937687456607819, 0.14970222115516663, -0.7761512398719788, -0.1658559888601303, -0.40708687901496887, -0.2916165888309479, 0.0549468994140625, 0.7915860414505005, 0.676513671875, 0.9809194803237915, -0.5055447816848755, 0.3992021977901459, -0.5716752409934998, -0.15068289637565613, -0.13797232508659363, -0.7526620626449585, -0.19376666843891144, 1.150897741317749, 0.5028780698776245, -0.4998262822628021, 0.9958120584487915, 0.48959586024284363, -0.44604963064193726, 0.4413287937641144, -0.5385014414787292, 1.295823335647583, 0.9117525815963745, 0.15825946629047394, 0.30654671788215637, 1.242412805557251, 0.1997651308774948, 0.16110464930534363, -0.6133598685264587, 0.463742196559906, 0.788954496383667, 0.2926776707172394, -0.21299156546592712, 0.41747841238975525, -0.4588153660297394, 0.3585885763168335, -0.12996937334537506, 0.20258449018001556, 0.6648231148719788, 1.145770788192749, -0.13871413469314575, -0.8380872011184692, 0.5604224801063538, 0.46872419118881226, 0.7634465098381042, 1.3974609375, 0.5710543394088745, 0.2395990788936615, 0.24245746433734894, -0.20353581011295319, -0.26904296875, -0.5464277863502502, 0.589430570602417, -0.10400390625, 0.03779836744070053, 0.28108566999435425, -0.7044912576675415, -0.4598459005355835, -0.21310894191265106, -0.07856163382530212, -0.08260169625282288, 0.5395460724830627, -1.1285247802734375, 1.2597304582595825, 1.119891881942749, -0.6208401918411255, -1.156813383102417, -0.126768559217453, 0.3991071283817291, -0.7891470193862915, 0.4802621603012085, 0.10071739554405212, -0.655961275100708, 0.9515380859375, 0.17385204136371613, 0.5194185972213745, 0.4194101095199585, -0.8535719513893127, -1.064133882522583, 0.5601759552955627, -0.5509220957756042, 1.1903921365737915, 0.02824636548757553, -0.5763314962387085, -1.3338717222213745, 0.5383816957473755, -0.272248774766922, -0.2195505052804947, 0.03338623046875, 1.376727819442749, 0.4393064081668854, 0.1398855298757553, 1.4583083391189575, 0.1615682691335678, -1.9020432233810425, -0.26365339756011963, 1.3012319803237915, 0.2882925271987915, -0.46145394444465637, -0.46594002842903137, 0.4603365361690521, -0.10994544625282288, -0.3575257658958435, -1.328995943069458, 0.10787729173898697, 1.03466796875, 0.0993194580078125, -0.28753721714019775, 0.14408992230892181, 0.01902242749929428, 2.0078125, 1.807692289352417, -0.8921273946762085, -0.7905836701393127, 0.24375534057617188, -1.0720778703689575, -0.5026039481163025, 0.23517081141471863, 0.47606950998306274, 1.016019344329834, -0.19815708696842194, 0.7378610372543335, -0.08369328081607819, -0.9828726053237915, 0.6077223420143127, 0.7357693910598755, 0.25100472569465637, -1.3419846296310425, 0.5446495413780212, 0.12012188136577606, 0.4476136565208435, -0.2747538685798645, -0.7815839052200317, 0.7307809591293335, 0.5832246541976929, -1.2844802141189575, 0.34509748220443726, 0.6597195863723755, -0.27717825770378113, 1.2956918478012085, 0.748521089553833, -0.6959933042526245, 0.41393572092056274, -0.06723491847515106, 0.15516780316829681, -0.7946214079856873, 0.11329063773155212, -0.13442054390907288, -0.4487774074077606, -0.36835187673568726, -0.11064895987510681, 0.4263446629047394, -0.14323483407497406, 0.3257610499858856, -0.3363553583621979, 0.6154221892356873, 0.5508375763893127, 0.33587411046028137, 0.13966251909732819, 0.604248046875, -0.7324406504631042, -0.24538810551166534, -0.6159245371818542, -0.9586087465286255, -0.6730018258094788, 0.9550265073776245, 0.12127450853586197, -0.2713176906108856, -0.5099534392356873, 0.14602133631706238, 0.29709067940711975, -0.634010910987854, -0.7897996306419373, -0.43949654698371887, -0.872802734375, 0.37515494227409363, -0.3127728998661041, 1.1670485734939575, -0.37089774012565613, 1.276267409324646, -0.4999788701534271, 0.43710562586784363, -0.25466039776802063, -0.6809927225112915, 0.2883699834346771, 0.845703125, 0.13047908246517181, 0.03255403786897659, -0.694413423538208, 0.32206374406814575, -0.035508375614881516, 0.10693006962537766, -0.702642560005188, -0.08849275857210159, -0.11763587594032288, 0.7220646739006042, 0.033491868525743484, -0.47998926043510437, 0.6890023946762085, 0.5330622792243958, -1.1274508237838745, -0.7162991762161255, 0.19686801731586456, 0.7239943146705627, -0.8489802479743958, -0.9955491423606873, 0.19925162196159363, -0.901170015335083, -0.5567744374275208, 0.060138996690511703, -0.010751577094197273, -1.064669132232666, -0.03615628927946091, 0.22237923741340637, -1.013014554977417, 0.4337158203125, 0.28409048914909363, -0.1924814134836197, -0.6766780018806458, 0.23965689539909363, -0.512620210647583, 0.3643704950809479, -0.5311549305915833, 0.4681408107280731, -0.4041841924190521, -0.1902700513601303, -0.16810138523578644, 0.44162458181381226, 0.19888187944889069, 0.11343501508235931, -0.2984994649887085, -0.14365093410015106, 0.2834733724594116, -0.33890944719314575, 0.4163677394390106, -0.882240891456604, -0.08715233206748962, -0.576829195022583, -0.47941529750823975, 0.19316688179969788, 0.1980215162038803, 0.527218759059906, -0.4339458644390106, -1.1922513246536255, -1.057692289352417, 0.34820085763931274, -0.39678955078125, -0.05792001634836197, 0.374267578125, -1.378192663192749, -0.8914700746536255, -1.1484750509262085, -0.5377760529518127, 1.458449125289917, -1.071552038192749, -0.07094632834196091, 0.3700115382671356, -0.5017019510269165, -0.6181077361106873, -0.30311936140060425, 0.24583552777767181, -0.36648324131965637, -1.5899094343185425, -0.07598407566547394, -0.9674635529518127, 1.076904296875, 0.741379976272583, 0.3590020537376404, -0.25670477747917175, -0.2581552267074585, 0.26067644357681274, 0.3016515076160431, 0.4030620753765106, -0.03534258157014847, -0.5035063028335571, 1.018291711807251, 0.5792518258094788, -0.8126925230026245, -0.08552903681993484, -0.1407470703125, -1.1249624490737915, 0.8674128651618958, -0.7374173402786255, -0.011338453739881516, -0.8886155486106873, -0.884202241897583, -1.1868239641189575, 1.9456881284713745, 0.17362858355045319, 0.6072810292243958, -0.8647648692131042, -0.4016582667827606, 0.635298490524292, 0.6384371519088745, 1.3777419328689575, -0.5881030559539795, 0.7887620329856873, -1.9261568784713745, -0.6237511038780212, -2.702448844909668, -0.2837430536746979, 0.15017707645893097, 0.8656851053237915, 0.4670504033565521, 1.080397367477417, 1.5134841203689575, 0.3225027322769165, 0.11096015572547913, 0.42079243063926697, 0.47019606828689575, -0.5423208475112915, 1.166485071182251, 0.8109611868858337, -0.060899000614881516, 0.11271080374717712, 1.5731858015060425, 0.788804292678833, 0.21624755859375, 0.6741215586662292, 0.29562729597091675, 0.17739281058311462, 0.49195215106010437, 0.09716796875, -2.308218240737915, -0.43545296788215637, 0.7088247537612915, 0.21314474940299988, -0.32326096296310425, 0.5375319123268127, 1.40576171875, -1.147564172744751, -0.3011615574359894, -0.6281926035881042, -1.061598539352417, -0.1557561457157135, 0.38075608015060425, -0.828538179397583, -0.20875431597232819, -1.069260835647583, 0.9086726307868958, -0.05495394021272659, -0.19303542375564575, 1.236891508102417, -0.35735613107681274, -0.46880868077278137, -0.29107666015625, 1.4042282104492188, 0.9587590098381042, 0.0003955914289690554, -0.43672531843185425, -0.9037898182868958, -0.5758761167526245, -0.18509380519390106, 0.11703725904226303, 0.7795785665512085, 0.38360595703125, -0.37539908289909363, 0.3785259425640106, -1.052659273147583, -0.5718712210655212, -0.07829871773719788, 0.56365966796875, -0.5928532481193542, 0.27426382899284363, 1.2768179178237915, -0.20423771440982819, 0.5302523374557495, 1.4888070821762085, 1.2454177141189575, 0.09628883004188538, -0.9642239809036255, -0.769822359085083, -0.01664264313876629, -0.38238054513931274, -1.600811243057251, 0.3656475245952606, 0.12626999616622925, -0.5908437967300415, 1.131854772567749, -0.22973735630512238, 0.6808882355690002, -0.30669137835502625, -0.1837429702281952, -0.32591599225997925, -0.26666611433029175, 1.5058969259262085, 0.4558950662612915, -0.9868351817131042, -0.729905366897583, -0.5292874574661255, -0.6177180409431458, -0.46808332204818726, -0.511854887008667, 0.11345027387142181, -0.822922945022583, 0.20160850882530212, 0.1484609693288803, -0.8695913553237915, 1.7961989641189575, 0.26223990321159363, 0.014226472936570644, -0.4139961898326874, -0.5873835682868958, -1.6868990659713745, 0.173552006483078, -0.3437406122684479, 0.025951679795980453, -0.3703199625015259, -0.05563589185476303, -0.18557503819465637, 0.7384220957756042, -0.5587698221206665, 1.2847055196762085, -0.19717994332313538, 0.662358820438385, 0.6656869649887085, 0.8484919667243958, 0.35787612199783325, 0.7266470193862915, -0.5383253693580627, -1.132906436920166, -0.45407339930534363, 0.21859213709831238, 1.070725679397583, 0.7655733823776245, 0.876662015914917, -0.3749706447124481, 0.8562411069869995, -0.48681169748306274, -0.5318040251731873, -1.380859375, -1.412935733795166, 0.15692080557346344], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.

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

{'search_vector': [0.6217122673988342, 1.1413748264312744, -2.5885183811187744, -1.0757359266281128, 1.8927175998687744, 0.13157108426094055, -0.4788927435874939, 0.4906180202960968, 0.6081629991531372, -0.9383109211921692, 0.1593845933675766, 0.50860595703125, 1.0185906887054443, 0.2243456095457077, 0.02422584779560566, -0.5241622924804688, 1.1780482530593872, -0.9276123046875, -0.3767133355140686, -0.0769260972738266, -0.3139103353023529, -1.0175607204437256, -1.0105677843093872, -0.3949715793132782, 2.2960031032562256, 0.15833227336406708, -0.1152866929769516, 0.69195556640625, -2.097935199737549, 0.0999516099691391, -0.5046212077140808, -0.2367204874753952, 0.9245387315750122, 0.0735669806599617, -0.130386620759964, -0.0461447574198246, -0.8733869194984436, -0.38568115234375, -0.7943507432937622, -0.2560184895992279, -0.3746097981929779, -0.7884259819984436, 0.2828369140625, 0.0422145314514637, 1.1461704969406128, 0.014238630421459675, 0.8343287706375122, 0.4827532172203064, 0.8305162787437439, -1.3540736436843872, 0.5089372992515564, -1.3069894313812256, 0.12200593948364258, -0.4282444417476654, 1.4024134874343872, 0.715118408203125, -0.5813849568367004, 0.8679373860359192, -0.5657173991203308, -0.9399239420890808, 0.8629586100578308, 1.0223388671875, 0.2169581800699234, 0.5913347601890564, 1.4195730686187744, -0.045412879437208176, -1.2574986219406128, 0.92578125, -0.4554001986980438, -0.1203744038939476, 1.0771734714508057, 0.0615561343729496, -0.2007359117269516, 0.6020965576171875, -1.1269181966781616, -0.2104731947183609, 0.2578059732913971, -1.2470703125, 0.0885402113199234, 0.6436549425125122, -0.37112098932266235, -0.7833775281906128, -0.3274405300617218, -1.2694963216781616, 0.436187744140625, 0.5145002007484436, -0.63330078125, 1.0246374607086182, -0.9205583930015564, 1.2986013889312744, 0.9412580132484436, -0.4124930202960968, 1.0686384439468384, 0.19524820148944855, -1.7954798936843872, 0.8218209147453308, -0.1443350613117218, 0.5565839409828186, -0.5449393391609192, -0.1230948343873024, -0.4898158609867096, 0.10533087700605392, -0.31065478920936584, -0.47974613308906555, 0.5212053656578064, 1.0106724500656128, -0.3438083231449127, 1.3355189561843872, 0.007110595703125, -0.3627515435218811, -1.0225141048431396, 1.4270542860031128, -0.5930731892585754, -0.8339897990226746, 0.15576063096523285, -0.3297031819820404, 1.1315220594406128, 0.1874258816242218, 0.2089167982339859, 1.4633091688156128, 0.4984087347984314, -0.6910487413406372, -0.23021316528320312, 0.9952043890953064, -0.1144561767578125, -0.110321044921875, -0.2791707217693329, 0.02400861494243145, 0.3442295491695404, -0.7909894585609436, -0.5914464592933655, -0.7728968858718872, -0.5705016255378723, -1.1476701498031616, 1.027921438217163, -0.1222730353474617, -0.4498181939125061, -0.5172467827796936, -0.3280399739742279, -0.2376600056886673, 0.7650321125984192, -0.3983241617679596, 0.0945238396525383, -0.594024121761322, 0.8941999077796936, -0.0889652818441391, 0.8096051812171936, 0.4324863851070404, -0.2485787570476532, 0.2614048421382904, -0.7532610297203064, 0.9529410600662231, 0.4712088406085968, 0.3823544681072235, 1.0703648328781128, -0.6226844787597656, -0.1944187730550766, -0.24010194838047028, 0.02828107587993145, 0.9344220757484436, 1.4236886501312256, 0.2603236734867096, -0.0706416517496109, 1.6820591688156128, 0.3915688693523407, -0.43804931640625, -0.45015063881874084, 0.9198695421218872, 0.6550641655921936, 1.0052839517593384, -0.4998149871826172, -0.4369768500328064, 0.6024584174156189, -0.3253462612628937, 0.3459385335445404, 0.1512974351644516, 1.385498046875, -0.634705662727356, -0.048914771527051926, -0.4621211588382721, -0.021332332864403725, -0.8804888129234314, 0.43642425537109375, 0.6335187554359436, -0.0810416117310524, -0.2649601399898529, 0.544952392578125, -0.21948787569999695, -1.8771275281906128, -2.1866629123687744, -0.16980865597724915, 0.3916015625, -0.4301539957523346, -0.3718741238117218, -1.0276925563812256, -0.3016880452632904, 0.7060753703117371, -0.9474051594734192, 0.9030936360359192, -0.2551792562007904, 0.7793563008308411, 0.2158333957195282, -0.0466700978577137, 0.0227530337870121, -1.0546875, 0.6296822428703308, -0.8095847964286804, -0.2420087605714798, -0.0773250013589859, -0.19055011868476868, 1.363037109375, -0.11941201239824295, -1.09912109375, 0.6156267523765564, -0.5601065754890442, -0.02234540693461895, -0.1520908921957016, -0.39400917291641235, -0.8880876898765564, -0.3485586941242218, 1.155458688735962, 0.12713623046875, -0.03437580540776253, -0.9849853515625, -0.4351893961429596, 0.048567090183496475, -1.4179774522781372, 0.1711447536945343, -0.1017085462808609, -0.31162479519844055, 0.5085776448249817, -1.4986048936843872, 0.7949044108390808, -0.1010349839925766, 0.6540418267250061, 0.4260190427303314, -0.10675648599863052, 0.537322998046875, 0.04672568291425705, 0.1508353054523468, 0.0243061613291502, 1.8749302625656128, -0.6466151475906372, 0.3660213053226471, -1.060546875, -0.6623557209968567, -0.32561439275741577, -1.3865443468093872, -0.3254568874835968, 0.09035710245370865, -0.8886370062828064, 0.1272125244140625, 0.9245539903640747, -0.47027587890625, 0.14018331468105316, -1.0272434949874878, 0.3046221137046814, 0.0292347501963377, 0.045999255031347275, -0.181793212890625, 0.0409393310546875, 0.24567069113254547, 0.0914568230509758, -0.7086530327796936, -0.6336495280265808, -1.2271009683609009, 0.5125035047531128, 0.3247440755367279, 0.13604190945625305, -0.2308371365070343, 0.1886858195066452, 0.08095387369394302, -0.2688380777835846, 0.0276620052754879, 1.1505998373031616, -0.2476457804441452, 0.21170343458652496, 0.025255510583519936, 0.28501564264297485, 0.7773350477218628, -0.4302956759929657, -0.35625022649765015, -0.5048392415046692, 0.6835578083992004, 0.4241267740726471, 0.4174630343914032, 0.6644287109375, 0.18183572590351105, 0.3461633324623108, -0.2400253862142563, 1.0018136501312256, -0.7598702311515808, -1.7569929361343384, 0.7255946397781372, -0.00783647783100605, 0.7802385687828064, 1.4518693685531616, -0.6904820203781128, 1.2513951063156128, -0.7182028889656067, -0.52215576171875, 0.0706699937582016, 0.7563754320144653, 0.3521990180015564, -0.2394866943359375, -0.6482020616531372, 1.5570242404937744, -0.3118852972984314, 0.0659702867269516, -0.2335553914308548, -0.9962332844734192, -0.1686335951089859, -0.2747454047203064, 1.4363490343093872, -0.5655430555343628, 1.1481759548187256, 0.9813407063484192, 0.18185779452323914, 0.7171282172203064, -0.004187447484582663, 0.45849719643592834, -0.5398472547531128, -0.1497126966714859, 0.0205361507833004, 0.5979090929031372, -0.2475997358560562, 0.0412466861307621, 0.4816109836101532, 0.1815425306558609, -0.5473065972328186, 0.1919424831867218, -0.06517791748046875, 0.2005397230386734, -0.7660239338874817, -0.27120643854141235, -0.6148899793624878, -0.34055382013320923, 0.20353341102600098, 0.6804689764976501, 0.6559883952140808, 0.6619524359703064, -0.7677241563796997, 0.3414393961429596, -0.4767826497554779, -0.012864180840551853, -0.2698187232017517, -0.9181256890296936, -0.14162643253803253, 0.8193621039390564, 0.46551513671875, -0.4085213840007782, 1.2301548719406128, 0.554229736328125, -0.1694532185792923, 0.48647743463516235, -0.5806961059570312, 1.2905622720718384, 1.234619140625, 0.1970345675945282, 0.4530465304851532, 1.1958705186843872, -0.0450265072286129, 0.1689409464597702, -0.3198694586753845, 0.2997390329837799, 0.8433903455734253, 0.4740338921546936, -0.4958670437335968, 0.41936928033828735, -0.5224391222000122, 0.5394788384437561, -0.1167646124958992, 0.1841823011636734, 0.6916323900222778, 1.1616560220718384, -0.3977704644203186, -0.8049466013908386, 0.4496547281742096, 0.3322012722492218, 1.0091902017593384, 1.4300363063812256, 0.9016985297203064, 0.12072866410017014, 0.064361572265625, -0.0599365234375, -0.3929050862789154, -0.3888375461101532, 0.3228166997432709, -0.207000732421875, 0.0244260523468256, 0.3240312933921814, -0.9994670152664185, -0.7036612629890442, -0.0897957906126976, 0.11167199164628983, -0.0795942023396492, 0.6581639051437378, -0.9966343641281128, 1.2146867513656616, 1.0380162000656128, -0.4384547770023346, -1.0627615451812744, -0.0735539048910141, 0.6311558485031128, -0.6487448811531067, 0.2440316379070282, 0.131744384765625, -0.6393007636070251, 0.9355000257492065, 0.2999136745929718, 0.21942125260829926, 0.21707399189472198, -0.7827191948890686, -1.2732456922531128, 0.5643178224563599, -0.3868778645992279, 1.1019113063812256, -0.0198080874979496, -0.6447361707687378, -1.1074578762054443, 0.4614715576171875, -0.2726004421710968, -0.1487644761800766, 0.0401960089802742, 1.1624232530593872, 0.5139666795730591, 0.0245492123067379, 1.407958984375, 0.1369672566652298, -1.7300502061843872, -0.2662266194820404, 1.1896798610687256, 0.3107087314128876, -0.2679661214351654, -0.6052322387695312, 0.588134765625, -0.01729910634458065, -0.5575997233390808, -1.1853898763656616, 0.09502629190683365, 0.9286237359046936, 0.0837009996175766, -0.4602072536945343, 0.0752890482544899, 0.010046550072729588, 2.1128628253936768, 1.6810128688812256, -0.4579511284828186, -0.7105843424797058, -0.08860887587070465, -1.1308854818344116, -0.7111119031906128, 0.1028180792927742, 0.6029225587844849, 0.7937883734703064, -0.006766182836145163, 1.1045793294906616, -0.0021013531368225813, -1.1508615016937256, 1.0427595376968384, 0.6609889268875122, 0.016773223876953125, -1.2935267686843872, 0.7838309407234192, 0.0095683503895998, 0.6300486326217651, -0.02329472079873085, -0.7777535319328308, 0.7390550971031189, 0.4634595513343811, -1.4436384439468384, 0.35767582058906555, 0.8809989094734192, -0.1501377671957016, 1.1657453775405884, 0.7482474446296692, -0.6531153917312622, 0.30568477511405945, 0.0356706902384758, 0.2719247043132782, -0.6791643500328064, -0.1989157497882843, -0.3120618462562561, -0.4761526882648468, -0.3699253499507904, -0.1026349738240242, 0.2899344265460968, -0.0056631905026733875, 0.4625680148601532, -0.4907139241695404, 0.5934012532234192, 0.5782994031906128, -0.12147249281406403, 0.11274828016757965, 0.3032929599285126, -0.3868931233882904, -0.4233136773109436, -0.5556510090827942, -0.6082283854484558, -0.3581564724445343, 1.1270010471343994, 0.1721583753824234, -0.2575123608112335, -0.3600981533527374, 0.3351549506187439, 0.1739916056394577, -0.6063101887702942, -1.0955984592437744, -0.5359758734703064, -0.9084821343421936, 0.1108834370970726, -0.3845981955528259, 1.3547712564468384, -0.37935203313827515, 1.1425257921218872, -0.5283780694007874, 0.5119541883468628, -0.1888558566570282, -0.6203133463859558, 0.34303393959999084, 0.7518310546875, 0.11273302137851715, 0.189300537109375, -0.9528546929359436, 0.24542509019374847, -0.2199619859457016, 0.061102185398340225, -0.5720999836921692, 0.1452854722738266, -0.2295510470867157, 0.6342800855636597, 0.2786927819252014, -0.429871141910553, 0.6437639594078064, 0.4827052652835846, -1.0744978189468384, -0.6477323174476624, 0.1136670783162117, 0.5719996690750122, -0.7986885905265808, -1.0235682725906372, 0.4212319552898407, -0.9763706922531128, -0.6711011528968811, 0.1351318359375, 0.3075779378414154, -1.0772225856781006, -0.1748003214597702, 0.3852669894695282, -0.9666573405265808, 0.0007416861481033266, 0.4252226650714874, -0.44198718667030334, -0.69781494140625, 0.417206346988678, -0.2773045003414154, 0.2052001953125, -0.5615452527999878, 0.7958461046218872, -0.4899553656578064, 0.0432477667927742, -0.18100956082344055, 0.5371748208999634, 0.3535194396972656, 0.4450748860836029, -0.3836168646812439, -0.3634556233882904, 0.0967581644654274, -0.5958600640296936, 0.2962602972984314, -0.7538059949874878, -0.5330635905265808, -0.4850572943687439, -0.4340732991695404, -0.004212515894323587, 0.0476728156208992, 0.5475856065750122, -0.4181431233882904, -1.3604212999343872, -1.0649064779281616, 0.21350915729999542, -0.3842424750328064, -0.1616777628660202, 0.5310551524162292, -1.0566056966781616, -1.0477818250656128, -0.9500819444656372, -0.4041944146156311, 1.6682783365249634, -1.017333984375, -0.3270438015460968, 0.2726985514163971, -0.4301496148109436, -0.5662493109703064, -0.4048374593257904, 0.3710763156414032, -0.14397157728672028, -1.3262678384780884, -0.1036464124917984, -0.8526872992515564, 0.9528459906578064, 0.5729500651359558, 0.5656084418296814, -0.7597264051437378, -0.3140825629234314, -0.17554447054862976, 0.2578125, 0.5139683485031128, 0.1259416788816452, -0.5930110216140747, 0.6265520453453064, 0.7957240343093872, -0.4582563042640686, -0.167816162109375, -0.1238141730427742, -0.8908866047859192, 0.8185948133468628, -0.8347298502922058, -0.0847909078001976, -0.8813389539718628, -0.6495034098625183, -1.2750070095062256, 1.5350167751312256, -0.2487836629152298, 0.6935904622077942, -0.7735421061515808, -0.3734550476074219, 0.34830763936042786, 0.7231009602546692, 1.4046804904937744, -0.6275373101234436, 1.1486467123031616, -1.8335658311843872, -0.6234261393547058, -2.4805386066436768, -0.3278350830078125, 0.29652294516563416, 0.9080985188484192, 0.3912876546382904, 1.0831822156906128, 1.7954798936843872, 0.3066057562828064, -0.45767349004745483, 0.3572365939617157, 0.1444266140460968, -0.2230486124753952, 1.0378068685531616, 0.9713570475578308, -0.3003474771976471, 0.10787364095449448, 1.4673374891281128, 0.664702296257019, 0.7764325737953186, 0.6500701904296875, 0.407744824886322, 0.31609290838241577, 0.1995217502117157, 0.1520036906003952, -2.114536762237549, -0.307662695646286, 0.6109575629234314, 0.1774946004152298, -0.7164524793624878, 0.3870914876461029, 1.1785017251968384, -1.1341203451156616, -0.1846051961183548, -0.5611855387687683, -0.9438127875328064, 0.0035814556758850813, 0.5484967827796936, -0.9435686469078064, -0.0556073859333992, -0.8033229112625122, 0.7553885579109192, -0.09458936750888824, -0.2826429009437561, 0.9263043999671936, -0.3306143581867218, -0.4986359775066376, -0.3537510335445404, 1.1586827039718628, 1.0692662000656128, -0.1195569708943367, -0.5075421929359436, -0.9263654351234436, -0.7611781358718872, -0.393310546875, 0.038457054644823074, 0.7458583116531372, 0.056365966796875, -0.1753147691488266, 0.30726295709609985, -1.1340157985687256, -0.7553275227546692, 0.22635868191719055, 0.30296462774276733, -0.3843165934085846, 0.0801173597574234, 1.1163853406906128, -0.3627777099609375, 0.7310267686843872, 1.4315359592437744, 1.2998046875, 0.06583677232265472, -0.8492823839187622, -0.75, -0.02414376474916935, -0.5545136332511902, -1.6426478624343872, 0.3753683865070343, 0.055964503437280655, -0.9183785319328308, 1.3552072048187256, -0.34957870841026306, 0.7576380968093872, -0.16346414387226105, -0.1646161824464798, -0.016338348388671875, -0.25574302673339844, 1.4101039171218872, 0.6225804090499878, -0.8441597819328308, -0.4801679253578186, -0.5977347493171692, -0.5717980265617371, -0.45432281494140625, -0.3907819390296936, 0.16327176988124847, -0.7368861436843872, 0.3730316162109375, -0.0645926371216774, -0.9075404405593872, 1.6051896810531616, 0.5103541612625122, -0.2794145941734314, -0.10628563910722733, -0.5116860270500183, -1.8427734375, 0.1231406107544899, -0.536865234375, 0.1101248636841774, -0.3606327474117279, 0.1464407742023468, 0.16725921630859375, 0.3614175021648407, -0.5420270562171936, 1.2445939779281616, -0.0388532355427742, 0.812255859375, 0.6797965168952942, 0.70611572265625, 0.2795671820640564, 0.6780613660812378, -0.6487023234367371, -1.1862515211105347, -0.3754010796546936, 0.2707868218421936, 1.1625279188156128, 0.7201331257820129, 0.8279004693031311, -0.0014288766542449594, 0.6140790581703186, -0.3416748046875, -0.5819963812828064, -1.3540388345718384, -1.3472377061843872, -0.007647923193871975], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (FastAPI | uses | Pydantic | request | validation)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Authentication | uses | dependency | injection | patterns | FastAPI)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.

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

{'search_vector': [1.4135091304779053, 2.0301105976104736, -3.121614694595337, -0.5531005859375, 0.9627441167831421, -0.94287109375, 1.1047648191452026, -0.8668050169944763, -0.1089540496468544, 0.03737451136112213, 2.0745441913604736, -0.02582600899040699, 1.2944661378860474, 0.5926716923713684, 0.7611653804779053, 0.5204833745956421, 0.04539591446518898, -0.6856099367141724, -0.3882995545864105, 0.3583821654319763, 0.3543701171875, -0.12849120795726776, -1.2808918952941895, 0.08203252404928207, 1.5150904655456543, 0.571044921875, 0.6043945550918579, -0.31878459453582764, -1.5909504890441895, -0.5919637084007263, 1.9202148914337158, -0.07519938051700592, 0.02188720740377903, -0.630200207233429, -0.6239873170852661, -0.47233885526657104, 1.5046712160110474, -0.23675537109375, -1.311425805091858, 0.26159870624542236, 0.07469279319047928, -0.0731201171875, 1.025390625, 0.02071380615234375, 0.8210204839706421, -0.13344725966453552, 1.159082055091858, 0.3809407651424408, 0.5725870728492737, -0.7091287970542908, 0.9939982295036316, 0.2038777619600296, -0.14566752314567566, -1.4267903566360474, 1.2046549320220947, 0.5489501953125, -1.869726538658142, 1.4763672351837158, -0.6757161617279053, -0.39739686250686646, 1.6420247554779053, 0.2711717486381531, -0.6821879148483276, 1.3692423105239868, 0.9959981441497803, 0.7213541865348816, -0.6785725951194763, 0.726959764957428, -0.6484944820404053, -0.5075276494026184, -0.25951969623565674, -0.1762542724609375, -0.5107503533363342, -0.6436197757720947, 0.3762369751930237, 0.3769124448299408, -1.072167992591858, -1.0878417491912842, -0.01520690880715847, 0.5945149660110474, -0.15992431342601776, 0.560070812702179, 1.3204426765441895, -0.2994323670864105, 1.184052586555481, 0.6015538573265076, 0.8811442255973816, 0.0729573592543602, -0.7615610957145691, 1.3133625984191895, -0.27164509892463684, -0.472747802734375, 0.618334949016571, -0.26659852266311646, -0.25679320096969604, 0.17396749556064606, -0.9132853150367737, 1.1219075918197632, -0.5190674066543579, 0.02483673021197319, -0.1578877717256546, 0.933673083782196, 0.4464457333087921, -0.7559814453125, -0.16785481572151184, 0.5192505121231079, 0.21552200615406036, 0.4477885067462921, 0.8062337040901184, -0.2312164306640625, 0.18741658329963684, 0.17623494565486908, 0.46625468134880066, -1.0774089097976685, -1.0194823741912842, -1.597070336341858, 1.8947265148162842, 0.1416524201631546, 0.28735604882240295, 0.8191243410110474, -0.5421345829963684, -0.1912134736776352, -0.647900402545929, 1.4566080570220947, -0.8257283568382263, 1.1597920656204224, -1.2877603769302368, 0.588958740234375, 0.4049479067325592, -1.0321125984191895, -0.02712097205221653, -1.5385416746139526, -1.4243327379226685, -0.04241231456398964, -0.27727967500686646, 0.582263171672821, -0.894030749797821, -0.9709025025367737, 0.14359131455421448, 0.7135660648345947, 0.02669881097972393, 0.29112955927848816, 0.8967071771621704, -0.3527018129825592, -0.6460489630699158, 0.10637614130973816, 0.8989583253860474, -0.348226934671402, 0.14313150942325592, -0.14533589780330658, -0.02090250700712204, 1.0087401866912842, -0.14266763627529144, 1.0064778327941895, -0.16336263716220856, -0.6850667595863342, 0.06348521262407303, 0.5272135138511658, 0.2786906063556671, 0.8340250849723816, 0.6480875611305237, -0.02452646940946579, -1.51611328125, 0.8182291388511658, -1.2513997554779053, -0.6735432744026184, 0.14317016303539276, 1.7014974355697632, -0.02343444898724556, 0.8305908441543579, -1.4632161855697632, -1.4580403566360474, 0.09312617033720016, -0.8460042476654053, 1.1986653804779053, 0.05450846254825592, 0.7736734747886658, -0.23082174360752106, 0.430734246969223, -0.2545674741268158, -0.6228190064430237, -0.933520495891571, 0.4305664002895355, 1.5218099355697632, -0.9177083373069763, -0.3322815001010895, 0.3878641724586487, 0.504418671131134, -0.2855015993118286, -0.6264282464981079, 1.2234050035476685, 0.2764383852481842, -1.3442057371139526, -0.7289673089981079, -0.7921793460845947, 0.08599650114774704, 2.048111915588379, -0.28601887822151184, 1.0676106214523315, -0.681530773639679, -1.0050455331802368, -0.2723347842693329, -1.3176432847976685, -0.8509114384651184, 0.13221333920955658, -0.33779704570770264, 0.712939441204071, 0.8159016966819763, -0.2157796174287796, 0.34773966670036316, 1.425268530845642, 0.12983804941177368, -0.9524739384651184, 0.22325795888900757, 1.619726538658142, -0.3956705629825592, -0.11618448793888092, -0.4287058413028717, 0.16599121689796448, 0.31244710087776184, 0.8944905400276184, -1.0831868648529053, -0.27859801054000854, -0.7363668084144592, -0.04689941555261612, -0.8622721433639526, -1.519140601158142, -1.2219727039337158, -0.12770487368106842, 0.6552164554595947, 0.09782104194164276, -1.1605631113052368, -0.6299804449081421, 0.2935791015625, -0.1858421266078949, 0.3944539427757263, 0.13653869926929474, 1.005926489830017, 0.4679809510707855, -0.7849446535110474, -0.4266611635684967, -0.4751332700252533, -0.4960286319255829, 0.6037139892578125, -1.3809244632720947, 0.32927143573760986, 0.04642028734087944, -0.8978230953216553, -0.6335774660110474, 1.3291015625, -0.10128987580537796, 0.15770263969898224, 0.3156372010707855, 0.5217122435569763, 0.06414413452148438, -0.36457520723342896, -0.5520385503768921, 0.39638087153434753, -0.12482299655675888, -0.913525402545929, 0.8040364384651184, 0.4191548526287079, 1.1354024410247803, -0.5093780755996704, 0.06217346340417862, -0.4494791626930237, 0.6224772334098816, 0.3991999328136444, -0.08086191862821579, -0.42633259296417236, 0.8753906488418579, 0.8305684328079224, 0.11969400942325592, 1.4041016101837158, 0.7796386480331421, 0.2123158723115921, -0.0700836181640625, -0.6461710333824158, 0.07054748386144638, 1.2597981691360474, -0.3620442748069763, -1.061767578125, -0.10801289975643158, -0.14962667226791382, -0.39714354276657104, 0.522864043712616, 0.01542561873793602, -0.14515991508960724, 0.12124837189912796, 0.6052774786949158, 0.6290506720542908, -0.10139159858226776, -0.5771830081939697, 0.28432515263557434, 0.6268025636672974, -0.04097289964556694, 0.90423583984375, 0.10903117060661316, 0.46515706181526184, -0.4914998412132263, 0.3574788272380829, -0.5135846734046936, 0.6754109859466553, 1.1165812015533447, 0.4987121522426605, 0.2874644100666046, 0.2569168210029602, -0.35124003887176514, 1.3967448472976685, 1.1390950679779053, -0.1560465544462204, 0.1296740174293518, -1.0746581554412842, 0.12874451279640198, -0.703967273235321, 0.5881592035293579, 1.3011068105697632, 0.6403523683547974, 0.6954182982444763, 0.6782115697860718, 0.4654296934604645, -0.10291340947151184, -0.23560892045497894, 0.11428757011890411, 0.3577474057674408, 0.9778971076011658, -0.907421886920929, 0.2661193907260895, 0.47026723623275757, 0.46882325410842896, 1.0056477785110474, -0.40563151240348816, 0.9896199703216553, -1.39892578125, -0.834057629108429, 0.5294942259788513, 0.5712077021598816, 0.6959086060523987, 0.538745105266571, -0.16042886674404144, 1.301904320716858, -0.8448384404182434, 1.4085286855697632, -1.9260417222976685, -0.6272481083869934, 0.6050699949264526, -0.7108398675918579, 0.4152872860431671, 0.5811360478401184, -0.16530151665210724, -0.8628092408180237, -0.02666524238884449, -0.7405924201011658, 0.3781494200229645, 0.6396728754043579, -0.05786437913775444, 0.6120239496231079, 0.8055338263511658, -0.5350138545036316, 0.2732584774494171, 0.623181164264679, -0.3346211612224579, 0.3404581844806671, 0.5997899174690247, -0.1341094970703125, 0.08170245587825775, 0.41611531376838684, -0.44351398944854736, -0.3785766661167145, -0.18454183638095856, -0.5136556029319763, -1.31494140625, -0.3774271607398987, 0.26713258028030396, -0.3974777162075043, 0.28820598125457764, -1.6197916269302368, -0.17419026792049408, -0.629687488079071, 0.911633312702179, 0.2820017635822296, -1.0138753652572632, 0.4054606258869171, 0.4298543334007263, -0.2790616452693939, -1.2581461668014526, -0.3930094540119171, -0.636425793170929, 0.32596078515052795, -0.46499836444854736, 0.2721496522426605, -2.2408204078674316, -0.6959187984466553, 0.8921111822128296, -0.1310628205537796, -0.3915293514728546, 0.7209228277206421, 0.2998825013637543, 0.9896606206893921, 1.4195963144302368, -1.2627604007720947, -0.3204294741153717, -0.5836018919944763, -0.932586669921875, -0.01906433142721653, -0.5400227904319763, -0.8831034302711487, -0.45214030146598816, 0.5550130009651184, -0.09439188987016678, -0.25202077627182007, -0.07046101987361908, -0.5596455931663513, -0.04071756824851036, -0.00923309288918972, 0.13884684443473816, 0.30121663212776184, -0.30890196561813354, 0.44525146484375, -0.00402781181037426, 0.05093688890337944, 0.5287841558456421, 0.002506510354578495, -0.3142659366130829, -0.35279542207717896, 1.0431965589523315, 0.40050047636032104, 1.362402319908142, 0.15051370859146118, -1.1260579824447632, 0.23908284306526184, 0.5024454593658447, 0.5707356929779053, -1.4124186038970947, 0.4220540225505829, -0.7960881590843201, -0.1617584228515625, -0.014109293930232525, -0.1643574982881546, 0.3003552258014679, 0.12988179922103882, -0.5447590947151184, -0.43968912959098816, -0.17552897334098816, -0.22563476860523224, 2.1513020992279053, 0.7119466066360474, -0.372650146484375, -0.15606485307216644, -0.35473302006721497, 0.68096923828125, 0.12983602285385132, -0.2485295683145523, 0.08655191957950592, 1.2148762941360474, -0.7217875123023987, -0.36877238750457764, 0.6335123777389526, 1.4395182132720947, 0.7969278693199158, 0.2738580107688904, 1.486181616783142, -1.905859351158142, 0.14521688222885132, 0.8762654662132263, 0.862011730670929, 1.5392252206802368, 0.3261871337890625, 0.22141113877296448, 0.8370524048805237, -1.18408203125, -0.7209838628768921, 0.5605245232582092, -0.5817321538925171, -0.8158203363418579, 0.5789225101470947, -0.267425537109375, -0.13776499032974243, 0.19484660029411316, 1.3202310800552368, -0.7167826294898987, -0.29954400658607483, -0.29582881927490234, -0.8549641966819763, -0.3067057430744171, 0.5677255988121033, 0.4970051944255829, -0.9939145445823669, 0.8166829347610474, -0.14743448793888092, 0.6702433228492737, 0.34161579608917236, -0.24932454526424408, 1.2785969972610474, 0.7464029788970947, 0.5999511480331421, 0.6727091670036316, 0.1763160675764084, 0.10913289338350296, -0.06124979630112648, -0.01977030374109745, 0.4875229001045227, 0.36197203397750854, -1.1616536378860474, 0.5515055060386658, -0.1747792512178421, 0.798327624797821, -0.987438976764679, -0.3084675967693329, 0.5683431029319763, 0.31605225801467896, 0.9476481080055237, 1.3523112535476685, 0.35089924931526184, 0.25696614384651184, -0.8011556267738342, 0.8582682013511658, -0.4185546934604645, -0.6302465796470642, -0.5028320550918579, -0.11827494204044342, -0.8906494379043579, -0.3415730893611908, -1.0422648191452026, -1.599218726158142, -0.7096140384674072, 0.16229452192783356, -0.1262715607881546, 0.7550944089889526, -0.7473673224449158, -0.5115274786949158, 0.4430190920829773, -0.9508138298988342, -0.9306966066360474, -0.21560464799404144, 0.06392008811235428, -0.568798840045929, 0.08586018532514572, 1.2933145761489868, 0.7045572996139526, 0.3427932858467102, -0.08569590002298355, 0.18937581777572632, 0.41997069120407104, 0.6130076050758362, -0.993603527545929, -0.8823567628860474, -0.16084188222885132, -1.2754557132720947, -1.7611979246139526, 0.9473551511764526, -1.0160807371139526, -0.05340982973575592, -0.5368026494979858, 0.5073812007904053, 0.0953776016831398, 0.25794270634651184, 0.4533650577068329, -0.3293505311012268, -1.1375000476837158, 0.5837554931640625, 0.41719409823417664, 1.4778971672058105, 0.20680440962314606, 0.1691233366727829, -2.0616536140441895, -0.08239339292049408, -0.548266589641571, -0.30865591764450073, 0.9010986089706421, 0.04266764223575592, -0.36345621943473816, 0.15520299971103668, 0.6577962040901184, 0.5303194522857666, -0.4714202880859375, -0.4272867739200592, -0.648590624332428, -0.7079326510429382, -0.839550793170929, 0.20967203378677368, -0.510449230670929, 0.6782613396644592, 0.35948243737220764, -0.16510009765625, 0.26720887422561646, -0.8317098021507263, -0.21740418672561646, -0.6904215216636658, -0.6826547980308533, -0.29655253887176514, -0.586499035358429, -0.152149960398674, -1.324743628501892, -0.2037251740694046, 0.3876993954181671, -0.8810908198356628, -0.5961832404136658, -0.9572916626930237, -0.1813512146472931, -0.3924880921840668, 0.01055297814309597, 0.7562581300735474, -0.828015148639679, 0.591473400592804, 1.4320474863052368, -0.19942982494831085, 0.9621419310569763, -0.09381917119026184, -0.08659668266773224, 0.9734293818473816, -0.6510213017463684, 0.31391462683677673, -0.02637532539665699, 0.36971843242645264, 0.049740981310606, 1.0611897706985474, -0.740893542766571, -1.090600609779358, 0.5460164546966553, 0.049560546875, -0.90380859375, 0.6684020757675171, -1.0490233898162842, 1.2418293952941895, -0.03085123747587204, -0.16411133110523224, -1.1829183101654053, 0.45232799649238586, -0.40672582387924194, 0.5038614869117737, 0.02819010429084301, -1.2592122554779053, -1.5076497793197632, -0.6328043341636658, 0.9564290642738342, -0.8911051154136658, 0.17393697798252106, 0.5986673831939697, 0.19481810927391052, 1.2955403327941895, 0.1906750649213791, -0.4223887026309967, -0.16913655400276184, 0.6341588497161865, -0.48304036259651184, 0.7462850213050842, -0.0890950858592987, 0.7905517816543579, -0.7430012822151184, 1.1463297605514526, 0.49819743633270264, -0.06777496635913849, 0.4983011782169342, 0.13613484799861908, 0.4500488340854645, 0.8434407711029053, -0.4021759033203125, -0.08392028510570526, -0.10961507260799408, 0.6819498538970947, 0.534802258014679, 0.6608723998069763, 0.007710265927016735, 0.928814172744751, -0.07961832731962204, 0.06494140625, -0.16432367265224457, -0.8333495855331421, -0.3852895200252533, 0.4300130307674408, 0.5517415404319763, -1.3422200679779053, -1.0247883796691895, 1.2005696296691895, 0.20493978261947632, 1.0715495347976685, 1.0889322757720947, -0.8236002326011658, 0.3448893129825592, 0.04973449558019638, -0.09452514350414276, 0.7645223140716553, -0.7079396843910217, -0.8354654908180237, -0.605224609375, -0.32335203886032104, -0.7157837152481079, 0.5432820916175842, -0.4328104555606842, -0.7222249507904053, -0.7295491695404053, -0.3865397274494171, 0.261984258890152, 0.14546304941177368, 0.2945495545864105, -0.5120658874511719, 0.732983410358429, -0.1456197053194046, 0.4147232174873352, 0.10612538456916809, 0.2265983521938324, 0.24300333857536316, 1.6528971195220947, -0.10811831057071686, 0.4949808716773987, 0.6013712286949158, -0.731433093547821, 0.12520751357078552, -1.0578124523162842, -1.5438802242279053, -0.3692667782306671, -0.5566731691360474, -0.15064696967601776, 0.08676859736442566, 0.20286865532398224, -0.7250305414199829, -1.4597656726837158, 0.08680012822151184, -0.2400360107421875, 1.0934244394302368, -0.2509572207927704, -0.5892333984375, -0.3078972101211548, 0.24915364384651184, -0.8469156622886658, 0.6042836308479309, -0.7482401728630066, -0.41322022676467896, -0.5144978761672974, 0.2625081241130829, -0.9437337517738342, -0.8709879517555237, 1.1479980945587158, -1.3182209730148315, 0.45213013887405396, -1.2331054210662842, 0.05175577849149704, -1.9690755605697632, 0.902783215045929, -1.5935547351837158, 0.16740722954273224, -0.7199869751930237, 1.010351538658142, -0.31361299753189087, 0.14769896864891052, -0.31517741084098816, 1.0642415285110474, 0.9776366949081421, -0.7673299312591553, 0.01852823980152607, -1.4103515148162842, -1.7194660902023315, 0.7322865724563599, 0.6075846552848816, -0.01912434957921505, -0.15240173041820526, 0.974609375, 2.0938801765441895, -0.6564371585845947, 0.5252522826194763, -1.0104573965072632, 0.7610921263694763, -0.7262227535247803, 0.5899240970611572, -1.3556314706802368, -0.2762593626976013, -1.3406575918197632], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.

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

{'search_vector': [0.3733150064945221, 0.8701041340827942, -3.283203125, -0.8237696886062622, 1.8587820529937744, -1.2651890516281128, -0.1662575900554657, -0.8273795247077942, -0.6716046929359436, -0.9754813313484192, 1.4313267469406128, 0.15629850327968597, 1.653076171875, 0.21351133286952972, -0.2202562540769577, 0.5960268378257751, 1.3892298936843872, -0.9069310426712036, -1.0660051107406616, 0.0735451802611351, -0.13080978393554688, -0.8337838053703308, -1.1962541341781616, -0.1757921427488327, 1.1533377170562744, -1.0752519369125366, 0.7735595703125, 0.7952008843421936, -1.41357421875, -0.762024998664856, 0.90728759765625, 0.5013297200202942, -0.12163543701171875, -1.3086808919906616, 0.2313908189535141, -0.2127663791179657, 1.2329798936843872, 0.13693292438983917, -0.5986388325691223, 0.5183977484703064, -0.5775931477546692, 1.0892508029937744, 1.0014474391937256, 0.7603411078453064, 0.5985107421875, -0.3764408528804779, 0.2769339382648468, 0.1484200656414032, -0.042887549847364426, -1.1122175455093384, 0.5623648762702942, -0.6858879923820496, 0.0706939697265625, -1.1795480251312256, 0.9498116374015808, 0.8876429796218872, -0.07709299027919769, 0.4414280354976654, -1.0717277526855469, -0.4216046929359436, 0.6204659342765808, 0.7411338090896606, 0.050996508449316025, 1.7786691188812256, 1.8202427625656128, 0.3939121663570404, -0.477386474609375, 0.4526563286781311, -0.9215262532234192, -0.217071533203125, 0.14909744262695312, -0.7410103678703308, 0.9745374321937561, 0.3884669840335846, 0.2986232340335846, 0.02842058427631855, -0.15534210205078125, -1.3710066080093384, -0.1018480584025383, 0.6115297675132751, 0.4682682454586029, 0.04295894131064415, 0.9726213812828064, -0.9433201551437378, 0.6450827717781067, 0.0292184017598629, -0.658905029296875, 1.0212129354476929, -0.9578508734703064, 0.7146083116531372, -0.0859375, -0.0492924265563488, 1.0412379503250122, 0.4467599093914032, -0.7428327798843384, 0.4633135199546814, -0.5757097601890564, 0.9025006890296936, -0.9837733507156372, -0.08203233778476715, 0.0329328253865242, 0.41596439480781555, 0.2956368625164032, -0.3987361490726471, 0.8928048014640808, 0.23455674946308136, -0.4034772515296936, 0.7928673624992371, 1.1166294813156128, -0.7583356499671936, -0.3316628634929657, 0.2652217447757721, 0.17242567241191864, -0.3459123969078064, 0.7237701416015625, -1.0731027126312256, 0.10618836432695389, 0.3279462456703186, 0.1654706746339798, 0.8646240234375, -0.5115879774093628, -0.21544210612773895, -0.3669956624507904, 1.2215402126312256, -0.12576048076152802, -0.21836437284946442, -1.3944615125656128, 0.5532630085945129, 0.0503169484436512, -0.2861262857913971, 0.5151847004890442, -1.4261300563812256, -1.1390904188156128, -0.2398463636636734, 0.48499950766563416, -0.195236474275589, -0.0626852884888649, -0.35411399602890015, 0.13389696180820465, -0.43058040738105774, 0.9500557780265808, 0.3811386525630951, 0.2267630398273468, -0.2524065375328064, -0.2040175050497055, -0.5503453016281128, 0.9926060438156128, -0.08960015326738358, 0.062117986381053925, -0.0774056538939476, 0.0820334330201149, 1.3520158529281616, 1.3568638563156128, 0.3465336263179779, 0.1777932345867157, -0.3550371527671814, -0.1502467542886734, 0.3486219048500061, 1.0585676431655884, 0.8371124267578125, 0.5248631238937378, -0.0369785837829113, -0.10310479253530502, 0.0599016472697258, -0.1380615234375, 0.09508950263261795, 0.2664838433265686, 1.32861328125, -0.2117244154214859, 1.3905900716781616, -0.6023483276367188, -1.1012660264968872, 0.08713041245937347, -0.6558445692062378, 0.8460868000984192, -0.3892190158367157, 0.3495309054851532, -0.08673422783613205, 0.625640869140625, -1.0066789388656616, 0.5417660474777222, -1.3306710720062256, 0.5898328423500061, 0.5298832654953003, -0.9719576239585876, 0.7023429870605469, 0.2697383463382721, 0.368072509765625, -1.2298060655593872, -1.2123674154281616, 1.1716482639312744, 0.5491071343421936, -1.1862008571624756, -0.131072998046875, -0.8675885796546936, -0.3292454183101654, 1.0174560546875, -0.6417672038078308, 0.7125679850578308, -0.5861729383468628, -0.46343994140625, -0.13938358426094055, -0.7265101671218872, -0.0616455078125, -0.5609305500984192, -0.0453665591776371, 0.2735334038734436, 0.0506068654358387, -0.8567940592765808, 0.1264692097902298, 1.6446009874343872, 0.5882001519203186, -1.4191545248031616, 0.3375222384929657, 0.2794145941734314, -0.4315011203289032, -0.10660988837480545, -0.6320626139640808, -0.1934814453125, 0.43555396795272827, 0.8951041102409363, 0.11443601548671722, 0.008272715844213963, -1.0894688367843628, -0.2349155992269516, 0.1780962198972702, -1.2292916774749756, -0.282654345035553, 0.01650564931333065, 0.5520063042640686, 0.3729269802570343, -1.2142159938812256, -0.0564749576151371, 0.6794695258140564, -0.018382754176855087, 0.2342180460691452, 0.3463527262210846, 0.8564845323562622, 0.228515625, -1.0572770833969116, -0.36539676785469055, -0.44364601373672485, -0.6460631489753723, 0.9582868218421936, -1.8318220376968384, -0.50823974609375, -0.7623465657234192, -0.9558280110359192, 0.4962158203125, 0.7255902886390686, -0.34067752957344055, -0.2391488254070282, 0.39809471368789673, -0.0612291619181633, -0.15391214191913605, 0.3712599575519562, 0.5067792534828186, -0.2725786566734314, 0.3308993875980377, -0.1121281236410141, 0.5861456990242004, -0.4220406711101532, -0.19941329956054688, -0.3279767632484436, 0.44698333740234375, -0.9936653971672058, -0.1099962517619133, 0.4278651773929596, 0.0498788021504879, -0.669648289680481, 0.811279296875, 0.0642678365111351, 0.7347052693367004, 0.2546408474445343, 0.4569113552570343, -0.4651203155517578, 0.5434178113937378, -0.08867508918046951, 0.4506443440914154, 1.45263671875, -1.0581315755844116, -1.0892333984375, -0.54180908203125, 0.6216692328453064, -0.75152587890625, 0.2938014566898346, 0.30342811346054077, -0.02690560556948185, 0.1676308810710907, -0.34711673855781555, 1.414306640625, -0.4289158284664154, -1.5668247938156128, 0.19202831387519836, -1.1457170248031616, 0.0567234568297863, 0.6811610460281372, -0.7637459635734558, 1.0741140842437744, -0.3178493082523346, -0.1978193074464798, 1.1081892251968384, 1.8256138563156128, 0.6910138726234436, 0.43697410821914673, -0.198822021484375, 0.26666259765625, -0.1971479207277298, 1.2708216905593872, 1.126953125, -0.44795921444892883, 0.741943359375, -0.740478515625, 0.43310546875, -0.7091020941734314, 0.17133548855781555, 1.0926687717437744, 0.4465157687664032, 0.29878562688827515, 1.0230189561843872, 0.0952736958861351, -1.0248216390609741, -0.3789106011390686, 0.7748456597328186, -0.21004976332187653, -0.5714078545570374, -0.3065338134765625, 0.2915191650390625, 0.011688232421875, -0.4937221109867096, 0.02861567959189415, 0.7010432481765747, 0.4965384304523468, -1.026654601097107, -0.9224330186843872, 0.7547737956047058, 0.4709908664226532, 1.0565708875656128, -0.3294939398765564, 0.5995701551437378, 0.5143345594406128, -1.5651506185531616, 1.3357020616531372, -1.9922224283218384, -0.8417292833328247, 0.1933964341878891, 0.544586181640625, -0.3633640706539154, 0.6493138074874878, 0.12784631550312042, -0.6014186143875122, 0.1890302449464798, -0.20536477863788605, -0.5476859211921692, 1.072446584701538, -0.39317867159843445, 0.7275521159172058, 0.5473240613937378, 0.072784423828125, 0.31202152371406555, 1.0436967611312866, 0.2907060980796814, 0.8015223741531372, -0.4668012261390686, 0.1758226603269577, 0.8317326307296753, 0.3937813937664032, -0.3090122640132904, -0.1791534423828125, -0.4645625650882721, 0.19978441298007965, -0.9328351616859436, -0.16383607685565948, 0.280761182308197, 0.47300830483436584, 0.7348197102546692, -1.1652482748031616, -0.7243260145187378, -0.7243303656578064, 0.6073259711265564, 0.8708147406578064, 0.5190342664718628, 0.7047032117843628, 0.4510563313961029, 0.1475655734539032, -0.1421966552734375, -0.4363534152507782, 0.4984479546546936, -0.1593802273273468, -0.20830318331718445, 1.0077601671218872, -1.0886056423187256, -1.1239885091781616, 0.2785470187664032, -0.3276585042476654, -0.0957096666097641, 1.1360909938812256, -0.8714337944984436, 0.290283203125, 1.4567173719406128, -1.6670619249343872, -0.9295130968093872, 0.1818106472492218, -0.912872314453125, -0.42959704995155334, -0.4323643147945404, -1.2350376844406128, -0.8897269368171692, 1.1086164712905884, 0.06708485633134842, 0.1504712849855423, -0.4305507242679596, 0.0783952996134758, -0.3808855414390564, 0.0864039808511734, 0.2260328084230423, 0.6817713975906372, -0.1889059841632843, -0.046339988708496094, -0.8265708088874817, 0.5224516987800598, 0.1565040498971939, 0.3578295111656189, 0.34158214926719666, 0.6883631944656372, 0.8987165093421936, 0.5048795342445374, 0.9969133734703064, 0.14217548072338104, -1.1593714952468872, 0.4059906005859375, 0.6777605414390564, 0.5905281901359558, -0.34161376953125, -0.1165291890501976, 0.2197134792804718, -0.4861602783203125, 0.29882267117500305, 0.2428065687417984, 0.0949467271566391, 1.0873500108718872, 0.5536651611328125, -0.3673054873943329, -0.16992929577827454, -0.5516014099121094, 2.6014230251312256, 1.5574253797531128, -0.3207070529460907, -0.4856218695640564, 0.3378470242023468, 0.2056535929441452, 0.06536620110273361, 0.2780621349811554, 0.9749755859375, 0.9261823296546936, 0.4798366129398346, 0.3169904351234436, 0.2049211710691452, 0.6238795518875122, 0.6489955186843872, 0.3402295708656311, -0.0899004265666008, -1.7518484592437744, 0.6788983941078186, 0.4595685601234436, 0.5944322943687439, 0.5216544270515442, 0.9175850749015808, 1.4485734701156616, 0.8269391655921936, -1.050048828125, -0.0337459035217762, 0.7050083875656128, -0.38670238852500916, 0.0984257310628891, 0.4014936089515686, -0.6832723617553711, 0.009220668114721775, -0.7646659016609192, 0.2204720675945282, -0.3753787577152252, 0.73675537109375, 0.08903884887695312, -0.982666015625, -0.240478515625, 0.1106131449341774, 0.6843523383140564, -0.11897659301757812, 0.2572413980960846, 0.050651006400585175, -0.4538835883140564, 0.16339111328125, 0.7941981554031372, 0.9735739827156067, 0.0806906595826149, -0.811798095703125, 0.4329049289226532, -0.3866054117679596, -0.3491014838218689, 0.2253962904214859, -0.6077095866203308, 0.9541887640953064, 0.6060747504234314, -1.0604814291000366, 0.5815495252609253, 0.206337109208107, 0.33996692299842834, -0.5452629923820496, 0.0076157706789672375, -0.031358446925878525, -0.1752188503742218, -0.0309579037129879, 0.41231536865234375, 0.77459716796875, 1.0969761610031128, -0.11645861715078354, 1.1045488119125366, -0.3994545340538025, -0.7411760687828064, 0.086273193359375, 0.8029567003250122, -0.35951122641563416, 0.6492134928703308, -0.9827706217765808, -1.1225782632827759, 0.25234222412109375, 1.0458177328109741, -0.5169001817703247, -0.22167150676250458, -0.8419560194015503, 0.10909707099199295, 0.5862775444984436, -1.3431919813156128, -0.3884931206703186, -0.0431256964802742, -0.7325526475906372, -0.1938607394695282, 0.4590824544429779, 1.2843714952468872, 0.30511102080345154, 0.1549333781003952, -0.6985735297203064, 0.1677812784910202, -0.2026258260011673, -0.0530635304749012, -0.42689186334609985, -0.02593914046883583, 0.20275552570819855, -0.54437255859375, -0.8816680908203125, 1.1622837781906128, -0.6006208062171936, 0.015049525536596775, -0.7024405598640442, 0.4604666531085968, -0.4303016662597656, -0.4319436252117157, 0.31431034207344055, 0.4139360785484314, -1.066436767578125, 0.3203243613243103, -0.2232295423746109, 0.3013749122619629, 0.02765914425253868, 0.3248247504234314, -1.3636997938156128, -0.2919834554195404, 0.07922472059726715, -0.7291085124015808, 0.0229012630879879, 0.1093837171792984, -0.7372261881828308, 0.0802699476480484, 0.1382860392332077, 0.8721836805343628, 0.1676374226808548, 0.26885169744491577, 0.5640019178390503, -1.0016218423843384, -0.5716901421546936, 0.6675905585289001, -0.74298095703125, 0.0991930291056633, 0.8489815592765808, 0.0883527472615242, -0.9801897406578064, -0.4980294406414032, -0.3909912109375, -0.4910539984703064, -0.7477852702140808, -0.2734287679195404, -0.3077043890953064, -0.5381951928138733, -1.3850795030593872, -0.22996248304843903, 0.4675728976726532, -0.5342385172843933, -0.2517634928226471, -0.34216636419296265, -0.3173828125, -0.2014378160238266, 0.0441545769572258, 0.6517519354820251, -0.4879412055015564, -0.5684422254562378, 0.4308101236820221, 0.2931029796600342, 0.6380135416984558, -0.1412792205810547, -0.7845557332038879, 0.9619097113609314, -0.1035178080201149, -0.6656766533851624, -0.7563803791999817, -0.15070615708827972, -0.8467145562171936, 0.9961983561515808, -0.5985282063484192, -0.07116807997226715, -0.4288678765296936, -0.7878243327140808, -0.4736851155757904, 1.477294921875, -0.7404196858406067, 0.3823721706867218, -0.7505754828453064, -0.8487025499343872, 0.00932366494089365, 0.4958365261554718, 0.5145350694656372, 0.4066249430179596, 0.4106793999671936, -0.8660888671875, -1.2221766710281372, -1.8618861436843872, 0.7461417317390442, -0.0592215396463871, 0.3999590277671814, 0.05718884989619255, 0.38511767983436584, 2.299037456512451, 0.5808199644088745, -0.3654741644859314, -0.5014386773109436, 0.7543596625328064, -0.48549869656562805, 0.8240683674812317, 1.0344935655593872, 0.1713823527097702, -0.06333378702402115, 1.9914201498031616, 0.1055232435464859, 0.6179591417312622, 0.2046293467283249, 0.7879093885421753, -0.0027825492434203625, 0.13729694485664368, 0.1555110365152359, -1.4131033420562744, -0.4759259819984436, 1.2339041233062744, -0.4105072021484375, -0.14532470703125, 0.32667431235313416, 1.7141462564468384, -0.4064309298992157, -0.4909493625164032, -0.5705544352531433, -0.7382463812828064, 0.02516828291118145, 0.2982352077960968, 0.0033002581913024187, -1.1005423069000244, -1.1944143772125244, 0.9004603624343872, -0.3269914984703064, 0.9827183485031128, 0.4898638129234314, -0.541534423828125, -1.1183384656906128, -0.1322849839925766, -0.2907584011554718, 1.1625453233718872, -0.1927446573972702, -0.46125683188438416, -0.4230869710445404, 0.08205632120370865, -0.2526375949382782, 0.7738385796546936, -0.2837567925453186, -0.14898736774921417, -1.830078125, -0.7488141655921936, -0.3385140597820282, 0.1140856072306633, -0.832763671875, -0.7286463975906372, -0.12980405986309052, -0.5383210778236389, 0.1796438992023468, -0.11845861375331879, 0.0777849480509758, 1.0775669813156128, 1.3174525499343872, -0.11047826707363129, 0.01628072001039982, 0.4810965359210968, 0.6218436360359192, 0.4036472737789154, -1.2825753688812256, -0.8768833875656128, 0.13131332397460938, -0.775726318359375, -0.0282461978495121, 0.2587454617023468, -0.1839338093996048, -0.8471505045890808, -0.6674941182136536, -0.4873613715171814, -0.2386474609375, 0.6084333062171936, -0.05859375, -1.2126115560531616, -0.4347163736820221, 0.0022584369871765375, -0.9705810546875, -0.7727225422859192, -0.4770856499671936, 0.6029052734375, -1.0548793077468872, 0.52691650390625, -0.0820094496011734, -1.3228933811187744, 0.6807861328125, -0.4979335367679596, -0.8868931531906128, -0.8201555609703064, -1.118927001953125, -0.6588309407234192, -0.0705806165933609, -1.3878347873687744, -0.47683605551719666, -0.7441580891609192, 0.8086133599281311, 0.00872039794921875, -0.24217605590820312, -0.6565377116203308, 1.1914411783218384, 1.5847865343093872, -0.7309613823890686, 0.5594220757484436, -0.9970179796218872, -0.9676600694656372, 0.1877877414226532, -0.4642486572265625, 0.32537841796875, -0.11529541015625, 0.2694179117679596, 1.619235873222351, -0.21967792510986328, 1.02783203125, -0.39472824335098267, 1.2251325845718384, -0.6311514973640442, 0.1063581183552742, -0.9914202094078064, -0.4573712944984436, -0.3694479763507843], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (FastAPI | requires | Pydantic | input | validation)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.

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

{'search_vector': [0.6173477172851562, 0.4750518798828125, -3.1241862773895264, -0.86553955078125, 0.5302593111991882, -1.771240234375, 0.9428914189338684, -0.4534931182861328, -0.5167236328125, -0.6948826909065247, 0.927886962890625, 0.4283580780029297, 1.3435872793197632, 0.3255748748779297, 0.9166666865348816, 0.6319656372070312, -0.1829121857881546, -0.668975830078125, -0.5548807978630066, 0.0959370955824852, -0.2474365234375, 0.9136149287223816, 0.23650360107421875, 0.43496957421302795, 1.8611208200454712, 0.478271484375, 0.5860798954963684, 0.1288808137178421, -1.7665201425552368, -1.5083822011947632, 2.7789714336395264, -0.4407399594783783, 0.146087646484375, -0.5260213017463684, -0.2656148374080658, -0.9795125126838684, 1.5647786855697632, -0.2218119353055954, -0.3466240465641022, -0.058074951171875, -0.6494407653808594, 0.5486348271369934, 1.1093343496322632, -1.19580078125, 0.7862446904182434, -0.3608676493167877, 0.26203665137290955, 0.12580108642578125, 0.7809956669807434, -0.9094950556755066, 0.3251698911190033, 0.5714060664176941, -0.42213186621665955, -1.394775390625, 1.3660888671875, -0.5824381709098816, 0.6480255126953125, 0.4203592836856842, -0.46228599548339844, -0.2005411833524704, 0.6549504399299622, -0.7005717158317566, 0.3245887756347656, 1.3658040761947632, 1.1674093008041382, 0.6185862421989441, 0.09983190149068832, 1.4576822519302368, -0.7537816166877747, -0.5600178837776184, 0.0836385115981102, -0.7871500849723816, 1.9973958730697632, 0.06459426879882812, 0.2762654721736908, 0.6124979853630066, 0.27749380469322205, -0.96722412109375, -0.8810469508171082, 0.39948782324790955, -0.07042694091796875, 0.7098363041877747, 0.9749348759651184, -0.25932565331459045, 0.3339589536190033, -0.30243173241615295, -0.38690948486328125, 0.011069933883845806, -0.3448143005371094, 0.5546467900276184, 0.41741690039634705, 0.6151326298713684, 0.23987960815429688, 0.8114216923713684, -0.15376663208007812, -0.21285247802734375, -1.4388021230697632, 1.6798095703125, -1.2071126699447632, -0.29222360253334045, -0.22093994915485382, 0.22462622821331024, 1.1913248300552368, -0.36582693457603455, 0.47918701171875, 0.3325398862361908, -0.14405250549316406, 0.16650645434856415, 0.20765304565429688, 0.03769366070628166, -0.34211477637290955, -0.013782501220703125, 0.2077585905790329, -1.7262979745864868, 1.31500244140625, -0.1759796142578125, 0.8201497197151184, -0.3607076108455658, 0.3524983823299408, 0.838623046875, -0.18656031787395477, -0.7037150263786316, -0.9861246943473816, 0.6405436396598816, -0.1439107209444046, -0.5794525146484375, -1.4998372793197632, 0.682220458984375, 0.8845341801643372, -1.002197265625, -0.3243509829044342, -1.24554443359375, -0.4684549868106842, -0.42768797278404236, 0.832275390625, -0.6501057744026184, -0.8127238154411316, -1.016387939453125, 0.48841872811317444, 0.8776041865348816, 0.3250312805175781, 0.4920400083065033, 0.1675669401884079, 0.39085516333580017, -0.8420206904411316, -0.5199686884880066, 0.2807699739933014, -0.24483998119831085, -0.5957489013671875, 0.2527742385864258, -0.23652394115924835, 0.8595988154411316, 0.0831349715590477, 1.3834228515625, -0.3772366940975189, 0.05358656123280525, -0.3162892758846283, -0.5190277099609375, 0.907257080078125, -0.0681254044175148, 0.6938273310661316, -0.6956532597541809, -0.43223318457603455, 0.5332590937614441, -0.14364178478717804, -0.9102630615234375, 0.5573374629020691, 1.0338134765625, 0.3922271728515625, 1.3918863534927368, -1.0087178945541382, -1.0946044921875, -0.3934834897518158, -0.052282970398664474, 0.6829020380973816, -0.1232248917222023, -0.3916371762752533, 0.36476007103919983, -0.004913965705782175, -0.9359512329101562, -0.5896021723747253, -0.7308400273323059, 0.26818719506263733, 1.4075723886489868, -0.6505330204963684, 0.0136324567720294, -0.6614735722541809, 0.3669281005859375, -0.7140350341796875, -1.0913289785385132, 0.5113932490348816, 1.0044351816177368, 0.03267478942871094, 0.12903468310832977, -0.6074422001838684, -0.44546255469322205, 0.9818522334098816, -0.07218996435403824, 1.1159261465072632, -0.8381703495979309, 0.5011622309684753, 0.5572090148925781, -1.0143228769302368, -0.4230111539363861, 0.2744394838809967, 0.5632832646369934, 0.46861395239830017, 0.1598256379365921, -0.46515145897865295, 0.4605661928653717, 2.2205402851104736, 0.5147755742073059, -0.19075267016887665, -0.16312091052532196, 0.7490768432617188, -0.7404581904411316, 0.29820919036865234, -0.31536865234375, -0.6957905888557434, 0.707305908203125, 1.0550537109375, -0.0072352089919149876, 1.0857747793197632, -1.6851400136947632, -0.38159051537513733, 0.34843191504478455, -1.5720621347427368, 0.13775761425495148, -0.3973175585269928, 0.627685546875, 0.05209978297352791, -0.5066884160041809, -0.08931223303079605, 1.0684407949447632, 0.056732177734375, 0.3666178286075592, -0.13793182373046875, 1.7998861074447632, 0.0011316934833303094, -0.1582997590303421, -0.6227518916130066, -0.5129292607307434, -0.7415263056755066, 0.10940424352884293, -1.9452310800552368, 0.5883407592773438, 0.028189977630972862, -0.421142578125, -0.4182891845703125, 1.3660074472427368, -0.15226173400878906, 0.368804931640625, 0.4249979555606842, 0.24915440380573273, 0.16718673706054688, 0.6727498173713684, -0.25944265723228455, -0.5142313838005066, 0.2334849089384079, -0.21127764880657196, 0.27590179443359375, 0.4072062075138092, 0.1627044677734375, 0.3995310366153717, 0.2050577849149704, -0.5247802734375, -0.0094757080078125, 0.06398582458496094, 0.004272142890840769, -0.93084716796875, 0.2174021452665329, 0.2854715883731842, 1.2350667715072632, 0.4122416079044342, 0.3563741147518158, -0.23987579345703125, 0.5124194025993347, 0.3184102475643158, -0.8035634160041809, 0.916985809803009, -0.7795512080192566, -1.109375, -0.35154977440834045, 0.05920473858714104, -0.67449951171875, 0.4808451235294342, -0.2808939516544342, -0.0595296211540699, 0.7724456787109375, 0.0782470703125, 1.69775390625, -0.7120590209960938, -0.8141224980354309, 0.3440500795841217, 0.04419199749827385, 0.226593017578125, 1.1516824960708618, -0.6543070673942566, 0.5163116455078125, -0.2830606997013092, 0.39971840381622314, -0.10453382879495621, 1.0106149911880493, -0.13527075946331024, -0.6252644658088684, 0.0592397041618824, 1.1237283945083618, -0.8014729619026184, 0.7789204716682434, -0.2096710205078125, 0.625396728515625, -0.07084020227193832, 0.0735880509018898, 0.2205352783203125, -0.3195088803768158, 0.511688232421875, 0.7530009150505066, 0.6767374873161316, 0.6720936894416809, 1.7913411855697632, 0.4232145845890045, 0.015111287124454975, -0.5609944462776184, -0.1326751708984375, 0.1915435791015625, 0.09316571801900864, -0.7636337280273438, 0.6243133544921875, 0.7050984501838684, -0.6040140986442566, -0.5653279423713684, 0.6492945551872253, 0.3948923647403717, -0.35016122460365295, -0.3791637420654297, 1.0666707754135132, 1.4140218496322632, 0.7967732548713684, -0.1657511442899704, 0.6200675964355469, 1.230224609375, -1.011962890625, 1.8282877206802368, -1.763916015625, -0.9723307490348816, 0.07238046079874039, 0.72967529296875, 0.819488525390625, 0.8702799677848816, 0.5828866958618164, -0.4443415105342865, -0.15917587280273438, -0.8317057490348816, -1.0665689706802368, -0.21457862854003906, -0.3311208188533783, 1.5356851816177368, 0.609588623046875, 0.4105377197265625, 0.7871907353401184, 1.3870035409927368, -0.1634960174560547, -1.1182657480239868, 0.7067057490348816, 0.0067342123948037624, -0.170166015625, -0.0756022110581398, 0.2326456755399704, 0.18963877856731415, 0.4200567305088043, -0.6073639988899231, -0.6538289189338684, -0.7046712040901184, 1.0486654043197632, -0.19366455078125, 0.0474141426384449, -0.5376129150390625, -0.5720062255859375, -0.1945749968290329, -0.22163645923137665, 0.3439903259277344, 0.17615501582622528, 0.20149104297161102, 0.7625885009765625, 0.4335801601409912, -0.3467235565185547, 0.013994853012263775, 0.4508005678653717, 0.60162353515625, -0.26402410864830017, 0.43994140625, -1.8191324472427368, -0.9625880122184753, 0.7104288935661316, -0.4304911196231842, 0.12469863891601562, 0.6191202998161316, -0.8692728877067566, 0.0550130195915699, 1.3086141347885132, -1.8055013418197632, -0.8376057744026184, 0.3979898989200592, -0.995330810546875, -0.15224425494670868, 0.1198069229722023, -0.90155029296875, -1.0521036386489868, 0.1109619140625, -0.4468460977077484, 0.23111216723918915, -0.33452096581459045, 0.18004734814167023, 0.11869629472494125, 0.5899245142936707, 0.18355433642864227, 0.5490010380744934, -0.423736572265625, 0.16185760498046875, -0.012982686050236225, 0.12402534484863281, 0.5798237919807434, -0.06728363037109375, 0.6318867802619934, -0.6737095713615417, 1.3496500253677368, 0.1543528288602829, 1.1009317636489868, -0.38746896386146545, -1.0657958984375, -0.2305571287870407, 0.5934880375862122, 1.11871337890625, -1.4063009023666382, 0.255584716796875, -0.9463602900505066, 0.28218841552734375, 0.12526829540729523, 0.31065335869789124, 0.6426880955696106, 0.754058837890625, 0.01904805563390255, -1.631591796875, -0.1276194304227829, -0.1555633544921875, 2.2831218242645264, 1.4322916269302368, -0.022017797455191612, -0.744384765625, 0.0793507918715477, 0.6645457148551941, -0.5448201298713684, -0.75848388671875, 0.8325188755989075, 0.9782359004020691, -0.32346343994140625, 0.02850850485265255, -0.4781239926815033, 1.1722817420959473, -0.15769004821777344, 0.9145100712776184, 0.0504709891974926, -1.42333984375, -0.4493408203125, 0.4222666323184967, 0.8422190546989441, 0.8555590510368347, -0.5983632206916809, 0.3294598162174225, 1.1736246347427368, -0.7557780146598816, 0.2900594174861908, 0.15532077848911285, -0.032950084656476974, 0.3916867673397064, 0.5774332880973816, -0.4551645815372467, 0.039572399109601974, 0.5588429570198059, 1.2502034902572632, 0.23855972290039062, -0.7773316502571106, -0.9294636845588684, -1.1758626699447632, -0.5588874220848083, -0.11274401098489761, 0.31131234765052795, -0.3010355532169342, 0.9652506709098816, 0.1710917204618454, 0.06574249267578125, 0.418914794921875, 0.8896891474723816, 1.22607421875, 0.5700175166130066, 0.8842061161994934, 0.20954830944538116, -0.923126220703125, -0.2649637758731842, -0.618896484375, 0.20673878490924835, 0.024290720000863075, -0.5691731572151184, -1.0481363534927368, 0.2496134489774704, 0.1339976042509079, 0.1859537810087204, -0.38502469658851624, -0.33477783203125, 0.9713134765625, 0.12225595861673355, 0.380126953125, 0.2844136655330658, -0.7690251469612122, 0.033966064453125, -0.750634491443634, 0.85009765625, -0.6461995244026184, -0.1259867399930954, 0.14498138427734375, -0.219512939453125, -0.6382039189338684, 0.008782386779785156, -0.8563740849494934, -1.3577880859375, -0.4150187075138092, 0.520263671875, -0.017913818359375, 0.4512532651424408, 0.07071042060852051, -0.5820414423942566, 0.23441822826862335, -0.7309163212776184, -0.038270313292741776, -0.5655059814453125, -0.5115916132926941, -0.5067647099494934, 0.80706787109375, 1.6082254648208618, 0.4039967954158783, 0.33961740136146545, 0.44467416405677795, -0.3189493715763092, 0.6192550659179688, -0.3699086606502533, -0.7234598994255066, -0.5077260136604309, 0.3212076723575592, -0.5818684697151184, -0.9111124873161316, 1.1496988534927368, -1.0660806894302368, 0.0817769393324852, -0.6912028193473816, 0.6364186406135559, -0.3502909243106842, 0.04198487475514412, 0.41117605566978455, -0.6697184443473816, -0.8349202275276184, 1.1548258066177368, -0.039653778076171875, 1.8213602304458618, 0.5333264470100403, -0.34504446387290955, -1.4755452871322632, 0.3880411684513092, 0.0408376045525074, 0.3723297119140625, 0.7400786280632019, 0.2734356224536896, -1.5482584238052368, -0.10648345947265625, -0.41651472449302673, 0.019371667876839638, -1.1394857168197632, -0.1295827180147171, 0.2542775571346283, -0.558807373046875, -0.3950449526309967, 1.1197509765625, -1.5127767324447632, 0.4025000035762787, 0.807586669921875, -0.16802978515625, 0.039476871490478516, -0.7185261845588684, 0.04718017578125, -0.1226450577378273, -0.07590707391500473, 0.4049072265625, 0.3255055844783783, -0.5280964970588684, -0.577948272228241, 0.6477222442626953, 0.19234339892864227, -0.4717966616153717, 0.3435262143611908, -0.1407063752412796, -0.04677264019846916, -1.3880208730697632, -0.09892018884420395, 0.8458163142204285, -0.035249073058366776, 0.109222412109375, 1.0761922597885132, -0.3414459228515625, -0.008046467788517475, -0.11514822393655777, -0.8338826298713684, 1.7771810293197632, -0.8478596806526184, 0.021984100341796875, -0.020233154296875, -0.146881103515625, -0.418469101190567, 0.4837442934513092, -0.58905029296875, -0.6544063687324524, 0.1844635009765625, -0.34870147705078125, -1.3880208730697632, 0.3655649721622467, -0.8592122197151184, -0.6374766230583191, -0.5631205439567566, -0.7675857543945312, -1.0334192514419556, 0.5087051391601562, -0.82244873046875, -0.288330078125, 0.932837188243866, 0.10701560974121094, -1.8053792715072632, -1.3364664316177368, 0.8222147822380066, -0.05568186566233635, -0.630279541015625, -0.5402424931526184, 1.07879638671875, 1.0722604990005493, 0.33796438574790955, 0.21262073516845703, -0.66668701171875, 0.589935302734375, -0.15591812133789062, -0.0030644733924418688, -0.2455495148897171, -0.07074642181396484, 0.32592010498046875, 1.2263132333755493, 1.03570556640625, 0.7832692265510559, -0.2318522185087204, 0.07257080078125, -0.33892822265625, 0.48391976952552795, 0.029466310515999794, -1.2967529296875, -0.23255856335163116, -0.3165028989315033, 0.0975087508559227, -0.448394775390625, 0.4384562075138092, 0.9844970703125, -0.6610107421875, 0.3946342468261719, 0.007624149322509766, -0.9183909296989441, 0.08398691564798355, 0.1821705549955368, 0.8330485224723816, -1.33203125, -1.3545736074447632, 1.2129720449447632, 0.33558526635169983, 1.185546875, 0.0382029227912426, 0.1011250838637352, -0.09970283508300781, -0.44934144616127014, -0.286102294921875, 0.8328654170036316, 0.7650464177131653, -1.4288126230239868, -0.5859629511833191, 0.3080380856990814, 0.28607305884361267, 0.0453592948615551, -0.1676839143037796, -0.5884602665901184, -1.1193491220474243, -0.39912161231040955, 0.5375874638557434, 1.0391845703125, -0.2250010222196579, -1.2992757558822632, -0.16544342041015625, -0.2114766389131546, 1.0342254638671875, 0.06696701049804688, 0.5970204472541809, -0.180755615234375, 0.3483683168888092, -0.3380330502986908, 0.2894287109375, 0.2193705290555954, 0.06713994592428207, 0.518798828125, 0.4474029541015625, -1.7750244140625, 0.34131622314453125, -0.6108551025390625, 0.0739339217543602, -0.6034978032112122, 0.0299530029296875, -0.7557474970817566, -1.6385091543197632, 0.24578857421875, -0.0688832625746727, 0.49242910742759705, -0.31218719482421875, -0.8837890625, 0.08199945837259293, -0.1127522811293602, -0.9224039912223816, 0.06678882986307144, -0.3637135922908783, -0.557342529296875, -1.1261495351791382, 0.8161213994026184, -1.4945068359375, -0.6100628972053528, 0.5899505615234375, -0.46920499205589294, -0.17766444385051727, -1.60546875, -1.3204549551010132, -1.6328939199447632, 0.0869547501206398, -1.366943359375, -0.7263132929801941, -1.1248372793197632, 1.5078125, -0.2032012939453125, -1.1141763925552368, 0.0382080078125, 0.7469431757926941, 1.4892578125, -0.29603704810142517, 1.1686807870864868, -0.7684326171875, -1.4324747323989868, -0.5884501338005066, 0.7762044072151184, 0.09830093383789062, -0.07651138305664062, -0.4230753481388092, 2.0805256366729736, -0.7815704345703125, 1.461669921875, -0.184722900390625, 0.4149017333984375, -0.5189552307128906, 0.0247370395809412, -0.7159627079963684, -0.636199951171875, -0.6746419072151184], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.

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

{'search_vector': [0.4238651394844055, 0.708953857421875, -2.4873046875, 0.11509628593921661, 0.7725822329521179, -0.7846587896347046, 0.8222931027412415, -0.44898223876953125, 0.2860611081123352, -0.7482269406318665, 0.6876777410507202, 0.5228309631347656, 1.0027344226837158, 0.4061737060546875, -0.3937074542045593, 0.41798028349876404, 0.4582626223564148, -0.6228622198104858, -0.006190490908920765, 0.0064826966263353825, -0.5267273187637329, -0.21912308037281036, -0.3264572024345398, 0.5501953363418579, 1.4420650005340576, 0.14758186042308807, 1.2459468841552734, -1.2210114002227783, -2.386279344558716, 0.213287353515625, 1.9181029796600342, 0.012735938653349876, 0.07286987453699112, -1.328710913658142, -0.5318344235420227, -0.662261962890625, 0.190257266163826, -0.3164825439453125, 0.19950027763843536, 1.201074242591858, 0.4656829833984375, 0.668804943561554, 1.277563452720642, -0.209228515625, 1.093316674232483, -0.0406225211918354, 0.1797744780778885, 0.0464019775390625, 0.8253501653671265, -1.314111351966858, 0.18545684218406677, 0.20763245224952698, 0.10094185173511505, -1.4983336925506592, 0.4741660952568054, 0.3641647398471832, 0.11371078342199326, 0.8852264285087585, -0.8855956792831421, 0.3875991702079773, 0.6708739995956421, 0.36415863037109375, 0.39587897062301636, 0.8969705700874329, 0.9967041015625, 0.2791892886161804, -0.944256603717804, 0.8409057855606079, -0.18053284287452698, -0.13547363877296448, 1.008276343345642, -0.009394073858857155, 1.12408447265625, 0.5289306640625, 0.4271162450313568, 0.7482719421386719, -0.11050491034984589, -1.0397827625274658, 0.31453245878219604, 1.0115760564804077, -0.7048629522323608, 0.08385543525218964, 0.7708969116210938, 0.27732008695602417, 0.697998046875, -0.11584071815013885, -0.13455811142921448, 0.0398380272090435, -0.702648937702179, 1.192968726158142, -0.3370010256767273, -0.1109771728515625, 0.6958328485488892, -0.6398956179618835, -0.624438464641571, -0.47660523653030396, -0.9519561529159546, 1.246923804283142, -0.6774841547012329, -0.3272705078125, -0.26427382230758667, 0.4303169250488281, -0.06081695482134819, -0.9600173830986023, 0.2693327069282532, -0.357687383890152, 0.7181802988052368, 0.5369804501533508, 0.2724285125732422, -0.3675994873046875, 0.78155517578125, 0.17355728149414062, -0.08956705033779144, -0.98114013671875, 0.15015287697315216, 0.032875824719667435, 0.35373228788375854, -0.6652466058731079, 0.2975580096244812, -0.12099456787109375, 0.02762603759765625, -0.712628185749054, -0.85821533203125, 0.6205505132675171, 0.5555053949356079, -0.14667129516601562, -0.43821126222610474, 0.751568615436554, 0.4404739439487457, -1.4142639636993408, -0.5140320062637329, -0.9726806879043579, -1.026208519935608, 0.31682413816452026, -0.5916793942451477, -0.3695247769355774, -0.6267277598381042, -1.465789794921875, 0.6565437316894531, 0.214976504445076, 0.5461181402206421, 0.681286633014679, 0.34768372774124146, -0.3020192086696625, 0.44578248262405396, -0.689862072467804, 0.3010299801826477, -0.6271911859512329, -0.298837274312973, 0.618609607219696, -0.31673258543014526, 0.875262439250946, 0.07605667412281036, 1.176025390625, -0.4707504212856293, -0.7212432622909546, -0.2693115174770355, 0.19378814101219177, 0.417288213968277, -0.008982086554169655, 1.2519042491912842, 0.2769836485385895, -1.0457763671875, 0.36327362060546875, -0.397439569234848, -1.048211693763733, 0.1674240082502365, 1.6957519054412842, 0.23380355536937714, 1.1173782348632812, -1.3310730457305908, -0.47829896211624146, 0.3751663267612457, -0.1358177214860916, 1.3477783203125, 0.20200929045677185, -0.5153053402900696, -0.13235855102539062, 0.37845152616500854, -0.11550979316234589, 0.10573577880859375, -0.6861358880996704, -0.37732619047164917, 0.3978416323661804, -1.212152123451233, 0.4943710267543793, -0.5133590698242188, 0.06120331212878227, -1.479522705078125, -0.03763847425580025, 1.351171851158142, 0.46534425020217896, -0.8921432495117188, -0.06507416069507599, -0.87738037109375, 0.0002716064336709678, 0.22199860215187073, 0.060005951672792435, 0.932385265827179, -0.21103553473949432, 0.13981933891773224, -0.3039192259311676, -0.49623411893844604, -0.3593086302280426, -0.628814697265625, -0.8883301019668579, 0.808819591999054, 0.332986444234848, -0.20812436938285828, 0.33490484952926636, 1.3478240966796875, 0.760711669921875, -1.1296875476837158, -0.2662951350212097, -0.06726150214672089, -0.957720935344696, -0.20201340317726135, -0.24626922607421875, -0.30233079195022583, 0.856311023235321, 1.426513671875, 0.1603187620639801, 0.41995009779930115, -1.3558471202850342, -0.9287109375, -0.7549362182617188, -0.5157123804092407, -0.22959557175636292, -1.092321753501892, 0.2877945005893707, -0.4545913636684418, -0.988354504108429, 0.4616241455078125, 0.317861944437027, -0.24755096435546875, 0.3854812681674957, 0.789501965045929, 2.121630907058716, 0.3600723147392273, -0.4097137451171875, -0.16241760551929474, 0.28769224882125854, -0.9833984375, 0.6325599551200867, -0.7527816891670227, -0.10022211074829102, -0.23825684189796448, -0.637097179889679, 0.07141266018152237, 0.947802722454071, 0.5126067996025085, -0.05871257930994034, 0.07669830322265625, 0.71246337890625, -0.547882080078125, -0.21018409729003906, 0.14389953017234802, 0.10267486423254013, -0.08641662448644638, -0.7138946652412415, 0.5419357419013977, -0.3171989321708679, -0.32860907912254333, -0.7523307800292969, 0.41664886474609375, -0.02389373816549778, 0.875244140625, 0.8581634759902954, 0.12035751342773438, -0.4529038369655609, -0.4017471373081207, 0.2230072021484375, 0.07284851372241974, 1.119866967201233, 0.5917474031448364, 0.06821136176586151, 0.24619273841381073, -0.5512580871582031, -0.40305662155151367, 1.807214379310608, -0.3542488217353821, -0.5539634823799133, -1.2308228015899658, -0.20416411757469177, 0.1531417816877365, 0.08089032024145126, 0.1513538360595703, -0.0013946533435955644, 0.9209970235824585, -0.06968460232019424, 0.589764416217804, 0.176727294921875, -1.2205016613006592, 1.0883376598358154, 0.4775441586971283, 0.06292305141687393, 0.20014934241771698, 0.06446532905101776, -0.016046274453401566, -0.05898322910070419, 0.6864898800849915, 1.0786559581756592, 1.441308856010437, 0.7646805047988892, -0.01762695237994194, -0.2748001217842102, -0.058496855199337006, -0.587969958782196, 1.116552710533142, 0.890209972858429, 1.126708984375, 0.872174084186554, -0.6533355712890625, 1.0920486450195312, -0.44089967012405396, 1.0589599609375, 0.5642334222793579, 0.393480122089386, 0.560559093952179, 0.734851062297821, -0.9905964136123657, 0.8914550542831421, -0.8428863286972046, -0.300546258687973, -0.9970798492431641, 1.0503021478652954, 0.5100356936454773, 0.7063003778457642, 0.05355072021484375, 0.7790893316268921, -0.6270354986190796, 0.24546661972999573, 1.9706817865371704, -1.306451439857483, -0.9248641729354858, 0.7382446527481079, 0.21649932861328125, -0.31487560272216797, -0.08298148959875107, 0.6287773251533508, 0.8420013189315796, -0.3929809629917145, 0.5991256833076477, -1.4884765148162842, -0.5670837163925171, -0.4382080137729645, 0.631756603717804, -0.17415428161621094, 0.8330215215682983, 0.8295348882675171, -0.8264312744140625, 0.8684326410293579, -0.8113464117050171, -0.47146111726760864, 0.28384095430374146, -0.24576416611671448, 0.691851794719696, 1.16778564453125, 0.00592041015625, 0.7815796136856079, 0.05417633056640625, -0.16237792372703552, 0.04745178297162056, 0.22394637763500214, 0.4580322206020355, 0.17355194687843323, -0.457711786031723, -0.527697741985321, 0.16410216689109802, -0.14264126121997833, 0.10193004459142685, -0.4186660647392273, 0.26205140352249146, 0.36569517850875854, -0.12442322075366974, -0.6885849237442017, -0.619537353515625, -0.510760486125946, -0.379843533039093, 1.336369276046753, 0.3078628480434418, -0.47603511810302734, -0.11761169135570526, 0.3741874694824219, 0.907788097858429, -0.6955734491348267, 0.3525024354457855, -0.3841384947299957, 0.16536244750022888, 0.36341553926467896, 0.3882043957710266, -1.2092711925506592, -0.004333305172622204, 0.8387695550918579, 0.7616165280342102, -0.3125728666782379, 1.0805505514144897, -0.00424270611256361, 0.2804134488105774, 0.91534423828125, -1.33233642578125, -0.8451477289199829, -0.05111236497759819, -0.89739990234375, 0.4353805482387543, 0.194294735789299, -1.220947265625, -0.49600905179977417, 1.2303451299667358, -0.32122498750686646, -0.35826873779296875, 0.2440948486328125, -0.2876083254814148, 0.3227905333042145, -0.16245421767234802, -0.09960003197193146, 1.0776641368865967, 0.9291183352470398, 0.06701831519603729, -1.1061890125274658, -0.17748793959617615, 0.8761352300643921, 0.27580565214157104, -0.13779525458812714, -0.8230377435684204, 0.55914306640625, 0.28804779052734375, -0.03420257568359375, -0.6277526617050171, -0.6424759030342102, -0.2463943511247635, 0.571062445640564, 0.48330268263816833, -0.2524169981479645, -0.14680442214012146, -0.22479858994483948, 1.03945791721344, 1.603759765625, 0.5202857851982117, 0.7637893557548523, 0.6704376339912415, 0.42635154724121094, -0.7119483947753906, 0.3916061520576477, -0.5094162225723267, 2.0179076194763184, 1.0106680393218994, -0.3630309998989105, -0.9909744262695312, 0.19944033026695251, 0.4545272886753082, -0.030644988641142845, 0.575854480266571, 0.326211541891098, 0.9591003656387329, -0.272116094827652, -0.548785388469696, 0.25138092041015625, 0.7745391726493835, 0.276406854391098, 0.416229248046875, 0.8928161859512329, -0.8835121393203735, 0.11939163506031036, -0.1708293855190277, 0.48038196563720703, 0.962139904499054, -0.1360878050327301, 0.43021851778030396, 1.077478051185608, -0.5752517580986023, 0.277496337890625, 0.0867336243391037, 0.6766265630722046, 0.3199752867221832, 0.4907165467739105, -0.5414184331893921, 0.6979202032089233, -0.5099338293075562, 1.2210204601287842, -0.3818214535713196, -0.6717529296875, -0.3863967955112457, -0.2014361321926117, -0.39009398221969604, 0.2124015986919403, -0.054149627685546875, -0.286224365234375, 0.1358603537082672, -0.03723449632525444, 1.1159179210662842, 0.3194122314453125, 0.6170074343681335, 1.12701416015625, -0.10792122036218643, 0.3208238482475281, -0.14174194633960724, 0.21579894423484802, -0.8919342160224915, 0.3251480162143707, -0.8620986938476562, -0.01760559156537056, -0.01683788374066353, -0.9209045171737671, 0.5468246340751648, 0.46144819259643555, 0.30469971895217896, -0.46984559297561646, -0.09732971340417862, -0.10295028984546661, 0.5319610834121704, 0.1986263245344162, 0.669097900390625, 0.7274535894393921, 0.837872326374054, -1.2311522960662842, 0.959014892578125, -1.0709044933319092, -0.4397037625312805, -0.09390411525964737, -0.611706554889679, -0.3579513430595398, -0.5551391839981079, -0.03496189042925835, -1.6313965320587158, -0.24263915419578552, -0.7625274658203125, 0.13806457817554474, -0.359579473733902, -0.02751617506146431, -0.13073882460594177, 0.37720948457717896, -0.7941039800643921, -0.493804931640625, -0.21827086806297302, -0.21207503974437714, -0.6945098638534546, 0.6089202761650085, 0.8415161371231079, 0.9287780523300171, -0.05460510402917862, 0.30331724882125854, 0.2870185971260071, 0.82098388671875, -1.3184936046600342, -0.207611083984375, -0.8541259765625, 0.2985427975654602, -0.01851806603372097, -1.6698729991912842, 0.820111095905304, 0.4195800721645355, -0.42698973417282104, -0.2959960997104645, 0.08783264458179474, -0.12061043083667755, 0.17334747314453125, 0.4301307797431946, -1.1115500926971436, -0.08912048488855362, 0.25710755586624146, 0.6089363098144531, 0.8720947504043579, 0.773114025592804, 0.11062125861644745, -1.928369164466858, -0.21443787217140198, 0.3993053436279297, -0.21044769883155823, 1.0306289196014404, -0.3777849078178406, -0.8785255551338196, -1.555932641029358, 0.4069366455078125, -0.0342891700565815, -0.32021790742874146, -0.686602771282196, 0.7611778378486633, -0.495147705078125, -1.28466796875, 0.00628318777307868, -0.884960949420929, 0.498727411031723, 0.209788516163826, -0.436990350484848, -0.6168281435966492, 0.04454803466796875, -0.574066162109375, 0.6703513860702515, -0.6834472417831421, -0.234516903758049, -0.6791412234306335, -0.5529893636703491, -0.48358154296875, -0.4261932373046875, 0.32402896881103516, -0.8509634137153625, -0.3170059323310852, -0.4982765316963196, 0.429055392742157, -1.418603539466858, 0.08996124565601349, 0.11434326320886612, -0.7085479497909546, -0.8523223996162415, 0.8397308588027954, 0.03723869472742081, 0.3914222717285156, -0.7162719964981079, -0.47259217500686646, 0.9515441656112671, -0.6600891351699829, 0.21058949828147888, -0.10023041069507599, -0.11473145335912704, -0.4806106686592102, 0.7791311144828796, 0.24874190986156464, -0.9990142583847046, -0.35802000761032104, -0.0003654480096884072, -1.1613647937774658, 0.7298736572265625, -0.1139373779296875, 0.7083282470703125, -0.4050644040107727, -0.3521781861782074, -0.13516274094581604, 0.07838745415210724, -0.22143784165382385, -0.024837112054228783, 0.8115860223770142, -1.8907043933868408, -1.69189453125, -0.8299835324287415, 0.16372069716453552, 0.32583314180374146, -0.07085876166820526, 0.212803453207016, 0.0738561823964119, 1.9057128429412842, 0.6437652707099915, -0.6336441040039062, -0.4244751036167145, -0.24289703369140625, -0.012036132626235485, 0.5603208541870117, 0.5946716070175171, 0.27802735567092896, -0.5318939089775085, 0.1299591064453125, 0.763781726360321, 0.849072277545929, 0.13927459716796875, 0.6318817138671875, -0.07912139594554901, 0.389962762594223, 0.1728920042514801, -0.8332405090332031, -0.2720809876918793, 0.3843318819999695, -0.2813720703125, 0.0070892334915697575, -0.48072510957717896, 1.5231444835662842, -0.3209823668003082, 0.6642717123031616, -0.55023193359375, -0.9518066644668579, -0.2926391661167145, 0.021700572222471237, 0.2638481557369232, -0.8414306640625, -1.5713379383087158, 0.568499743938446, -0.0505218505859375, 0.6271774172782898, -0.05317077785730362, -1.0948975086212158, 0.02525482140481472, 0.37670817971229553, -0.03751497343182564, 0.249095156788826, 0.3758811950683594, -0.443276584148407, 0.11371307075023651, 0.023078154772520065, -0.9713333249092102, -0.8277664184570312, -0.5069999694824219, -0.6198364496231079, -0.771344006061554, -0.4999938905239105, -0.6457168459892273, -0.7242881655693054, -0.495880126953125, -1.289636254310608, -0.14966697990894318, -0.6702194213867188, 0.893389880657196, 0.40059202909469604, 0.32834702730178833, 0.26285094022750854, 1.2510497570037842, -0.5513244867324829, 0.39357298612594604, 0.26803892850875854, -0.49112242460250854, 0.540814220905304, 0.2999511659145355, -1.1436035633087158, 0.42071837186813354, -0.5136855840682983, 0.1692863404750824, -0.007565307430922985, -1.4222412109375, -0.7912231683731079, -1.000732421875, -0.1464393585920334, -0.03345031663775444, 0.7313459515571594, 0.07960815727710724, -0.8122407793998718, -0.006285476498305798, -0.17355461418628693, -0.35696715116500854, 1.284814476966858, -0.34899672865867615, 0.3672843873500824, -1.002893090248108, 0.4911041259765625, -0.055585481226444244, -0.341543585062027, 0.38197022676467896, -1.3772701025009155, 0.7726806402206421, -0.44071274995803833, -0.9097305536270142, -1.8271973133087158, 0.4114517271518707, 0.01676025427877903, -0.725360095500946, -1.2198975086212158, 0.5880386233329773, 0.15097656846046448, 0.35178107023239136, -0.24282531440258026, 1.149627685546875, 0.03090057335793972, -0.663256824016571, 0.2977737486362457, -0.6564849615097046, -1.4125244617462158, 0.3328605592250824, 0.307821661233902, 0.2936843931674957, 0.05606842041015625, 0.10177765041589737, 1.7281067371368408, 0.248942568898201, 0.6262508630752563, -1.3023681640625, 0.08251647651195526, -0.3872106671333313, 0.245402529835701, -1.434289574623108, -0.16107559204101562, -0.9270385503768921], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.

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

{'search_vector': [-0.05908902361989021, 0.3240877687931061, -3.7428386211395264, -1.0586344003677368, 0.9513346552848816, -0.9807078242301941, 1.2306722402572632, 0.06479135900735855, -0.3530324399471283, -0.07082811743021011, -0.56012362241745, 0.3643442690372467, 1.0518798828125, 0.38206353783607483, 0.0626220703125, -0.17815780639648438, -0.6890462040901184, 0.11236826330423355, -0.5574544072151184, -0.8434651494026184, -0.44714227318763733, -0.04718272015452385, 0.3025480806827545, -0.6373392939567566, 1.9555383920669556, 0.9766795039176941, -0.6659774780273438, -0.86419677734375, -0.6282145380973816, -0.9668375849723816, 1.5967203378677368, -1.3906046152114868, 1.2530924081802368, -0.6124165654182434, -1.23876953125, -0.6886653900146484, 0.7740020751953125, -0.5837745666503906, -0.23238880932331085, 0.8934428095817566, 0.1583607941865921, -0.7136866450309753, 0.5831095576286316, -1.2138265371322632, 0.3725484311580658, -0.4599323272705078, 0.106292724609375, 0.48037973046302795, 0.086578369140625, -1.7782388925552368, 1.2023111581802368, 0.6796976923942566, -0.21372222900390625, -0.5104777216911316, 1.2498372793197632, -0.9996744990348816, 0.5273234248161316, 0.714813232421875, -0.3386586606502533, -2.05224609375, 0.2183583527803421, 0.4769287109375, -0.6802520751953125, 1.0064773559570312, 0.2906443178653717, 0.5906295776367188, -0.4957192838191986, 0.96527099609375, -0.1116434708237648, -0.20875120162963867, 0.1905522346496582, -0.7450154423713684, 0.6324278712272644, -0.29587554931640625, -0.21163685619831085, -0.13220469653606415, -0.0974985733628273, -0.5855814814567566, -0.4529825747013092, 0.4742991030216217, 0.0216191615909338, -0.13217799365520477, -0.14804840087890625, 0.29411378502845764, 0.5766347050666809, 0.2313588410615921, -0.5714848637580872, -0.10313669592142105, 0.71649169921875, 1.64434814453125, -0.3397725522518158, 0.0354868583381176, 0.0313822440803051, 0.4516487121582031, -1.34820556640625, -0.28482818603515625, -0.5496444702148438, 0.47967657446861267, -0.4431253969669342, -0.3264547884464264, -0.0816599503159523, -0.37474822998046875, 0.3054097592830658, -0.31535717844963074, -0.7429097294807434, 0.7054240107536316, -0.10299301147460938, 0.5311203002929688, -0.1377461701631546, -0.23926925659179688, -0.3236885070800781, 0.38963571190834045, -0.0085906982421875, 0.1947021484375, 0.7575404047966003, -0.1213734969496727, 1.2705078125, -0.6537882685661316, -0.0202051792293787, 1.1020303964614868, -0.02860005758702755, -1.2869466543197632, -0.3397928774356842, 1.0904134511947632, 0.0061696371994912624, 1.4556375741958618, -1.2502847909927368, 0.815673828125, 0.4621772766113281, -0.9270426630973816, 0.0946909561753273, -0.32521820068359375, -0.3474082946777344, -0.018510818481445312, 0.3753407895565033, -0.464019775390625, -1.0177001953125, -1.2253150939941406, 1.7406412363052368, 0.103912353515625, 0.8003947138786316, 0.3575563430786133, -0.06021944805979729, 0.045745849609375, -0.05756378173828125, -0.4703165590763092, -0.40594482421875, -0.07953771203756332, -0.53814697265625, 0.5399017333984375, -0.49011072516441345, 0.7788493037223816, -0.464780330657959, 0.2848714292049408, -0.7386983036994934, -0.13852183520793915, 0.25086846947669983, -0.2599385678768158, 0.2508901059627533, 0.6623942255973816, 0.9546305537223816, -0.6252339482307434, -0.23238308727741241, 0.04457855224609375, 0.012821197509765625, -0.934814453125, 0.6789512634277344, 1.82080078125, 0.11237844079732895, 0.7529703974723816, -0.9254633784294128, -0.5450782775878906, -0.8502044677734375, 0.69525146484375, 0.4575907289981842, -0.08784230798482895, 0.6808955073356628, -0.2943153381347656, 0.915435791015625, -1.3846435546875, -1.3336588144302368, -0.8063151240348816, 0.7928110957145691, 0.7215932011604309, -0.28602853417396545, -0.0857086181640625, 0.1481374055147171, -1.726318359375, -0.5293490290641785, -1.1548665761947632, -0.4954071044921875, 0.25640869140625, -0.2865994870662689, 6.357828533509746e-05, -0.611029326915741, -0.054107666015625, 1.0065103769302368, 0.2956644594669342, 0.7893473505973816, -1.1494140625, 0.7706400752067566, 0.4557138979434967, -0.8950602412223816, 0.3489430844783783, -0.8355305790901184, 1.2136434316635132, 0.21104685962200165, 0.58319091796875, -0.2041524201631546, 0.7773844599723816, 1.8583984375, -0.25273895263671875, 0.36036428809165955, -0.651458740234375, 0.2465565949678421, -0.6630045771598816, -0.022891363129019737, 0.1220804825425148, -0.7266082763671875, 0.17181523144245148, 1.0236002206802368, -0.9801025390625, 1.0697733163833618, -0.8446248173713684, -0.36873117089271545, 0.3350677490234375, -1.10699462890625, 0.3914998471736908, -0.8901163935661316, 0.28339895606040955, -0.0604604072868824, -1.0830078125, 0.75531005859375, -0.0822347030043602, 0.32843017578125, 0.13490994274616241, -0.812955379486084, 1.406982421875, -0.14829635620117188, -0.5934092402458191, -0.3059844970703125, 0.98504638671875, 0.07321548461914062, 0.20087940990924835, -0.7262064814567566, 0.2437267303466797, -0.7483062744140625, -0.8823292851448059, -0.3050049841403961, 1.1660562753677368, 0.8408584594726562, 0.11099115759134293, 0.36455535888671875, -0.127777099609375, 1.7038167715072632, -0.2699788510799408, -0.35093435645103455, -0.6465861201286316, 0.46808114647865295, 0.3632723391056061, -0.4258168637752533, 0.69024658203125, 0.45428720116615295, -0.3013763427734375, -0.0867818221449852, -1.4675089120864868, -0.64825439453125, 0.3069063723087311, -0.08680597692728043, -0.3582560122013092, -0.18247954547405243, -0.12529627978801727, 1.0089517831802368, 0.1349741667509079, 0.7453816533088684, 0.4602813720703125, 1.2351633310317993, 0.34643808007240295, -1.5093994140625, 1.4429931640625, -0.034515380859375, -1.3183187246322632, 0.15126292407512665, 0.029129663482308388, 0.21430587768554688, -0.2133026123046875, -0.1190236434340477, 0.23760731518268585, 0.43126678466796875, 0.7161152958869934, 1.5077718496322632, -0.4185609817504883, -0.6355956196784973, 0.9713948369026184, 0.2877248227596283, 0.0913238525390625, 0.6784210205078125, -0.15374882519245148, 0.06843694299459457, -0.3964754641056061, -0.0523173026740551, -0.3477376401424408, 0.4029947817325592, 0.0812327042222023, -0.10840606689453125, -0.1739095002412796, 1.2958780527114868, -0.17173893749713898, 0.7425384521484375, -0.4522705078125, 0.2292797565460205, -0.37213134765625, 0.1604512482881546, -0.0728047713637352, 0.31342825293540955, 1.21951162815094, -0.25119781494140625, 0.58453369140625, 0.12288618087768555, 0.7973530888557434, 0.5687662959098816, -0.13468360900878906, -0.5819256901741028, 0.0771433487534523, 0.5094553828239441, 1.6953836679458618, -1.160400390625, 1.1239217519760132, -0.1146952286362648, -0.4405314028263092, -0.5118560791015625, 0.5022252202033997, 0.675994873046875, -0.7140910029411316, -0.5507354736328125, 0.36375555396080017, 0.713134765625, 0.4300180971622467, -0.5163345336914062, 0.91412353515625, 1.2447103261947632, -1.4891763925552368, 0.5981114506721497, -1.1238199472427368, -1.102325439453125, 0.1445872038602829, -0.7781982421875, -0.1560465544462204, 0.493438720703125, 0.9129588007926941, -0.25425466895103455, -0.3137423098087311, -0.328033447265625, -0.5714912414550781, -0.05142974853515625, 0.10125541687011719, 0.8698399662971497, 1.0384927988052368, 0.691680908203125, 0.4427909851074219, 0.5730336308479309, 0.0659128800034523, -1.1330159902572632, 0.987548828125, 0.7295735478401184, 0.0692596435546875, 0.06621106714010239, 0.19123919308185577, 0.5040003657341003, 0.8534647822380066, -0.6014214754104614, 0.0511881522834301, -0.4315163195133209, 1.7880045175552368, 0.02493794821202755, -0.116424560546875, -0.869140625, 0.5697314143180847, 1.10150146484375, 0.4190419614315033, -0.11678632348775864, -0.43274688720703125, 0.7562611699104309, -0.5523783564567566, 0.17251189053058624, -0.08605702966451645, -0.5103594660758972, 0.4410756528377533, 0.6678873896598816, 0.027604421600699425, -0.6173858642578125, -0.630126953125, -1.32373046875, 0.3548685610294342, 0.2611338198184967, 0.13849131762981415, 0.8286539912223816, -0.1135762557387352, 0.6525166630744934, 0.8380126953125, -0.6219990849494934, -1.9994710683822632, 0.77789306640625, -0.4094441831111908, -0.6652755737304688, 0.2520205080509186, -1.0253092050552368, -1.0298868417739868, 0.15057945251464844, -0.1515401154756546, 0.15459473431110382, -0.5674946904182434, 0.15801620483398438, -1.1863199472427368, 0.6682078242301941, 0.1562906950712204, 1.2696533203125, 0.2899576723575592, 0.079071044921875, 0.6068572998046875, 0.047962188720703125, 0.27436065673828125, 0.27594757080078125, -0.2387593537569046, -0.2717742919921875, 1.3524576425552368, 0.10437774658203125, 0.22248585522174835, 0.32891082763671875, -1.0338134765625, -0.0609232597053051, 0.1813405305147171, 0.7509714961051941, -0.9892985224723816, 0.0628458634018898, -0.9223530888557434, 0.3206024169921875, -0.6202386021614075, -0.5449625849723816, 1.1240335702896118, 0.3317464292049408, -1.7744140625, -0.5471928715705872, -0.7765095829963684, -0.6156514286994934, 2.17431640625, 1.7213134765625, -0.59393310546875, -0.1457265168428421, 1.1659342050552368, -0.04110463336110115, -0.395550400018692, -0.2695465087890625, 0.9194539189338684, 0.9482421875, -0.8167164921760559, 0.5495198369026184, -0.6886520385742188, 0.7338969111442566, 0.2010599821805954, 0.5161641240119934, -0.45543670654296875, -0.8298670649528503, -0.8712361454963684, 0.33403778076171875, 0.69580078125, 0.06117502972483635, -0.67938232421875, 0.9957415461540222, 0.22192008793354034, -0.1627451628446579, 0.2737102508544922, 0.09252611547708511, 0.0020968120079487562, 0.707611083984375, 0.1732025146484375, 0.0384877510368824, 0.17525482177734375, 0.84222412109375, 1.106689453125, -0.0379587821662426, -1.521484375, -0.9823048710823059, -0.4673410952091217, -1.05828857421875, 0.9769490361213684, 0.6639811396598816, 0.28308358788490295, 0.4615122377872467, 0.3758530616760254, -0.15025584399700165, 0.2094472199678421, 0.0526784248650074, 0.79901123046875, 0.3347218930721283, 0.20314915478229523, -0.2608133852481842, -0.6615498661994934, -0.3389434814453125, -0.6793721318244934, 0.5084158778190613, 0.3873647153377533, -0.02233290672302246, -0.5186055302619934, -0.760894775390625, -0.68115234375, 0.426922470331192, -0.3046061098575592, -0.5262451171875, -0.022836288437247276, 0.0958760604262352, 0.417449951171875, 0.28819528222084045, -0.967529296875, 0.3128538131713867, -1.2382405996322632, -0.12378004938364029, -0.093017578125, 0.7256978154182434, 0.7319386601448059, -0.4281514585018158, 0.3075040280818939, 0.21090316772460938, -0.30739083886146545, -1.3492227792739868, -0.22938676178455353, -0.13283061981201172, 0.011365254409611225, 0.9151204228401184, -0.061159152537584305, -0.1910247802734375, 0.3497823178768158, -0.6476643681526184, -0.72930908203125, -0.8465474247932434, -0.9588215947151184, -0.2160797119140625, 1.2814534902572632, 0.26100730895996094, 0.6839243769645691, 0.3747965395450592, 0.8323771357536316, -0.080963134765625, -0.0054194130934774876, 0.0388641357421875, -1.6055501699447632, -0.24209976196289062, 0.6577351689338684, -0.85662841796875, -1.4532470703125, 0.3179117739200592, -0.2875773012638092, 0.0447743721306324, 0.10713609308004379, 0.4019978940486908, -0.3546854555606842, -1.0238851308822632, -0.8133366703987122, -0.32708868384361267, 0.4933370053768158, 0.8649190068244934, -0.9549153447151184, 2.5420734882354736, 0.18215100467205048, 0.42684808373451233, -0.2977142333984375, -0.4772224426269531, 0.19373448193073273, 0.9707940220832825, 1.7189127206802368, 0.3000640869140625, -0.516265869140625, 0.2638041079044342, -0.5971934199333191, -0.6274006962776184, -0.47569337487220764, -0.29782357811927795, -0.794830322265625, -1.0034993886947632, 0.23771412670612335, 0.9795735478401184, -1.0279031991958618, 0.23827743530273438, 1.741455078125, 0.49200439453125, 0.05462646484375, -0.7289835810661316, -0.3722686767578125, 0.31543731689453125, -0.1845601350069046, -0.249725341796875, 0.7161865234375, 0.37466683983802795, 0.5873680114746094, 0.5158818364143372, 0.1238149031996727, -0.3362860679626465, 0.8832600712776184, 0.0904693603515625, 0.4276714324951172, -0.5662434697151184, -0.07697805017232895, 0.03152211382985115, -0.17544300854206085, 0.5100809931755066, 1.3313802480697632, 0.08321889489889145, 1.0449447631835938, -0.024380048736929893, -0.9823557734489441, 1.3061116933822632, -0.9071858525276184, -0.1041666641831398, 0.10827621072530746, -0.09961477667093277, -1.2224527597427368, 0.15032704174518585, -0.21794001758098602, 0.0364939384162426, -1.2986654043197632, -0.7669677734375, -1.7806802988052368, 0.7785593867301941, -0.7566731572151184, -0.7763316035270691, 0.005633512977510691, 0.07207298278808594, -1.0458883047103882, 1.0654093027114868, 0.3117828369140625, -1.1837564706802368, 1.4049478769302368, -0.28040313720703125, -1.0626157522201538, -1.2613118886947632, -0.0280176792293787, -0.8428751826286316, -0.17534129321575165, -0.1188608780503273, 0.9818522334098816, 0.8996989130973816, 0.6039835810661316, 0.9674479365348816, -1.1521390676498413, 0.2897860109806061, -0.6782938838005066, 1.2827962636947632, -0.0395253486931324, 0.6263096928596497, 0.0326436348259449, 0.9906209111213684, 1.6742349863052368, 0.3718656003475189, -0.7125701904296875, 0.2829793393611908, -0.317535400390625, 0.48286691308021545, -0.19447200000286102, -1.250885009765625, -0.6531925201416016, -0.9034525752067566, 0.36316999793052673, -0.8144327998161316, 0.4130655825138092, 0.27306365966796875, -0.5557110905647278, 0.3754476010799408, -0.45591482520103455, -0.51270991563797, -0.22149913012981415, 0.20835621654987335, 0.9076945185661316, 0.25875043869018555, -0.23225276172161102, 1.0600992441177368, 0.17433612048625946, 0.8520405888557434, -0.006146907806396484, 0.23042552173137665, -0.40584850311279297, -0.6425374150276184, -0.8506113886833191, 0.9357706904411316, 0.25172170996665955, -0.3324330747127533, -0.10797119140625, 0.3542900085449219, 0.04891395568847656, 0.3438771665096283, -0.6255391240119934, 0.2550630569458008, -0.043856460601091385, -0.43951287865638733, -0.18944613635540009, 0.6298421025276184, 0.9101359248161316, -1.1404622793197632, -0.5668690800666809, 0.24156443774700165, 1.5783284902572632, -0.08997758477926254, 1.1875406503677368, -0.06259409338235855, -0.17979812622070312, 0.108367919921875, -0.6471354365348816, -0.5096028447151184, -1.09320068359375, -0.05364290997385979, 0.1314290314912796, -1.0209401845932007, -0.16899776458740234, 0.0215428676456213, 0.9092203974723816, -0.7894694209098816, 0.68914794921875, -0.37828317284584045, -1.1377969980239868, -0.1597340852022171, 1.1492716073989868, 1.30963134765625, 0.4927622377872467, -0.30545297265052795, 0.8182169795036316, -0.3612823486328125, 0.05615234375, 0.5726242065429688, -0.91241455078125, -0.48729196190834045, -0.9175516963005066, 0.7885182499885559, -0.64471435546875, 0.2984720766544342, 0.5034103393554688, 0.0315450020134449, 0.5729115605354309, -0.4985453188419342, -0.03882789611816406, -1.3108114004135132, -0.827880859375, -0.8145344853401184, 0.0156160993501544, -0.7344303131103516, 1.0556234121322632, 0.0043818154372274876, -0.5675455927848816, -0.0047632851637899876, 0.1246541365981102, -0.3904775083065033, -0.225799560546875, 1.166259765625, -0.019486745819449425, -0.9200897216796875, -0.9666748046875, -0.4253826141357422, -0.3670094907283783, 0.397491455078125, -0.5718485713005066, 2.3291015625, -0.7848103642463684, 1.0823415517807007, 0.2838999330997467, 0.5506489872932434, -0.5133259892463684, -0.8840535283088684, -0.339630126953125, -0.7094268798828125, -0.6303812861442566], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (FastAPI | addresses | rate | limiting | configuration | part | its | guidance)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (API | versioning | implemented | main | py)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (Pydantic | used | alongside | Uvicorn | part | FastAPI | development)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.

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

{'search_vector': [0.19728206098079681, -0.520438551902771, -2.794320821762085, -1.256797194480896, 1.083759069442749, -0.7434269785881042, -0.878126859664917, -0.2733999490737915, 0.2749774754047394, -0.27427321672439575, 0.6404184103012085, -0.12125337868928909, 1.5219351053237915, 0.8894277811050415, -0.193084716796875, -0.891845703125, 0.03572904318571091, -2.453125, -0.231093630194664, 0.265766441822052, 0.49237531423568726, -0.8188664317131042, 0.31621140241622925, -0.6060110330581665, 2.4482598304748535, 0.199737548828125, -0.21996274590492249, 0.051524821668863297, -0.2551809549331665, -0.47793343663215637, 0.49949997663497925, -0.07732684910297394, 0.8793287873268127, 0.3455106317996979, 0.4691373407840729, -0.7447415590286255, 0.7045710682868958, -0.8665771484375, -0.5681340098381042, 0.4213092625141144, -0.3807842433452606, 0.7027869820594788, 0.644118070602417, -0.42559814453125, 0.28619384765625, -1.195575475692749, 0.543287992477417, 0.32448166608810425, 0.9825251698493958, -0.9329881072044373, 0.506788969039917, 0.2638009786605835, 0.5380507111549377, -0.4760061502456665, 1.7905648946762085, 0.7846491932868958, -1.2038949728012085, 0.7593899965286255, -0.43438720703125, -0.9667686820030212, 1.184476375579834, 1.366549015045166, -0.5659742951393127, 1.647122859954834, 0.18556565046310425, 0.020608168095350266, -0.5896278023719788, 0.53619384765625, -0.26253098249435425, -0.30642464756965637, -0.1605561375617981, -0.36688232421875, 0.3362285792827606, -0.3335125148296356, 0.36500078439712524, -0.19055058062076569, -0.5154747366905212, -0.6491981148719788, -0.52496337890625, 1.381572961807251, -0.04348989576101303, 0.427154541015625, 0.7535212635993958, -0.7690054178237915, 1.7335110902786255, -0.8540884256362915, -0.07494647800922394, 0.10276912152767181, -1.9427584409713745, 1.123798131942749, -0.516387939453125, -0.2610767185688019, -0.5892991423606873, -0.2764047384262085, -2.065260648727417, -0.510178804397583, -0.9656324982643127, 0.6327749490737915, -0.5666075348854065, 0.7977107167243958, -0.17167076468467712, 0.25454801321029663, -0.14398428797721863, -0.679912269115448, 0.4308236837387085, 0.7355862855911255, 0.05021902173757553, 0.8837890625, -0.09241016209125519, 0.21215584874153137, 0.08654432743787766, 1.11749267578125, 0.8740140199661255, 0.18866436183452606, -0.6631985902786255, -0.5200430154800415, 0.8573373556137085, 0.7082716226577759, -0.08922268450260162, 0.8089834451675415, -0.7331947684288025, -1.321439266204834, 0.11740827560424805, 1.0693734884262085, -0.15849289298057556, -0.982252836227417, -1.584059476852417, -0.45446306467056274, 0.3924466669559479, -0.738525390625, 0.04892906919121742, -0.04414837062358856, -0.5213904976844788, 0.09237083792686462, 0.47797101736068726, 1.7505258321762085, 0.23345477879047394, -1.171126127243042, -0.23044174909591675, 0.23101043701171875, -0.30238401889801025, 0.04763559252023697, -0.29475051164627075, 0.536521315574646, 0.7281376719474792, -0.5314158201217651, 1.172137975692749, -0.24827633798122406, 0.19143441319465637, 1.1346200704574585, -0.22414691746234894, 0.5423161387443542, -0.08443040400743484, 0.44613412022590637, 0.3484661281108856, -0.22182171046733856, 0.8531681895256042, 0.3498910665512085, 0.9051607847213745, -0.3066030740737915, 0.18773826956748962, -0.27481549978256226, -0.21116286516189575, 0.09882413595914841, -0.43243408203125, -0.05538705736398697, -0.3238431513309479, 0.38550275564193726, -0.6456416249275208, 1.0315505266189575, -0.8868690133094788, -0.15370295941829681, -0.2940767705440521, 0.2576059103012085, -0.8009220957756042, 0.5632892847061157, 0.5325645804405212, -0.12027681618928909, 0.33557069301605225, -0.11044956743717194, -0.4251708984375, -1.4532376527786255, -1.028958797454834, 0.671555757522583, -0.7500375509262085, 0.22808720171451569, 0.29220345616340637, -1.021240234375, -0.40447527170181274, -0.7571739554405212, 0.5816662311553955, 0.18940617144107819, -0.7611412405967712, -0.404296875, -1.632061243057251, -0.7409292459487915, 0.4863727390766144, -0.2271728515625, 0.6298218965530396, -0.5912428498268127, -0.19018027186393738, -0.8657414317131042, -0.30335763096809387, -0.08748157322406769, -0.9343824982643127, 0.17981426417827606, -0.347342848777771, 0.3963716924190521, -0.06851489841938019, 0.6654381155967712, 2.153902530670166, -0.18433615565299988, -0.010197565890848637, -0.4909292459487915, 0.32256609201431274, -0.022612351924180984, -0.11209575831890106, -0.5912710428237915, 0.17154400050640106, 0.387603759765625, 0.5281254649162292, -0.09039665758609772, -0.12918208539485931, -0.6844294667243958, 0.620086669921875, 0.5020094513893127, -1.1006423234939575, -0.47832781076431274, 0.1665109544992447, -0.08701734989881516, 0.596307635307312, -1.895432710647583, 0.022965651005506516, 1.2745455503463745, 0.1673044115304947, 0.8643516898155212, -0.6821852326393127, 0.6493735909461975, 0.830047607421875, -0.05641761049628258, -0.14043954014778137, 0.258636474609375, 0.2503803074359894, 0.807326078414917, -0.39846566319465637, 0.306546151638031, 0.2018808275461197, -0.22636325657367706, -0.4109943211078644, 1.375751256942749, -0.6601750254631042, -0.7449951171875, 0.7890507578849792, 1.3730844259262085, -0.1498788744211197, -1.2755221128463745, -0.04480684548616409, -0.04372934252023697, 0.47532302141189575, -0.4848797023296356, 0.13692063093185425, 0.17474834620952606, 0.45210030674934387, -0.5458045601844788, 1.1384652853012085, 0.272987961769104, 0.24720412492752075, 0.051207322627305984, 0.36446908116340637, 0.26926130056381226, 1.0448092222213745, 0.5903836488723755, -0.844482421875, -0.09718675166368484, 0.0628715306520462, 0.8076829314231873, 0.6541653871536255, 0.5739840269088745, -0.5980882048606873, 1.1660531759262085, -0.292634516954422, -0.9487985372543335, -0.47656720876693726, 0.38662368059158325, 1.15966796875, 0.4134145975112915, -0.15370765328407288, -1.1396859884262085, -0.10491708666086197, 0.18608210980892181, 0.665185809135437, -0.36273443698883057, -0.3739177882671356, 0.2607327997684479, -0.036469679325819016, -0.2837870717048645, 0.3219451904296875, 0.28519850969314575, 0.07507793605327606, -1.1705914735794067, 0.673583984375, 0.6266432404518127, 1.0102298259735107, 0.5578519105911255, 1.2511550188064575, -0.12941917777061462, 0.17135855555534363, 0.14609703421592712, 1.103853702545166, 0.34951546788215637, 0.9375698566436768, 0.6104736328125, -1.5205078125, 1.0526779890060425, -1.2305814027786255, 0.9291334748268127, 0.09110318869352341, 0.11902324855327606, 1.2511080503463745, -0.43520882725715637, -0.024423452094197273, -1.49609375, -0.62841796875, -0.48105093836784363, 0.44774216413497925, -0.10367760062217712, 0.06501417607069016, 1.774564266204834, -0.21111679077148438, 0.14092548191547394, 0.7006272673606873, -0.710862398147583, 0.09066185355186462, -1.280498743057251, 0.6361178159713745, 0.44534653425216675, 0.2087331861257553, 0.6553767323493958, 0.004009540192782879, 1.1521559953689575, 1.4619680643081665, -0.918961763381958, 0.09081561863422394, -0.789922297000885, -0.18942496180534363, -0.9909949898719788, 0.024694589897990227, 0.18642425537109375, 0.5550819039344788, 0.7640944123268127, 0.02736135572195053, 0.8258009552955627, -0.00919342041015625, 0.4666748046875, 0.334511399269104, -0.6334111094474792, -0.04847247898578644, 0.33340689539909363, 0.19126540422439575, 0.02518169768154621, 1.4075270891189575, -0.19357064366340637, 0.5836463570594788, -0.28903433680534363, 0.92095947265625, 0.9362663626670837, 0.23143240809440613, -1.10693359375, 0.846510648727417, -0.2520751953125, 0.08917001634836197, -0.22956496477127075, 0.2018667310476303, 0.5630915760993958, 0.2156606763601303, -0.6953500509262085, -2.143629789352417, 1.370999813079834, -0.5355400443077087, 0.7483848929405212, 1.190354585647583, -0.44102126359939575, 0.635178804397583, 0.49795767664909363, 0.16688655316829681, -0.33173078298568726, 0.32718130946159363, 0.3462360203266144, -0.04807222634553909, 0.896575927734375, 0.7913630604743958, -0.33410879969596863, 0.49714308977127075, 0.678908109664917, 0.5176292061805725, 0.4535053074359894, 0.29803556203842163, -0.3199932277202606, 0.014216496609151363, 0.49728628993034363, -1.7974008321762085, -0.7610989809036255, 0.8822303414344788, -0.3526235818862915, 0.1335824877023697, -0.10263883322477341, -0.7277244925498962, -1.013089656829834, 0.8949256539344788, -1.2702261209487915, 0.3727346658706665, 0.9206730723381042, -0.3544851541519165, -1.6977914571762085, 0.5775146484375, -0.3747347295284271, 0.5310856699943542, 0.3446796238422394, -1.2173221111297607, -0.18948422372341156, 0.834580659866333, -0.08283878862857819, 0.21705862879753113, 0.868896484375, 0.04280912131071091, 0.8279841542243958, 0.7229379415512085, 0.546980619430542, 1.397122859954834, -2.708984375, 0.13291403651237488, 0.2491384595632553, 0.3669809103012085, 0.0070706880651414394, -0.7534273862838745, -0.6470900177955627, 1.1748340129852295, 0.3994891941547394, -0.33964890241622925, 0.16301316022872925, 1.24462890625, -0.2063058763742447, -1.0706692934036255, -0.28710702061653137, 0.09587684273719788, 1.5852144956588745, 0.5249305367469788, -1.456279993057251, 0.015124247409403324, 0.5785035490989685, 0.987135648727417, -0.6037315726280212, 0.9158090353012085, 1.060260534286499, 1.3798452615737915, -0.44022077322006226, 0.531762957572937, 0.17276352643966675, 0.022126417607069016, 0.5127915740013123, 1.221454381942749, 0.6203848123550415, -1.2042142152786255, 0.3410392105579376, 0.4840043783187866, 0.19479605555534363, -0.609266996383667, -0.559118390083313, 0.438906729221344, 0.22101065516471863, -1.712252140045166, -1.3731225728988647, 0.8753145933151245, 0.025526780635118484, -0.16587477922439575, 0.6157084107398987, 0.437305748462677, -0.08356182277202606, 0.6087012887001038, 0.6365779042243958, -0.7200645804405212, -0.7710524201393127, -0.7052823305130005, -0.511449933052063, -0.553969144821167, 0.12008901685476303, 0.3648681640625, -0.3128873407840729, -0.5737069845199585, 0.08181058615446091, 0.2795928418636322, 0.40632277727127075, 1.110858678817749, 0.2723199129104614, -0.5217041373252869, -0.45879656076431274, -0.43649527430534363, -0.02766888029873371, 0.9528996348381042, 0.15451519191265106, 0.594773530960083, 1.233867883682251, 0.9393967986106873, -0.43459612131118774, 0.24993896484375, -0.13242164254188538, 1.3385220766067505, -0.1252899169921875, -1.233736515045166, -0.035460252314805984, 1.2269192934036255, -0.051169175654649734, -0.06710111349821091, 0.7353515625, 0.23080679774284363, -0.7603665590286255, -0.24384014308452606, 0.5375131368637085, -1.0371657609939575, -1.0346087217330933, 0.05621807277202606, -0.9173176288604736, 0.8145751953125, -1.3562575578689575, -0.955857515335083, 0.8329315185546875, 0.1219065710902214, -0.9143934845924377, 0.9180344939231873, -0.5345529317855835, -0.33876916766166687, -0.4877166748046875, -0.2873159646987915, -0.5568286776542664, -0.730923593044281, 0.23509685695171356, -1.8303786516189575, 0.8746760487556458, 0.20946326851844788, 0.29363030195236206, 0.15762093663215637, 0.10125732421875, -0.17803016304969788, 0.07874591648578644, -0.23591144382953644, -0.30055588483810425, -0.574293851852417, 0.5410884022712708, 0.31979429721832275, -0.7404597401618958, 2.670297384262085, -0.4013836085796356, 0.17986591160297394, -0.25703489780426025, 0.47640755772590637, 0.022718869149684906, 0.07693246752023697, -0.9030163288116455, -0.561279296875, -0.06183330714702606, 0.9129732847213745, 0.10433725267648697, 1.2166842222213745, -0.08693753927946091, 0.38793709874153137, -0.39232590794563293, -0.2685365080833435, -0.06896928697824478, -0.36786359548568726, 1.249248743057251, -1.1492074728012085, -0.5914822816848755, 0.20362472534179688, 0.025036152452230453, 0.8013117909431458, 0.14228469133377075, -0.14094895124435425, 0.16571514308452606, -0.8871556520462036, -0.5515230894088745, -0.16837722063064575, -0.5293250679969788, 0.15023685991764069, 0.38708025217056274, -0.3463533818721771, 0.11888709664344788, -0.10250150412321091, -0.4010526239871979, 0.09243539720773697, 0.023850660771131516, 0.4198232889175415, 0.46055251359939575, -0.030546922236680984, -0.16358830034732819, 0.1777883619070053, 0.5837449431419373, -0.8022508025169373, 0.19745811820030212, 0.24793770909309387, -0.8572845458984375, 0.016639122739434242, -0.29254502058029175, 0.3527315557003021, -0.3271484375, -0.59375, 1.230562686920166, -0.3853759765625, -0.13006356358528137, 0.696580171585083, -0.06960707157850266, 0.5943791270256042, -0.9308894276618958, -0.5574246644973755, -1.158128023147583, 0.9488149881362915, -1.471210241317749, 0.22160457074642181, 0.565690279006958, 0.1251596361398697, -1.2399338483810425, -1.089241623878479, -1.2748647928237915, 1.231295108795166, -0.2959735691547394, 0.46678513288497925, -0.06934767216444016, -0.43903058767318726, -0.48122113943099976, 0.9234243631362915, 1.4075270891189575, -0.03946626931428909, 0.33818289637565613, -2.2333984375, -0.4992769658565521, -1.582782506942749, -0.7267221212387085, -0.15736740827560425, 0.3438098728656769, -0.11924861371517181, 0.6217322945594788, 1.8854416608810425, -0.18383143842220306, 0.5571805238723755, 0.44914597272872925, 0.35701340436935425, -0.7041943073272705, -0.40990734100341797, 1.089092493057251, 0.14520028233528137, -0.25693923234939575, 0.8496798276901245, 1.073392391204834, 0.1035502478480339, -0.18303386867046356, 0.21967609226703644, -0.007690723054111004, 0.0631754919886589, -1.0857497453689575, -1.538311243057251, -0.5047091245651245, -0.10612135380506516, -0.9530123472213745, -0.25231698155403137, 0.38889724016189575, 1.104539155960083, 0.20469753444194794, 0.14681771397590637, 0.08419565111398697, -0.7098482847213745, -0.9448524117469788, 0.21824821829795837, 0.19537353515625, -0.37241774797439575, -0.678635835647583, 0.6886831521987915, 0.4646841287612915, 0.6678091287612915, -0.27871468663215637, -0.7074819803237915, -0.6336951851844788, -0.00734960101544857, 0.555029034614563, 0.7830716371536255, -0.41951048374176025, -0.08783134818077087, -1.722318172454834, 0.14186447858810425, -0.3539968729019165, -0.7548311948776245, -0.826002836227417, -0.4502047002315521, -1.0071364641189575, 0.19334998726844788, -0.0006619967170991004, -0.23967978358268738, 0.11563345044851303, 0.2983304560184479, -0.3390737771987915, -0.4183402359485626, 0.5208740234375, -0.2164541333913803, 0.06530174612998962, 0.634505033493042, 0.39638108015060425, -0.0015200101770460606, -0.24476036429405212, -0.22392360866069794, -0.5297804474830627, -0.12181209027767181, -1.533128023147583, -1.6661282777786255, 0.031015248969197273, -0.5761671662330627, 0.9349635243415833, 0.11891526728868484, 0.7398590445518494, 0.20598895847797394, -1.081595778465271, -0.37022048234939575, 0.2518761456012726, 1.0084322690963745, 0.342384934425354, -1.3672250509262085, 0.187215656042099, 0.4468547999858856, -0.1361541748046875, 0.97265625, -1.422137975692749, 0.08439753949642181, -0.38040396571159363, 0.42580002546310425, 0.41964957118034363, -1.2562350034713745, 0.45525243878364563, -0.3515859842300415, -0.9201472401618958, -0.6217698454856873, -0.3740703761577606, -0.956528902053833, -1.0506685972213745, -0.8698777556419373, -0.351127028465271, -0.27187874913215637, 0.8607835173606873, -0.893507719039917, 1.443997859954834, -0.4304035007953644, 0.7629206776618958, -0.07666954398155212, -0.8558631539344788, 0.27447956800460815, -0.7241539359092712, -0.8254206776618958, -0.2653433084487915, -0.7442532777786255, -0.5106106996536255, 0.81787109375, 1.0873746871948242, 1.4763747453689575, 0.3412311375141144, 0.06036376953125, -0.15630486607551575, 0.5816673636436462, -0.06073937192559242, -0.5418795347213745, -0.638535737991333, -1.0167893171310425, -0.3689058721065521], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (FastAPI | concerns | itself | request | handling | endpoint | routing)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.

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

{'search_vector': [0.24579516053199768, 1.338623046875, -3.1468393802642822, -0.6573153138160706, 0.9909889698028564, -1.3470348119735718, 0.7642489075660706, -0.6650834679603577, 0.21049360930919647, -0.8912464380264282, -0.1421051025390625, 0.38704195618629456, 1.5573508739471436, 0.5362825989723206, -0.06938700377941132, 0.4153941869735718, 0.46795654296875, -0.6375621557235718, -0.331943154335022, 0.025254683569073677, -0.10588905960321426, 0.24850741028785706, -1.3440607786178589, 0.4980357885360718, 1.3607732057571411, -0.5111472606658936, 1.0746182203292847, -0.09366676956415176, -1.7357066869735718, -1.517578125, 1.938432216644287, -0.4639733135700226, 0.3234752416610718, -0.8636030554771423, 0.39475318789482117, -1.050537109375, 0.6636407971382141, 0.6869673132896423, -0.3015185594558716, 0.8166725635528564, -0.5357000231742859, 0.8346168994903564, 0.7201038599014282, 0.37124910950660706, 0.4975475072860718, 0.5540993213653564, 1.0945934057235718, -0.18738903105258942, 0.7157703638076782, -0.9308915734291077, -0.19102062284946442, -0.7429420948028564, 0.2847484350204468, -1.0755947828292847, 1.439897060394287, 0.6186634302139282, 0.3464219868183136, 1.0001109838485718, -0.7787198424339294, -0.21461625397205353, 0.8068403601646423, 0.17464932799339294, -0.8548139929771423, 1.9190119504928589, 0.7259174585342407, 0.8427734375, -0.7910489439964294, 0.9659534692764282, -0.5380803942680359, -0.2822210192680359, 0.2705979645252228, -0.8493874073028564, 0.7375155091285706, 0.31045255064964294, 0.4334217309951782, 0.08878950774669647, 0.02852838672697544, -0.9163707494735718, 0.06792103499174118, 0.9050514698028564, -0.22451505064964294, 0.18838223814964294, 0.39288330078125, -0.3770807385444641, 0.5153309106826782, -0.3195689916610718, -0.59844970703125, -0.04821222648024559, -0.6787775158882141, 0.9798473119735718, 0.46151456236839294, 0.3133752942085266, 0.22283796966075897, 0.5275226831436157, -0.9564985632896423, 0.547950029373169, -0.5056068897247314, 0.7952769994735718, -1.8312321901321411, -1.1072887182235718, 0.09015447646379471, 0.39707252383232117, 0.7761563658714294, -0.4182572662830353, 0.070556640625, 0.2049505114555359, -0.17421826720237732, -0.07069813460111618, 0.5344571471214294, 0.876220703125, -0.33555880188941956, 0.5782463550567627, 0.5932506322860718, -0.8528941869735718, -0.36797818541526794, -1.3981267213821411, 0.3368363678455353, -0.37832918763160706, 0.6668367981910706, 0.7482133507728577, -0.3947892487049103, -1.1724964380264282, -0.6012296080589294, 1.0199973583221436, -0.04251514747738838, -0.018599076196551323, -0.9540349841117859, 0.20559969544410706, -0.16123685240745544, -1.6305485963821411, 0.1233239620923996, -1.297407627105713, -0.9093128442764282, -0.4289717376232147, 0.364471435546875, -0.6195734143257141, -0.6406221985816956, -0.556396484375, 0.09541008621454239, 0.22453723847866058, 0.15833768248558044, 0.6782281994819641, -0.29181548953056335, -0.6044533252716064, -0.11404592543840408, -0.8135209679603577, 0.7868208289146423, -0.3255670666694641, 0.02957708202302456, 0.011023781262338161, 0.07002570480108261, 1.3869850635528564, 0.31314709782600403, 1.6457741260528564, -0.5844005346298218, 0.006432272959500551, -0.08513294905424118, -0.06660184264183044, 1.0703125, 0.6109285950660706, 0.9599165320396423, -1.0178583860397339, -0.11704011261463165, 0.7396129369735718, -0.2578901946544647, -0.5309614539146423, 0.7897283434867859, 1.2958984375, 0.25646695494651794, 1.663041591644287, -0.3370923101902008, -0.6155617237091064, -0.8908802270889282, -0.8684276342391968, 1.2183948755264282, -0.5753423571586609, -0.18800145387649536, -0.9476041197776794, 1.569047451019287, -0.5610101819038391, -0.5301492810249329, -1.2042347192764282, 0.4203435778617859, 0.03159886971116066, -0.4909757375717163, 0.5260065197944641, 0.7307018041610718, -0.08578214049339294, -0.7649924755096436, -1.3727360963821411, 0.9646217823028564, 0.6645063757896423, -0.9192699193954468, -0.5606245398521423, -1.4148615598678589, -0.21665261685848236, 1.238725185394287, 0.673095703125, 0.5663618445396423, -0.42682144045829773, 0.2833057641983032, 0.47556790709495544, -0.4193587005138397, -0.5959028601646423, 0.41561058163642883, -0.19743451476097107, 0.8463467955589294, -0.4714799225330353, -0.6536976099014282, 0.38059303164482117, 1.3352383375167847, 0.2650396227836609, -1.1275523900985718, 0.1753227859735489, 1.0848056077957153, 0.12100989371538162, 0.17748190462589264, -0.4815230071544647, 0.2329046130180359, 0.22205699980258942, 1.8496981859207153, -0.20942549407482147, 0.06793212890625, -1.2674227952957153, -0.461669921875, 0.17448841035366058, -1.7303799390792847, -0.5328999161720276, -1.067582607269287, 0.32510653138160706, -0.64837646484375, -1.1917613744735718, 0.04033314064145088, 0.32781982421875, 0.20623917877674103, 0.16263650357723236, 0.2975548803806305, 1.219071865081787, 0.33420422673225403, -0.6209161877632141, -0.5056846141815186, -0.5203524231910706, -0.8782848119735718, 0.5603693127632141, -1.4418460130691528, 0.17143110930919647, -0.9533802270889282, -0.5439563989639282, -0.5048703551292419, 1.0811434984207153, -0.018755478784441948, 0.4545912444591522, 0.03265935555100441, -0.7296919226646423, -0.19678358733654022, -0.013069846667349339, 0.34990137815475464, -0.6199840307235718, 0.6467729210853577, -0.5908758044242859, 1.05322265625, -0.5305647253990173, -0.28788062930107117, 0.315338134765625, 0.17113147675991058, -1.1200450658798218, 0.9846857190132141, 0.5548012256622314, -0.23180042207241058, -0.5097302794456482, 0.40725985169410706, 0.8544034361839294, 0.7226340770721436, 0.29012784361839294, 0.6046919226646423, 0.2585698962211609, 0.009016557596623898, -0.35848721861839294, -0.5718217492103577, 1.3200905323028564, -0.70068359375, -1.1572265625, -0.6879078149795532, 0.22978349030017853, -0.24085165560245514, 0.4595170319080353, 0.021351207047700882, 0.2881150543689728, 0.5682927966117859, 0.2886962890625, 1.955078125, -0.4175581634044647, -1.6941584348678589, 0.7512567639350891, -0.7412664294242859, -0.06996848434209824, 1.130171298980713, -0.4757190942764282, 0.6295166015625, -0.11894642561674118, 0.19871382415294647, 0.2959095239639282, 1.5570400953292847, -0.2879527807235718, 0.3410894274711609, -0.7412034869194031, 0.4308360815048218, -0.29090186953544617, 0.6409912109375, 1.0550426244735718, -0.23059359192848206, 0.35603436827659607, -0.4132246673107147, 0.20034512877464294, -0.5530062317848206, 1.1536976099014282, 0.6301324963569641, 0.8172940611839294, 0.6716419458389282, 0.5752508044242859, -0.32717618346214294, -0.7783480286598206, 0.023288726806640625, 0.5139604210853577, 0.24385763704776764, 0.021939365193247795, -0.5325372815132141, 0.3732355237007141, -0.12972329556941986, -0.3399852514266968, -0.28050926327705383, 0.09576693177223206, 0.6744051575660706, -0.6310036182403564, -1.2808948755264282, 0.26054659485816956, 0.8618608117103577, 0.5460482239723206, -0.37136077880859375, 0.29574307799339294, 1.303022861480713, -1.8917790651321411, 1.97265625, -2.267489433288574, -0.8175382018089294, -0.08924449235200882, 0.6802117228507996, -0.3151078522205353, 1.0904430150985718, 0.39620140194892883, -0.756591796875, 1.122758388519287, -0.5717856884002686, -0.6225475072860718, 0.09638283401727676, -0.4590343236923218, 1.6424449682235718, 1.1021728515625, 0.08829290419816971, 0.05809992179274559, 1.1747825145721436, 0.10127119719982147, 0.46597567200660706, -0.4952281713485718, -0.3948475122451782, 0.30267074704170227, 0.3800215423107147, -0.3862804174423218, 0.15914639830589294, -0.1097564697265625, 0.15669389069080353, -0.8089488744735718, -0.7964532971382141, 0.044638894498348236, -0.5837624073028564, 0.20626553893089294, -1.5628107786178589, -0.9858787059783936, -0.9073930382728577, -0.20570096373558044, 0.20007982850074768, 0.14833484590053558, 0.3110406994819641, 0.8278642296791077, 0.49635037779808044, -0.5346457958221436, 0.06568215042352676, 0.5292524695396423, 0.3615611791610718, 0.3275257349014282, 1.033158779144287, -0.7563587427139282, -0.8614280223846436, 0.9025157690048218, 0.0063067348673939705, -0.6003196239471436, 0.4132218658924103, -0.20222888886928558, 0.03285355865955353, 1.381819248199463, -1.4103337526321411, -1.2297751903533936, 0.03980601951479912, -1.3698508739471436, -0.6201837658882141, 0.18437471985816956, -1.1035377979278564, -0.9933860301971436, 0.986328125, -0.5296519994735718, 0.20001359283924103, -0.4445953369140625, 0.3917957544326782, -0.44900789856910706, 0.01373776514083147, 0.4968982934951782, 0.6435657739639282, -0.38869962096214294, 0.33434781432151794, -0.692138671875, -0.5651528835296631, 0.24978360533714294, 0.8145807385444641, 1.1967551708221436, -0.22431807219982147, 0.5411598682403564, 0.6875, 1.3960849046707153, -0.166900634765625, -1.158979892730713, 0.2028399407863617, 0.17973189055919647, 1.368607997894287, -1.2080868482589722, 0.03376353904604912, -0.6977983117103577, -0.10631491988897324, 0.6198952198028564, 0.3762262463569641, 0.3607593774795532, 0.42185279726982117, 0.4483046233654022, -0.9105668663978577, 0.3116898834705353, 0.019326860085129738, 2.8802378177642822, 1.1573264598846436, 0.2745194733142853, 0.16615711152553558, 0.6573153138160706, 0.3216996490955353, 0.10849276185035706, -0.16385650634765625, 1.0568625926971436, 0.9928533434867859, 0.08997449278831482, -0.8363869190216064, 0.7238492369651794, 1.1066228151321411, -0.26861572265625, 0.7197709679603577, 1.1960670948028564, -2.1798651218414307, -0.05195201560854912, -0.1560918688774109, -0.3360803723335266, 0.8115678429603577, 0.4678455591201782, 0.9888361096382141, 1.274214267730713, -0.4213756322860718, -0.18884658813476562, 0.5714388489723206, 0.07438313215970993, 0.48715832829475403, 0.8860639929771423, -0.6592573523521423, 0.21009133756160736, -0.034279562532901764, 0.9183016419410706, -0.6417735815048218, 0.20219837129116058, -0.3561567962169647, -0.24899014830589294, -0.02948552928864956, -0.2773909270763397, 0.36920166015625, -0.7021761536598206, 0.34633705019950867, 0.2276611328125, 0.4340348541736603, -0.22412942349910736, 1.0806773900985718, 0.9618003368377686, 0.49987098574638367, -0.1965581774711609, 0.08775746077299118, -0.09888804703950882, -0.21227194368839264, -0.32357510924339294, 0.09504561126232147, 0.6476163268089294, -0.6219940185546875, -1.2731711864471436, 1.0049937963485718, -0.6680631041526794, 0.35759657621383667, -0.5376920104026794, 0.5209472179412842, 0.18921314179897308, -0.09292879700660706, -0.3919011950492859, 0.24461503326892853, 0.027671121060848236, 0.4061986804008484, -0.10167668014764786, 1.0257900953292847, -0.6924715638160706, -0.2877197265625, -0.06685014069080353, -0.6806751489639282, -0.7894081473350525, -0.18420687317848206, -0.8941761255264282, -1.1202946901321411, 0.041861794888973236, 0.6514559388160706, -0.046364523470401764, 0.812744140625, 0.174560546875, -0.04259837791323662, 0.7780706286430359, -1.4611150026321411, 0.23963789641857147, 0.05983109772205353, -0.36128929257392883, -1.2580695152282715, 0.8460804224014282, 1.5506037473678589, 0.8834783434867859, 0.8417524695396423, 0.21031397581100464, -0.258148193359375, -0.031824979931116104, 0.08043878525495529, -0.3718927502632141, 0.3963678479194641, 0.6575872302055359, -0.5586159229278564, -0.5632379651069641, 1.091203212738037, -1.4752308130264282, -0.47604092955589294, -1.1432439088821411, 0.2158563733100891, 0.4080977141857147, 0.027405478060245514, 0.3316705822944641, 0.3820134997367859, -0.22788862884044647, 0.8066295385360718, 0.23649458587169647, 0.3591253161430359, 0.023215554654598236, -0.8139121532440186, -1.4454013109207153, 0.046114835888147354, -0.8970281481742859, -0.04361378028988838, 0.6715421080589294, 0.20547208189964294, -0.6208717823028564, -0.08318328857421875, 0.4154413342475891, 0.460845947265625, -0.15868498384952545, 0.35904207825660706, 0.3148665130138397, -0.11031272262334824, -0.8731800317764282, 0.1647893786430359, -0.5145984888076782, -0.05100874602794647, 0.19099287688732147, 0.4976029694080353, -0.5476740002632141, -1.023359775543213, -0.3560430407524109, -0.26628389954566956, -0.35923072695732117, -0.5831798315048218, -0.4448907971382141, -0.6727849841117859, -1.2910377979278564, 0.6228346228599548, 0.14046408236026764, -0.7009832262992859, 0.21546520292758942, 0.04397444427013397, -0.2101384997367859, -0.12147105485200882, -0.3270208239555359, 0.7006502747535706, -0.19571755826473236, -0.4232177734375, 0.6079212427139282, 0.5332801342010498, 0.23690518736839294, -0.3210431933403015, -0.4418889880180359, 1.6159001588821411, -0.7067316174507141, -1.0317035913467407, -0.068511962890625, 0.7067010998725891, -1.072709560394287, 1.111860752105713, -0.20224276185035706, -0.5810602307319641, 0.6751154065132141, -0.732421875, -1.0379527807235718, 0.5038729310035706, -1.2625621557235718, -0.016751376911997795, -1.141557216644287, -0.4031316637992859, 0.04960493743419647, 0.2536121606826782, -0.7005504369735718, 0.045768044888973236, 0.2454279065132141, -0.04855485260486603, -1.3000710010528564, -1.404829502105713, 0.7670454382896423, -0.3198505640029907, -0.21392683684825897, 0.10256680846214294, 0.7767167687416077, 1.0184992551803589, 0.5794344544410706, 0.2650895416736603, -0.16833852231502533, 0.6221646666526794, 0.15745283663272858, 0.2559148669242859, 0.64501953125, 1.1652165651321411, 0.3476063013076782, 2.007768154144287, 1.3509854078292847, 0.6174649596214294, 0.19657205045223236, 0.4917435944080353, -0.35991114377975464, 0.6526766419410706, -0.7254305481910706, -0.6003084778785706, -0.08051507920026779, 0.593105673789978, -0.5380277037620544, -0.11425226181745529, -1.081587314605713, 1.4202769994735718, 0.40061673521995544, 1.276533603668213, -0.36849698424339294, -1.1097744703292847, 0.17358537018299103, -0.09007540345191956, 0.16150735318660736, -0.8167710900306702, -0.9779163599014282, 1.0350674390792847, -0.06288840621709824, 1.0184658765792847, -0.046363137662410736, -0.9532803893089294, -0.02389318309724331, -0.5633683800697327, -0.2576349377632141, 0.7461381554603577, 0.6176313757896423, -0.7531654834747314, 0.2697088122367859, 0.8486993908882141, -0.39736661314964294, 0.123779296875, -0.44254857301712036, -1.115034580230713, -1.176513671875, -0.8288629651069641, -0.06895793229341507, 0.4018998444080353, -0.06656160950660706, -0.9417280554771423, -0.42617520689964294, -0.5458781719207764, 0.5961248278617859, -0.6003251671791077, 0.7756680846214294, 0.49908447265625, 0.8766090869903564, -0.6434825658798218, -0.2954212427139282, 0.42887184023857117, -0.2015838623046875, 0.3475910425186157, -0.2656243145465851, -0.9252437353134155, 0.15466031432151794, -0.4079756438732147, 0.4037059545516968, -0.20424166321754456, -0.07197432219982147, -0.6685981750488281, -1.1580699682235718, -0.6804698705673218, -0.07102827727794647, 0.8916917443275452, 0.06967718154191971, -1.1040927171707153, -0.7383700013160706, -0.5055042505264282, -0.36658409237861633, 0.28753939270973206, -0.1908971667289734, 0.04983381927013397, -0.9131303429603577, 0.1680096685886383, -0.8487659692764282, -0.8272926807403564, 0.6321355700492859, -0.8407759070396423, 0.6996959447860718, -0.7732044458389282, -1.1926935911178589, -1.7987393140792847, 0.37797996401786804, -0.6021312475204468, -0.4299677014350891, -0.7211109399795532, 1.0641423463821411, -0.6065118908882141, -0.6932039856910706, -0.11197454482316971, 0.8949390649795532, 0.9025490283966064, -0.21788857877254486, 0.8864856958389282, -0.7337202429771423, -1.4931640625, 0.48717984557151794, 0.09715132415294647, 0.4952753186225891, -0.6247780323028564, 0.1701056808233261, 2.3386008739471436, -0.34097567200660706, 1.6376953125, -0.4657149016857147, 0.6964333057403564, -0.6366077661514282, 0.13658557832241058, -0.4745316803455353, -0.18861736357212067, -0.6714966297149658], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.

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

{'search_vector': [-0.05552063137292862, 0.7381347417831421, -3.767578125, -0.2608669400215149, 1.4294312000274658, -1.295141577720642, -1.0698531866073608, -1.1782439947128296, -0.5989929437637329, -1.0490233898162842, 1.7903320789337158, 0.15956802666187286, 1.9385986328125, -0.11819954216480255, -0.11380310356616974, 0.7697814702987671, 0.3634018003940582, 0.02750396728515625, -0.5054931640625, -0.41219767928123474, -1.1025497913360596, -1.1510498523712158, -0.33185118436813354, 0.7130783200263977, 0.8603614568710327, 0.11358642578125, 0.447317510843277, 0.37436333298683167, -0.5898376703262329, -1.0562744140625, 2.3161957263946533, -0.20250244438648224, -0.561309814453125, -0.2725204527378082, -0.254241943359375, -0.3664611876010895, 1.480316162109375, 0.4938507080078125, -0.32791727781295776, 0.3347229063510895, -0.14103126525878906, 1.735620141029358, 0.8927574157714844, 0.05584373325109482, 0.7666870355606079, -0.13459166884422302, -0.09981460869312286, -0.019411468878388405, 0.36610108613967896, -0.5259441137313843, 1.076727271080017, 0.061409782618284225, -0.719744861125946, -0.940417468547821, 0.510986328125, 0.6521129608154297, 1.0359290838241577, -0.261514276266098, -0.1611616164445877, 0.03740539401769638, 0.3105529844760895, 1.0088989734649658, 0.5231979489326477, 1.6853516101837158, 2.1520018577575684, -0.21094512939453125, 0.17315979301929474, 0.4542602598667145, -0.2732910215854645, 0.21974869072437286, -0.2650032043457031, -1.256079077720642, 1.5323302745819092, -0.13878726959228516, 0.6007751226425171, -0.4330078065395355, 0.1352672129869461, -0.8786987066268921, -0.31142425537109375, 0.6198577880859375, 0.6442722082138062, 0.3144485354423523, 0.8065269589424133, -0.16493435204029083, 0.7569946050643921, -0.5188441276550293, -0.3981019854545593, 0.6935329437255859, -1.2666015625, 0.9607788324356079, 0.47769585251808167, 0.6640609502792358, -0.170257568359375, 0.774707019329071, -0.9093017578125, 0.223568394780159, -0.9531921148300171, 0.9056549072265625, -0.9615234136581421, 0.14208245277404785, 0.4973708987236023, -0.06322173774242401, 0.07750441879034042, -0.05620880052447319, 0.827832043170929, 0.7838379144668579, -0.0047210692428052425, -0.1834716796875, 0.927502453327179, 0.005999374203383923, -0.7456909418106079, 0.05100898817181587, -0.19855347275733948, -0.9554992914199829, 0.35791054368019104, -1.1064453125, -0.05652160570025444, -0.16854968667030334, 0.8781799077987671, 0.33444976806640625, -0.5437835454940796, -0.16169843077659607, 0.2512969970703125, 0.475830078125, 1.1099536418914795, 0.047655485570430756, -1.3327758312225342, -0.13358230888843536, -0.3099571168422699, -0.629376232624054, 0.9230430722236633, -0.7276672124862671, -1.0015990734100342, -0.460043340921402, 0.9901062250137329, 0.20536956191062927, -0.1757678985595703, 0.21586303412914276, 0.6135040521621704, 0.24269255995750427, 0.5982726812362671, 0.42622679471969604, 0.030855655670166016, 0.423043817281723, -0.6261146664619446, -0.6922363042831421, 0.7223144769668579, -0.7133086919784546, -0.885089099407196, 0.15273456275463104, -0.006563114933669567, 0.7800232172012329, 0.981747031211853, 0.2706451416015625, -0.47759246826171875, -0.620281994342804, -0.37916260957717896, 0.656917929649353, 0.883636474609375, 0.12505149841308594, 0.31618040800094604, 0.276846319437027, -0.3563198149204254, -0.6516609191894531, -0.673504650592804, -1.2814117670059204, 0.9977782964706421, 1.1418883800506592, -0.0010356903076171875, 0.9914230108261108, -1.0193774700164795, -0.90765380859375, -0.299163818359375, 0.2567245364189148, 1.0204589366912842, -0.29380112886428833, 0.8401588201522827, -0.2987914979457855, 0.12627562880516052, -0.549694836139679, 0.34235841035842896, -1.3863525390625, 0.428741455078125, 0.270119845867157, -0.7912033200263977, 1.445092797279358, 0.4076385498046875, -0.513653576374054, -1.2548828125, -0.18652191758155823, 1.095556616783142, 1.271783471107483, -1.1042312383651733, -0.3124946653842926, -1.1318175792694092, -0.593170166015625, 1.039129614830017, -0.7022323608398438, 0.9913330078125, -0.18577881157398224, -0.704882800579071, -0.39684218168258667, -0.976428210735321, -0.542144775390625, -0.19271469116210938, -0.179443359375, -0.3671020567417145, 0.54571533203125, 0.25791627168655396, -0.0063728331588208675, 2.3929686546325684, 0.0605374351143837, -0.5206543207168579, 0.3389247953891754, 0.5717574954032898, -0.774798572063446, -0.42508238554000854, -0.5952285528182983, -0.42820435762405396, 0.4531935155391693, 0.6514673233032227, 0.6123107671737671, 0.7063873410224915, -0.8155456781387329, 0.5585266351699829, 0.1737280786037445, -1.169368028640747, -0.06416626274585724, 0.12873229384422302, 0.33175963163375854, 0.5672714114189148, -1.095703125, 0.5343658328056335, 0.5123962163925171, 0.07350387424230576, -0.06964568793773651, 0.5375137329101562, 0.26443785429000854, -0.5727264285087585, -0.39655762910842896, 0.18878173828125, -0.7134475708007812, -0.7395431399345398, 0.5065536499023438, -1.143896460533142, 0.04325880855321884, -0.16196441650390625, -0.5759662389755249, -0.09844055026769638, 1.326867699623108, 0.18984833359718323, -0.3394622802734375, 0.794873058795929, -0.07010803371667862, -0.2571156322956085, -0.10005979239940643, -0.15246276557445526, -0.6323776245117188, -0.14276123046875, -0.7548248171806335, 0.186412051320076, -0.7343463897705078, 0.4714111387729645, -0.10248260200023651, 0.698132336139679, -0.5754657983779907, -0.39277952909469604, 0.12843474745750427, 0.5023773312568665, -0.5439397692680359, 0.4997619688510895, -0.22559508681297302, 0.4998571276664734, -0.20433273911476135, -0.2301502525806427, -0.1872284859418869, 0.9121322631835938, -0.301034539937973, -0.3463241457939148, 1.514306664466858, -1.0198485851287842, -1.2626831531524658, -0.24612045288085938, 0.03835134580731392, -0.4817628860473633, 0.878753662109375, 0.23169556260108948, -0.2927175462245941, 0.42626953125, -0.22034911811351776, 1.233209252357483, -0.3857925534248352, -0.5535186529159546, 0.043114472180604935, -0.22971495985984802, -0.6723572015762329, 1.08935546875, -0.3287399411201477, -0.17405471205711365, -0.5889343023300171, 0.394186407327652, 0.8136879205703735, 1.9441406726837158, 1.0275253057479858, 0.3817901611328125, -0.01588287390768528, -0.7276672124862671, -0.3356689512729645, 0.8709470629692078, 0.04739322513341904, -0.597003161907196, 0.31069642305374146, -1.2066650390625, 0.0067955018021166325, -0.8674255609512329, 0.098876953125, 1.2557799816131592, 0.7370758056640625, 0.932861328125, 1.100744605064392, 0.5745483636856079, -0.5720764398574829, -0.5780166387557983, 0.354330450296402, -0.7212432622909546, -0.013347625732421875, 0.18405990302562714, 0.21666260063648224, -0.00922393798828125, -0.48538970947265625, 0.6104881167411804, 1.0509856939315796, 1.0549347400665283, 0.04864807054400444, -0.9337615966796875, 1.19830322265625, 0.26883697509765625, 0.6592193841934204, -0.7401542663574219, 0.26248079538345337, 0.2890640199184418, -1.241662621498108, 1.296136498451233, -1.8230712413787842, -0.6302947998046875, -0.261117547750473, 0.9159148931503296, -0.29349976778030396, -0.005078124813735485, 0.613391101360321, -0.23154906928539276, 0.2902160584926605, -0.36023712158203125, 0.10209961235523224, 0.5726326107978821, -0.5712417364120483, 0.36700743436813354, 0.6106621026992798, -0.09385757148265839, -0.2743873596191406, 0.240478515625, -0.4243942201137543, 0.626574695110321, -0.6543014645576477, -0.01338043250143528, 0.8982192873954773, 0.621917724609375, -0.6432250738143921, 0.2641277313232422, 0.0015861510764807463, -0.08440475165843964, -0.4678482115268707, -0.11969032138586044, 0.10593567043542862, -0.45551759004592896, 0.22949866950511932, -0.678985595703125, -0.63238525390625, -1.252416968345642, 0.42224612832069397, 0.4863906800746918, 0.009343480691313744, 1.5131912231445312, 1.194879174232483, -0.078038789331913, 0.18453827500343323, -0.17103271186351776, -0.12634487450122833, -0.5820373296737671, 0.4881513714790344, 0.86944580078125, -0.9789764285087585, -1.022552490234375, -0.23151855170726776, -0.8232132196426392, -0.4626907408237457, 1.024572730064392, -0.8660286068916321, -0.2531600892543793, 1.7245361804962158, -1.664605736732483, -1.707250952720642, 0.26119691133499146, -0.8316055536270142, -0.5910245776176453, -0.28371429443359375, -1.2895019054412842, -1.1066405773162842, 0.8175705075263977, -0.2233620584011078, 0.8287612795829773, 0.5206010937690735, 0.5372816324234009, -0.3429412841796875, 0.11873264610767365, 0.46890562772750854, 0.5958954095840454, -0.07566528022289276, -0.10193081200122833, 0.13214950263500214, 0.21058349311351776, 0.9421294927597046, -0.21677474677562714, 0.42869263887405396, 0.5718849301338196, 1.712158203125, 0.7490226626396179, 0.5237594842910767, -0.1544807404279709, -0.812530517578125, 0.6819092035293579, 0.4450012147426605, 1.1032378673553467, -0.2416084259748459, 0.01953125, 0.11530761420726776, 0.052919767796993256, 0.01796741411089897, 0.09430389106273651, 0.3888000547885895, 1.40032958984375, 0.3721275329589844, -0.6663818359375, -1.0107848644256592, -0.42572784423828125, 2.2312989234924316, 1.531957983970642, -0.2141265869140625, -0.640124499797821, 0.442617803812027, 1.0820099115371704, 0.38483887910842896, 0.8979705572128296, 1.2420532703399658, 0.936206042766571, 0.1832883358001709, 0.03210601955652237, -0.2624708116054535, 0.18783339858055115, 0.4192478060722351, -0.0023712157271802425, -0.35431861877441406, -1.761474609375, 0.4991821348667145, 0.6260952949523926, 0.0580902099609375, 0.11740503460168839, 0.6506317257881165, 1.1585876941680908, 1.2657592296600342, -1.0553100109100342, 0.11104965209960938, 0.4192054867744446, 0.15736541152000427, -0.5794464349746704, -0.7762451171875, 0.118901826441288, 0.029147814959287643, -0.32196617126464844, 0.8204620480537415, -0.2435123473405838, 0.6452789306640625, -0.13150939345359802, -1.137841820716858, -0.4828033447265625, 0.17289428412914276, 0.17633375525474548, -0.4388030171394348, -0.416952520608902, -0.3000854551792145, -0.6127209663391113, 0.34379807114601135, 0.8692779541015625, 1.077478051185608, -0.08435191959142685, -0.7347137331962585, 0.345803827047348, -0.18990173935890198, 0.5225919485092163, 0.5557006597518921, 0.49205321073532104, 1.2743651866912842, 0.2621704041957855, -0.9666687250137329, 0.9997056722640991, -0.4264392852783203, 0.5369521975517273, -0.29456788301467896, -0.006854248233139515, -0.01810302771627903, 0.26715487241744995, 0.1946266144514084, 0.5208648443222046, 1.1803100109100342, 1.1699554920196533, -0.14821204543113708, 1.0067627429962158, -0.5176233053207397, -0.9477218389511108, -0.11125946044921875, 0.48545533418655396, -0.20493564009666443, -0.1756233274936676, -0.664929211139679, -0.16568870842456818, 0.21127519011497498, 0.8331543207168579, 0.2228168547153473, -1.0486786365509033, -0.01963195763528347, 0.5279739499092102, 0.546185314655304, -1.0958983898162842, -0.10116882622241974, -0.5610321164131165, 0.22090645134449005, -0.21680298447608948, 0.9251144528388977, 0.798992931842804, 0.23042908310890198, -0.2073616087436676, -0.8394729495048523, 0.07895660400390625, 0.6269928216934204, -0.0002639770391397178, -0.6379486322402954, -0.6328353881835938, 0.02698516845703125, -0.3858909606933594, -0.750030517578125, 1.439416527748108, -0.9714012145996094, -0.09364776313304901, -1.018316626548767, 0.5276641845703125, -0.2440212219953537, -0.2955513000488281, -0.325692355632782, 0.01338348351418972, -1.273413062095642, 0.31876373291015625, -0.22766518592834473, 0.412710577249527, 0.1273948699235916, 0.541369616985321, -0.4917709231376648, -0.321533203125, -0.08627624809741974, -0.18021774291992188, -0.0037139891646802425, 0.49342042207717896, -0.58087158203125, 0.31182020902633667, 0.17131194472312927, 0.9166351556777954, -0.10013733059167862, 0.8174880743026733, 0.9305419921875, -1.3192870616912842, -0.276641845703125, 0.2605438232421875, -1.5471923351287842, -0.32173842191696167, 0.2724609375, 0.19351044297218323, -0.7657836675643921, -0.5310516357421875, -0.5216079950332642, -0.4886581301689148, -1.024438500404358, 0.06961727142333984, -0.07797546684741974, -0.6930176019668579, -0.7710326910018921, -0.44671630859375, 0.7751709222793579, -0.31591796875, -0.01825561560690403, -0.7993255853652954, -0.6868011355400085, -1.3044006824493408, -0.2969497740268707, 1.026556372642517, -1.2715530395507812, -0.9530242681503296, 0.6360138058662415, 0.35418471693992615, 0.24020080268383026, -0.3708464503288269, -0.9453064203262329, 0.8357635736465454, -0.6361703872680664, -0.6609436273574829, -0.710400402545929, 0.09669408947229385, -0.3558288514614105, 0.7667205929756165, -0.2526504397392273, -0.48460084199905396, -0.6856445074081421, -0.822857677936554, -0.20483025908470154, 0.5947113037109375, -0.559002697467804, 0.08801154792308807, -0.5935913324356079, -0.8523834347724915, -0.7950790524482727, -0.01578216627240181, 0.6161773800849915, 0.07545623928308487, 0.6979835629463196, -0.3249569833278656, -0.6433441042900085, -0.6044290661811829, 1.1235015392303467, -0.5944579839706421, 0.21662597358226776, 0.0056022643111646175, -0.34161376953125, 1.550048828125, 0.013417243957519531, -0.6796020269393921, 0.26014405488967896, 0.6552841067314148, 0.04986572265625, 0.6315463781356812, 0.522930920124054, 0.5105785131454468, 0.6454223394393921, 1.739160180091858, 0.05820159986615181, 0.463034063577652, -0.29635971784591675, 0.6340118646621704, 0.39688053727149963, 0.566326916217804, -0.8092041015625, -0.3936523497104645, -0.17369651794433594, 0.30214232206344604, 0.01491394080221653, -0.15175780653953552, 0.08865127712488174, 1.407470703125, -0.2749641537666321, -0.4673828184604645, -0.144673153758049, -1.1841552257537842, -0.06223030015826225, 0.20531921088695526, 0.66253662109375, -1.320532202720642, -1.3637268543243408, 0.7317565679550171, -0.34460145235061646, 1.1885192394256592, 0.04731903225183487, 0.15672607719898224, -0.6665763854980469, 0.08965873718261719, -0.645062267780304, 1.302886962890625, -0.5790923833847046, -0.12586669623851776, -0.4205160140991211, -0.22621002793312073, -0.46868592500686646, 0.992358386516571, -0.6966552734375, 0.02982359007000923, -1.229711890220642, -1.2503540515899658, -0.15800628066062927, 0.556884765625, -0.1938163787126541, -0.4319053590297699, 0.5202118158340454, -0.961883544921875, 0.3336532711982727, -0.5057891607284546, 0.4372965693473816, 0.6700989007949829, 0.9154052734375, 0.01566772535443306, 0.42104092240333557, 0.854156494140625, 0.3204624056816101, 0.47625732421875, -0.8326080441474915, -0.35444068908691406, -0.4602626860141754, -0.23447570204734802, 0.003563499543815851, -0.4975524842739105, -0.227879136800766, -0.9457458257675171, -1.2458374500274658, -0.4746337831020355, 0.9161205291748047, 0.051186371594667435, -0.7124541997909546, -1.1010162830352783, -0.64630126953125, 0.1407623291015625, -0.716046154499054, 0.2292938232421875, -0.8012005090713501, 0.5534757375717163, -1.1309082508087158, 0.15992584824562073, -0.553112804889679, -1.4826171398162842, -0.086395263671875, -0.8609619140625, -0.710040271282196, -1.36029052734375, -0.603741466999054, -0.6023162603378296, -0.17305298149585724, -1.7968261241912842, -0.4614273011684418, -0.3376403748989105, 0.1614631712436676, 0.26699143648147583, 0.19875183701515198, -0.12485961616039276, 0.9283798336982727, 1.214958906173706, -0.3235134184360504, 0.7500060796737671, -0.29562893509864807, -1.260358452796936, -0.609356701374054, -0.01761779747903347, 0.17945727705955505, 0.5850372314453125, 0.4480880796909332, 1.40179443359375, 0.07010193169116974, 0.731311023235321, -0.15746422111988068, 0.943127453327179, -0.5754478573799133, 0.3295799195766449, -0.4380355775356293, -0.42739391326904297, -0.722705066204071], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (FastAPI | includes | integration | authentication | patterns)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.

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

{'search_vector': [0.4274851381778717, 0.45941162109375, -3.1944987773895264, -0.8983993530273438, 1.3100992441177368, -1.0638834238052368, 0.6257476806640625, -0.3529459536075592, 0.2482808381319046, -0.9000040888786316, -0.222747802734375, 0.4087317883968353, 1.58056640625, 0.0605061836540699, -0.07783190160989761, 0.820587158203125, 0.8620198369026184, -0.8890787959098816, -0.0481160469353199, 0.0801442489027977, -0.046747684478759766, 0.2707010805606842, -1.3929443359375, 0.6463521122932434, 1.295867919921875, -0.8481547236442566, 0.7767741084098816, -0.2822163999080658, -1.4258829355239868, -0.92626953125, 1.6369222402572632, 0.2994740903377533, 0.4605194628238678, -1.2121124267578125, 0.30099233984947205, -0.8217875361442566, 0.713592529296875, 0.8674113154411316, -0.07600688934326172, 1.0372720956802368, -1.87890625, 0.925994873046875, 1.07177734375, 0.7631613612174988, -0.0991312637925148, 0.3206278383731842, 0.8343098759651184, 0.6322657465934753, 0.6326802372932434, -0.872650146484375, -0.13538233935832977, -0.6435801386833191, 0.30949655175209045, -1.6922607421875, 1.6150716543197632, 1.02874755859375, -0.785247802734375, 0.90789794921875, -0.87542724609375, -0.5170542597770691, 0.9711812138557434, -0.047211963683366776, -0.9777018427848816, 1.93798828125, 0.2291971892118454, 0.596160888671875, -1.1257730722427368, 0.8583984375, -0.31092676520347595, -0.707672119140625, -0.0029958088416606188, -1.05859375, 0.2462310791015625, 0.0732218399643898, 0.19803301990032196, 0.4020233154296875, -0.42096710205078125, -1.14520263671875, 0.0369517020881176, 0.9355061650276184, 0.2600199282169342, -0.2668568193912506, 0.527923583984375, -0.6111857295036316, 0.7634785771369934, -0.26753297448158264, -0.9545186161994934, 0.22782135009765625, -0.19351451098918915, 0.8581746220588684, 0.6948445439338684, -0.4727681577205658, 0.14218966662883759, 0.4296163022518158, -1.0042623281478882, -0.14342117309570312, -0.5097071528434753, 0.8554890751838684, -0.9731852412223816, -0.6834751963615417, -0.1415812224149704, 0.23709742724895477, 0.12007904052734375, -0.88330078125, -0.2617238461971283, 0.28898558020591736, 0.3751322329044342, 0.1978403776884079, 0.4269612729549408, 0.7831065058708191, -0.05962181091308594, 0.942169189453125, 0.3885243833065033, -0.6235707402229309, -0.5165799260139465, -1.4361165761947632, 0.0652211531996727, -0.4706153869628906, 0.14187876880168915, 0.04292042925953865, -0.7151997685432434, -1.3809000253677368, -1.0779317617416382, 1.1814371347427368, -0.1129659041762352, 0.00482177734375, -1.2011312246322632, 0.5656916499137878, 0.17906443774700165, -1.4893392324447632, 0.01593017578125, -1.41162109375, -0.845458984375, -0.2287750244140625, 0.310089111328125, -0.39191436767578125, -0.9480387568473816, -0.29705810546875, -0.1704222410917282, 0.05303192138671875, -0.2705484926700592, 0.9364725947380066, -0.32076263427734375, -0.4635416567325592, -0.3265940248966217, -0.4732666015625, 0.982421875, -0.6235453486442566, 0.19061534106731415, 0.2028961181640625, -0.00201416015625, 1.0588327646255493, -0.24954478442668915, 1.2389730215072632, -0.06252797693014145, 0.17146332561969757, 0.28070321679115295, -0.3095550537109375, 0.31760916113853455, 0.9268849492073059, 0.8999837040901184, -0.7936909794807434, -0.1880950927734375, 0.8602498173713684, -0.1528162956237793, -0.5600993037223816, 0.9064127802848816, 1.543701171875, 0.24510955810546875, 1.2674154043197632, -0.7861582636833191, -0.6132399439811707, -1.2160135507583618, -1.050763487815857, 0.9299519658088684, -0.29519906640052795, -0.32441458106040955, -1.2102457284927368, 1.7956491708755493, -0.7257232666015625, -0.21039073169231415, -1.1317138671875, 0.07300567626953125, 0.771209716796875, 0.08611170202493668, 0.3147360384464264, 0.5467173457145691, -0.02266438864171505, -0.5596033930778503, -1.3120931386947632, 0.6031519770622253, 0.3233286440372467, -0.6782171130180359, -0.8544578552246094, -1.2921956777572632, -0.7599385380744934, 1.2864786386489868, -0.1171875, 0.5697657465934753, 0.2907053530216217, -0.3331807553768158, 0.02171802520751953, -0.22378094494342804, -0.1442972868680954, -0.1877884864807129, -0.26129403710365295, 0.8543701171875, -0.36593374609947205, -0.7762451171875, 0.961944580078125, 1.3898519277572632, 0.6174793243408203, -0.98199462890625, 0.1529693603515625, 1.0635579824447632, 0.00953547190874815, -0.2570546567440033, -0.8001963496208191, -0.08630117028951645, 0.23787593841552734, 1.6486002206802368, 0.08306757360696793, 0.9090372920036316, -1.3494873046875, -0.39539846777915955, 0.34625497460365295, -1.7058511972427368, -0.5221099853515625, -0.94781494140625, -0.0710601806640625, -0.4469706118106842, -1.2618814706802368, -0.1587321013212204, 0.5194600224494934, 0.3296763002872467, 0.32013067603111267, 0.11981201171875, 1.322509765625, 0.06933847814798355, -0.808837890625, -0.3199551999568939, -0.3361307680606842, -0.819854736328125, 0.801239013671875, -0.8142598271369934, -0.56707763671875, -0.5870869755744934, -0.74176025390625, -0.3216400146484375, 0.99072265625, -0.3687705993652344, 0.13725630939006805, -0.02060953713953495, -0.742523193359375, 0.011225382797420025, 0.0277252197265625, 0.0634206160902977, 0.1269633024930954, 0.044036865234375, -0.743408203125, 0.8948974609375, -0.21059925854206085, -0.5614420771598816, 0.4781545102596283, 0.6877453923225403, -0.5754318237304688, 0.7107696533203125, 0.549407958984375, -0.29608154296875, -0.0763295516371727, 0.176910400390625, 0.8086954951286316, 0.85321044921875, 0.1465805321931839, 0.5302327275276184, 0.27679190039634705, -0.2814076840877533, 0.049065906554460526, -0.8713703155517578, 1.2195028066635132, -0.7131754755973816, -0.7158864140510559, -0.96185302734375, 0.8150075078010559, -0.26206526160240173, 0.0652262344956398, -0.33331298828125, -0.32193252444267273, 0.3551025390625, 0.08021799474954605, 2.1255695819854736, 0.1646525114774704, -1.9249674081802368, 1.346405029296875, -0.5463053584098816, -0.15703518688678741, 0.61505126953125, -0.23248291015625, 0.3600107729434967, 0.0403950996696949, 0.0154571533203125, 0.46350225806236267, 0.8319314122200012, 0.4234384000301361, -0.020506540313363075, -0.2288004606962204, 0.5067774653434753, -0.6406046748161316, 0.4930318295955658, 1.0521240234375, -0.7083536982536316, 0.7437388300895691, -0.5944620966911316, 0.7890828251838684, -0.36400094628334045, 1.2275491952896118, -0.002971649169921875, 0.43821462988853455, 0.26812744140625, -0.3206278383731842, -0.252593994140625, -1.1668510437011719, 0.0029551188927143812, 0.560235321521759, 0.18593788146972656, -0.0055592856369912624, -0.938720703125, 0.1144561767578125, -0.5098012089729309, -0.65911865234375, 0.2560272216796875, -0.01898193359375, 0.4097951352596283, -0.9781951904296875, -1.00244140625, 0.38118743896484375, 0.4512837827205658, 0.6243038177490234, -0.9259745478630066, 0.7581990361213684, 0.9228515625, -1.3353677988052368, 1.1649678945541382, -1.4803670644760132, -0.4470583498477936, 0.6621754765510559, 0.4933064877986908, -0.17009226977825165, 1.1688232421875, 0.3100249767303467, -0.723876953125, 0.7751261591911316, -0.7520751953125, -0.2404988557100296, 0.2840016782283783, -0.3253377377986908, 1.4186197519302368, 0.6399027705192566, 0.19569523632526398, 0.1938323974609375, 1.07818603515625, -0.6921793818473816, 0.6460902094841003, -0.559326171875, -0.14527130126953125, 1.0287679433822632, 0.8409321904182434, -0.31232962012290955, 0.6648356318473816, -0.10774930566549301, -0.0706583634018898, -1.1051839590072632, -0.522003173828125, 0.5637664794921875, -0.5685221552848816, 0.5628560185432434, -0.9991658329963684, -0.9482066035270691, -0.9458935856819153, 0.09962081909179688, -0.03833262249827385, 0.17971038818359375, 0.859771728515625, 1.2491785287857056, 0.5297597050666809, -0.5197550654411316, 0.0956319198012352, 0.3693440854549408, 0.2263743132352829, 0.3094278872013092, 0.8878173828125, -1.1569112539291382, -0.8427479863166809, 1.0636190176010132, 0.1580607146024704, -0.7013473510742188, 0.3018358051776886, 0.2241617888212204, 0.64813232421875, 0.976898193359375, -1.5531005859375, -0.9699605107307434, -0.33418241143226624, -0.7021458745002747, -0.38677978515625, -0.13685353100299835, -0.9808756709098816, -0.9097900390625, 0.677001953125, -0.9346771240234375, 0.5598805546760559, -0.8490040898323059, 0.31605783104896545, -0.23198826611042023, 0.20556640625, 0.3139190673828125, 1.1974283456802368, 0.3317311704158783, 0.3271840512752533, -0.682891845703125, -0.248077392578125, 0.0534464530646801, 1.0102945566177368, 0.9637858271598816, -0.0023924510460346937, 0.34303078055381775, 0.5137532353401184, 0.9983317255973816, 0.4025777280330658, -1.0374552011489868, -0.1804300993680954, 0.8586222529411316, 1.3284505605697632, -1.4973806142807007, 0.15065257251262665, -0.3275095522403717, -0.7513605952262878, 0.8256428837776184, 0.6354166865348816, 0.41563859581947327, 1.138946533203125, 0.25276973843574524, -0.523162841796875, 0.9404703974723816, -0.044757843017578125, 2.6714680194854736, 1.1147664785385132, -0.1538289338350296, 0.5491587519645691, 0.9301859736442566, -0.282196044921875, -0.07791391760110855, 0.3671366274356842, 0.6405842900276184, 1.6229654550552368, 0.10143343359231949, -1.0090993642807007, 0.572265625, 1.0334066152572632, -0.0762176513671875, 0.45013427734375, 1.1507974863052368, -1.8241780996322632, 0.4441324770450592, -0.2173970490694046, 0.1933695524930954, 0.36544546484947205, -0.3117777407169342, 1.4803873300552368, 1.3590850830078125, -0.48451486229896545, -0.33592095971107483, 0.7193374633789062, -0.3691355288028717, 0.6817881464958191, 0.8115412592887878, -0.2313079833984375, 0.2890714108943939, 0.0982309952378273, 0.564117431640625, -0.2010854035615921, -0.03799692913889885, -0.5335960388183594, -0.08216730505228043, -0.19244511425495148, 0.0194117221981287, 0.6654459834098816, -0.7893880009651184, 0.8872883915901184, -0.275238037109375, 0.6375172734260559, 0.09808921813964844, 0.7072855830192566, 0.9908738136291504, 0.5659561157226562, -0.67657470703125, 0.43744659423828125, 0.283538818359375, 0.12700271606445312, -0.647491455078125, -0.1604817658662796, 0.6836709976196289, -0.14100901782512665, -0.8524373173713684, 0.2976264953613281, -0.87322998046875, 0.8734995722770691, -0.6658884882926941, 0.45908451080322266, -0.2996877133846283, -0.5067850947380066, 0.1119435653090477, 0.0635325089097023, 0.2777188718318939, 1.0766042470932007, 0.07109197229146957, 0.3233439028263092, -0.1743672639131546, -0.05803171917796135, -0.6022847294807434, -0.08432642370462418, -0.4175987243652344, -0.59820556640625, -0.5737972259521484, -0.6444804072380066, -0.034112293273210526, -0.15197880566120148, -0.5151036381721497, 0.2461954802274704, -0.25449371337890625, -0.033456165343523026, 0.31890869140625, -1.23828125, 0.34060096740722656, 0.4831339418888092, -0.09035491943359375, -0.6365916132926941, 0.4108146131038666, 0.7830047607421875, 0.7782745361328125, 1.34521484375, -0.22741515934467316, -0.5091654658317566, -0.8914852142333984, -0.11500295251607895, -0.5830078125, 0.15969054400920868, 0.561248779296875, -0.6471150517463684, -0.7517496943473816, 0.97723388671875, -0.4851277768611908, -0.2219950407743454, -0.92047119140625, 0.3563283383846283, 0.1073354110121727, 0.042319297790527344, 0.2291971892118454, -0.3444925844669342, -0.0716552734375, 0.4374288022518158, 0.12572987377643585, 0.6482696533203125, -0.11428960412740707, -1.1325277090072632, -1.1453857421875, -0.026287714019417763, -0.6854336857795715, -0.06566110998392105, 0.7465413212776184, 0.4816029965877533, -0.2210489958524704, -0.1484578400850296, 0.2038421630859375, 0.09053230285644531, 0.4997355043888092, 0.15262286365032196, 0.02773030661046505, -0.3433481752872467, -0.6446736454963684, 0.5967966914176941, -0.7354329228401184, 0.382415771484375, 0.17758814990520477, 0.06024169921875, -0.7373148798942566, -0.6009724736213684, -0.5337321162223816, -0.07235908508300781, -0.5427958369255066, -0.24933116137981415, -0.1710968017578125, -0.3585103452205658, -0.7255859375, 0.670867919921875, 0.06689866632223129, -0.8001505732536316, 0.2166341096162796, 0.08829053491353989, -0.40468597412109375, 0.3051961362361908, 0.1849365234375, 0.7579777836799622, -0.0852610245347023, -0.8316752314567566, 0.22490184009075165, -0.031317394226789474, 0.21119435131549835, -0.1628519743680954, -0.4735107421875, 1.3701578378677368, -0.8900960087776184, -0.9007771611213684, -0.2727851867675781, 0.859222412109375, -0.3771463930606842, 0.7219942212104797, 0.1817677766084671, -0.4250946044921875, 0.3388773500919342, -0.2254740446805954, -0.8857828974723816, 0.6981608271598816, -1.25360107421875, -0.038621265441179276, 0.01823933981359005, -0.2523600161075592, -0.32700857520103455, 0.47845458984375, -0.389404296875, 0.1015777587890625, 0.154998779296875, -0.962493896484375, -1.5606282949447632, -1.500732421875, 1.1708984375, -0.7166569828987122, 1.0473836660385132, -0.009621620178222656, 0.8517354130744934, 1.2175089120864868, 0.2599588930606842, -0.22510020434856415, -0.5072352290153503, 0.3445764482021332, 0.28451791405677795, 0.4334055483341217, 1.317626953125, 0.9953816533088684, 0.8017781376838684, 1.9829915761947632, 1.4621988534927368, 0.4810689389705658, 0.06355031579732895, 0.56787109375, -0.11477788537740707, 0.3151957094669342, -0.7831013798713684, -1.2500406503677368, -0.44281005859375, 0.2934977114200592, -0.33990478515625, -0.1138407364487648, -0.4927622377872467, 1.399169921875, 0.16155624389648438, 0.6661097407341003, -0.555145263671875, -0.012364705093204975, -0.1150716170668602, -0.030317306518554688, -0.26321157813072205, -0.2705484926700592, -1.18426513671875, 0.9690755009651184, -0.04193115234375, 0.9264729619026184, 0.6418838500976562, -1.3770751953125, -0.0712381973862648, -0.5258560180664062, -0.1011810302734375, 0.79736328125, -0.0541025809943676, -0.994873046875, 0.1462656706571579, 0.8340047001838684, -0.601470947265625, 0.1147867813706398, -0.8553873896598816, -1.5222574472427368, -1.1886698007583618, -0.9533488154411316, 0.6631672978401184, 0.5397135615348816, 0.24446868896484375, 0.0931345596909523, -0.6359660029411316, 0.4041252136230469, 0.9143961071968079, -0.9338582158088684, 0.7459996342658997, 0.8361002802848816, 0.7560088038444519, -0.6785557866096497, -0.21633976697921753, 0.023480653762817383, -0.08786264806985855, 0.141754150390625, -0.41119384765625, -0.49574533104896545, -0.6626790165901184, -0.77716064453125, 0.21478271484375, -0.025360107421875, -0.16284401714801788, -0.3279215395450592, -0.8686930537223816, -0.29403337836265564, 0.2206980437040329, 0.713616669178009, 0.0468088798224926, -0.5566609501838684, -0.4684244692325592, -0.6054026484489441, -0.2364095002412796, 0.3090057373046875, -0.6304550170898438, -0.122100830078125, -0.9561564326286316, 0.10844548791646957, -1.0439046621322632, -0.6032511591911316, 0.3442840576171875, -0.3881988525390625, 0.5723800659179688, -0.9538981318473816, -0.9300015568733215, -1.6664224863052368, 0.32645097374916077, -0.7678425908088684, 0.4290212094783783, -0.6072590947151184, 0.297119140625, -0.22536206245422363, -0.40004029870033264, -0.5083821415901184, 1.2849527597427368, 0.7727432250976562, -0.1090240478515625, 0.8925698399543762, -1.6551920175552368, -0.9026272892951965, 0.2535603940486908, -0.05778757855296135, 0.04315948486328125, -1.0287882089614868, 0.47907066345214844, 3.2537434101104736, 0.1066741943359375, 1.2957967519760132, -0.2326650619506836, 0.6536296606063843, -0.5501301884651184, 0.25998687744140625, -0.626190185546875, -0.32450613379478455, -0.17335891723632812], 'limit': 20, 'min_score': 0.6, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (HTTPException | used | request | validation | error | handling)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: Connection closed by server.
CALL db.idx.fulltext.queryRelationships('RELATES_TO', $query)
    YIELD relationship AS rel, score
    MATCH (n:Entity)-[e:RELATES_TO {uuid: rel.uuid}]->(m:Entity)
     WHERE e.uuid in $edge_uuids AND e.group_id IN $group_ids
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

{'query': ' (FastAPI | integrates | CRUD | operations)', 'limit': 20, 'routing_': 'r', 'edge_uuids': [], 'group_ids': ['rules']}

GuardKit initialized successfully!

Next steps:
  1. Create a task: /task-create "Your first task"
  2. Work on it: /task-work TASK-XXX
  3. Complete it: /task-complete TASK-XXX
<sys>:0: RuntimeWarning: coroutine 'search' was never awaited
RuntimeWarning: Enable tracemalloc to get the object allocation traceback
<sys>:0: RuntimeWarning: coroutine 'edge_search' was never awaited
RuntimeWarning: Enable tracemalloc to get the object allocation traceback
<sys>:0: RuntimeWarning: coroutine 'node_search' was never awaited
RuntimeWarning: Enable tracemalloc to get the object allocation traceback
<sys>:0: RuntimeWarning: coroutine 'episode_search' was never awaited
RuntimeWarning: Enable tracemalloc to get the object allocation traceback
<sys>:0: RuntimeWarning: coroutine 'community_search' was never awaited
RuntimeWarning: Enable tracemalloc to get the object allocation traceback
richardwoollcott@Richards-MBP vllm-profiling %