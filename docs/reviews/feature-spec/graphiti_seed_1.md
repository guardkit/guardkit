richardwoollcott@Richards-MBP guardkit % guardkit-py graphiti add-context docs/research/feature-spec/FEATURE-SPEC-feature-spec-command-v2.md

Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: RediSearch: Syntax error at offset 22 near command
CALL db.idx.fulltext.queryNodes('Entity', $query)YIELD node AS n, score WHERE n.group_id IN $group_ids
            WITH n, score
            ORDER BY score DESC
            LIMIT $limit
            RETURN

        n.uuid AS uuid,
        n.name AS name,
        n.group_id AS group_id,
        n.created_at AS created_at,
        n.summary AS summary,
        labels(n) AS labels,
        properties(n) AS attributes

{'query': ' (Slash | command | ` | claude/commands/feature | spec | md`)', 'limit': 20, 'routing_': 'r', 'group_ids': ['guardkit__feature-spec-bdd-specification-generator']}
WARNING:guardkit.knowledge.graphiti_client:Episode creation request failed: RediSearch: Syntax error at offset 22 near command
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: RediSearch: Syntax error at offset 18 near flags
CALL db.idx.fulltext.queryNodes('Entity', $query)YIELD node AS n, score WHERE n.group_id IN $group_ids
            WITH n, score
            ORDER BY score DESC
            LIMIT $limit
            RETURN

        n.uuid AS uuid,
        n.name AS name,
        n.group_id AS group_id,
        n.created_at AS created_at,
        n.summary AS summary,
        labels(n) AS labels,
        properties(n) AS attributes

{'query': ' (CLI | flags | ` | from` | ` | output` | ` | auto` | ` | stack` | ` | context` | ` | scenarios`)', 'limit': 20, 'routing_': 'r', 'group_ids': ['guardkit__feature-spec-bdd-specification-generator']}
ERROR:graphiti_core.driver.falkordb_driver:Error executing FalkorDB query: RediSearch: Syntax error at offset 29 near tags
CALL db.idx.fulltext.queryNodes('Entity', $query)YIELD node AS n, score WHERE n.group_id IN $group_ids
            WITH n, score
            ORDER BY score DESC
            LIMIT $limit
            RETURN

        n.uuid AS uuid,
        n.name AS name,
        n.group_id AS group_id,
        n.created_at AS created_at,
        n.summary AS summary,
        labels(n) AS labels,
        properties(n) AS attributes

{'query': ' (Cross | cutting | tags | ` | smoke` | ` | regression`)', 'limit': 20, 'routing_': 'r', 'group_ids': ['guardkit__feature-spec-bdd-specification-generator']}
  ⚠ docs/research/feature-spec/FEATURE-SPEC-feature-spec-command-v2.md (feature-spec) — 1 episode(s) failed

Summary:
  Added 1 file, 0 episodes
  Failed: 1 episode

Warnings:
  Warning: docs/research/feature-spec/FEATURE-SPEC-feature-spec-command-v2.md: Missing feature overview section
  Warning: docs/research/feature-spec/FEATURE-SPEC-feature-spec-command-v2.md: No phases found in feature spec

Errors:
  Error: docs/research/feature-spec/FEATURE-SPEC-feature-spec-command-v2.md: Episode creation returned None (possible silent failure)
<sys>:0: RuntimeWarning: coroutine 'search' was never awaited
RuntimeWarning: Enable tracemalloc to get the object allocation traceback