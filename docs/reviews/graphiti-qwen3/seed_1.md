richardwoollcott@Richards-MBP agentic-dataset-factory % guardkit graphiti add-context docs/architecture/ARCHITECTURE.md --timeout 900
Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

INFO:graphiti_core.graphiti:Completed add_episode in 169651.2668132782 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [docs/architecture/ARCHITECTURE.md]: nodes=13, edges=9, invalidated=0
  ✓ docs/architecture/ARCHITECTURE.md (full_doc)

Summary:
  Added 1 file, 1 episode
richardwoollcott@Richards-MBP agentic-dataset-factory %