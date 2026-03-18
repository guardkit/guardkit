richardwoollcott@Richards-MBP agentic-dataset-factory % guardkit graphiti add-context docs/architecture/ARCHITECTURE.md --timeout 900
Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

ERROR:graphiti_core.llm_client.openai_generic_client:Error in generating LLM response: Error code: 404 - {'error': {'message': 'The model `claude-sonnet-4-6` does not exist.', 'type': 'NotFoundError', 'param': None, 'code': 404}}
WARNING:graphiti_core.llm_client.openai_generic_client:Retrying after application error (attempt 1/2): Error code: 404 - {'error': {'message': 'The model `claude-sonnet-4-6` does not exist.', 'type': 'NotFoundError', 'param': None, 'code': 404}}
ERROR:graphiti_core.llm_client.openai_generic_client:Error in generating LLM response: Error code: 404 - {'error': {'message': 'The model `claude-sonnet-4-6` does not exist.', 'type': 'NotFoundError', 'param': None, 'code': 404}}
WARNING:graphiti_core.llm_client.openai_generic_client:Retrying after application error (attempt 2/2): Error code: 404 - {'error': {'message': 'The model `claude-sonnet-4-6` does not exist.', 'type': 'NotFoundError', 'param': None, 'code': 404}}
ERROR:graphiti_core.llm_client.openai_generic_client:Error in generating LLM response: Error code: 404 - {'error': {'message': 'The model `claude-sonnet-4-6` does not exist.', 'type': 'NotFoundError', 'param': None, 'code': 404}}
ERROR:graphiti_core.llm_client.openai_generic_client:Max retries (2) exceeded. Last error: Error code: 404 - {'error': {'message': 'The model `claude-sonnet-4-6` does not exist.', 'type': 'NotFoundError', 'param': None, 'code': 404}}
WARNING:guardkit.knowledge.graphiti_client:Episode creation failed: Error code: 404 - {'error': {'message': 'The model `claude-sonnet-4-6` does not exist.', 'type': 'NotFoundError', 'param': None, 'code': 404}}
  ⚠ docs/architecture/ARCHITECTURE.md (full_doc) — 1 episode(s) failed

Summary:
  Added 1 file, 0 episodes
  Failed: 1 episode

Errors:
  Error: docs/architecture/ARCHITECTURE.md: Episode creation returned None (possible silent failure)
richardwoollcott@Richards-MBP agentic-dataset-factory %