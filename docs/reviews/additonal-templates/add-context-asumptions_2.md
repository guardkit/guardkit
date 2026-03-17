richardwoollcott@Richards-MBP agentic-dataset-factory % guardkit graphiti add-context docs/architecture/assumptions.yaml
Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 120s: docs/architecture/assumptions.yaml
  ⚠ docs/architecture/assumptions.yaml (yaml) — 1 episode(s) failed

Summary:
  Added 1 file, 0 episodes
  Failed: 1 episode

Errors:
  Error: docs/architecture/assumptions.yaml: Episode creation returned None (possible silent failure)
richardwoollcott@Richards-MBP agentic-dataset-factory %