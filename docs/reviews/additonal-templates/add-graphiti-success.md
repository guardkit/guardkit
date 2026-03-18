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
richardwoollcott@Richards-MBP agentic-dataset-factory % guardkit graphiti add-context docs/architecture/container.md --timeout 900
Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 2] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 309274.95312690735 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [docs/architecture/container.md]: nodes=15, edges=28, invalidated=0
  ✓ docs/architecture/container.md (full_doc)

Summary:
  Added 1 file, 1 episode
richardwoollcott@Richards-MBP agentic-dataset-factory % guardkit graphiti add-context docs/architecture/domain-model.md --timeout 900
Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

INFO:graphiti_core.graphiti:Completed add_episode in 237993.16787719727 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [docs/architecture/domain-model.md]: nodes=15, edges=20, invalidated=0
  ✓ docs/architecture/domain-model.md (full_doc)

Summary:
  Added 1 file, 1 episode
richardwoollcott@Richards-MBP agentic-dataset-factory % guardkit graphiti add-context docs/architecture/decisions/ADR-ARCH-002-six-module-decomposition.md --timeout 900
Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 14 out of bounds for chunk of size 14 in edge HAS_RESPONSIBILITY
WARNING:graphiti_core.utils.maintenance.edge_operations:Target index 14 out of bounds for chunk of size 14 in edge HAS_RESPONSIBILITY
INFO:graphiti_core.graphiti:Completed add_episode in 217249.0599155426 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-002-six-module-decomposition]: nodes=14, edges=12, invalidated=0
  ✓ docs/architecture/decisions/ADR-ARCH-002-six-module-decomposition.md (adr)

Summary:
  Added 1 file, 1 episode

Warnings:
  Warning: docs/architecture/decisions/ADR-ARCH-002-six-module-decomposition.md: Missing required section: Status
richardwoollcott@Richards-MBP agentic-dataset-factory %