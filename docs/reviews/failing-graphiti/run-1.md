commands with an asterix at the start ran fine the others failed the repo path was /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/docs/design

*guardkit graphiti add-context docs/design/contracts/API-tools.md
*guardkit graphiti add-context docs/design/contracts/API-output.md
failed guardkit graphiti add-context docs/design/contracts/API-entrypoint.md


richardwoollcott@Richards-MBP agentic-dataset-factory % guardkit graphiti add-context docs/design/contracts/API-entrypoint.md
Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

ERROR:graphiti_core.llm_client.openai_generic_client:Error in generating LLM response: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 18954 input tokens (16384 > 32768 - 18954). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
WARNING:graphiti_core.llm_client.openai_generic_client:Retrying after application error (attempt 1/2): Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 18954 input tokens (16384 > 32768 - 18954). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
ERROR:graphiti_core.llm_client.openai_generic_client:Error in generating LLM response: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 19098 input tokens (16384 > 32768 - 19098). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
WARNING:graphiti_core.llm_client.openai_generic_client:Retrying after application error (attempt 2/2): Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 19098 input tokens (16384 > 32768 - 19098). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
ERROR:graphiti_core.llm_client.openai_generic_client:Error in generating LLM response: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 19242 input tokens (16384 > 32768 - 19242). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
ERROR:graphiti_core.llm_client.openai_generic_client:Max retries (2) exceeded. Last error: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 19242 input tokens (16384 > 32768 - 19242). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
WARNING:guardkit.knowledge.graphiti_client:Episode creation failed: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 19242 input tokens (16384 > 32768 - 19242). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
  ⚠ docs/design/contracts/API-entrypoint.md (full_doc) — 1 episode(s) failed

Summary:
  Added 1 file, 0 episodes
  Failed: 1 episode

Errors:
  Error: docs/design/contracts/API-entrypoint.md: Episode creation returned None (possible silent failure)
richardwoollcott@Richards-MBP agentic-dataset-factory %


# Data models (5 entities)
*guardkit graphiti add-context docs/design/models/DM-goal-schema.md
failed - guardkit graphiti add-context docs/design/models/DM-training-example.md

richardwoollcott@Richards-MBP agentic-dataset-factory % guardkit graphiti add-context docs/design/models/DM-training-example.md
Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

ERROR:graphiti_core.llm_client.openai_generic_client:Error in generating LLM response: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 17557 input tokens (16384 > 32768 - 17557). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
WARNING:graphiti_core.llm_client.openai_generic_client:Retrying after application error (attempt 1/2): Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 17557 input tokens (16384 > 32768 - 17557). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
ERROR:graphiti_core.llm_client.openai_generic_client:Error in generating LLM response: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 17701 input tokens (16384 > 32768 - 17701). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
WARNING:graphiti_core.llm_client.openai_generic_client:Retrying after application error (attempt 2/2): Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 17701 input tokens (16384 > 32768 - 17701). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
ERROR:graphiti_core.llm_client.openai_generic_client:Error in generating LLM response: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 17845 input tokens (16384 > 32768 - 17845). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
ERROR:graphiti_core.llm_client.openai_generic_client:Max retries (2) exceeded. Last error: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 17845 input tokens (16384 > 32768 - 17845). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
WARNING:guardkit.knowledge.graphiti_client:Episode creation failed: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 17845 input tokens (16384 > 32768 - 17845). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
  ⚠ docs/design/models/DM-training-example.md (full_doc) — 1 episode(s) failed

Summary:
  Added 1 file, 0 episodes
  Failed: 1 episode

Errors:
  Error: docs/design/models/DM-training-example.md: Episode creation returned None (possible silent failure)
richardwoollcott@Richards-MBP agentic-dataset-factory %


failed - guardkit graphiti add-context docs/design/models/DM-coach-rejection.md

richardwoollcott@Richards-MBP agentic-dataset-factory % guardkit graphiti add-context docs/design/models/DM-coach-rejection.md
Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

ERROR:graphiti_core.llm_client.openai_generic_client:Error in generating LLM response: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 16765 input tokens (16384 > 32768 - 16765). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
WARNING:graphiti_core.llm_client.openai_generic_client:Retrying after application error (attempt 1/2): Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 16765 input tokens (16384 > 32768 - 16765). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
ERROR:graphiti_core.llm_client.openai_generic_client:Error in generating LLM response: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 16909 input tokens (16384 > 32768 - 16909). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
WARNING:graphiti_core.llm_client.openai_generic_client:Retrying after application error (attempt 2/2): Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 16909 input tokens (16384 > 32768 - 16909). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
ERROR:graphiti_core.llm_client.openai_generic_client:Error in generating LLM response: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 17053 input tokens (16384 > 32768 - 17053). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
ERROR:graphiti_core.llm_client.openai_generic_client:Max retries (2) exceeded. Last error: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 17053 input tokens (16384 > 32768 - 17053). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
WARNING:guardkit.knowledge.graphiti_client:Episode creation failed: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 17053 input tokens (16384 > 32768 - 17053). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
  ⚠ docs/design/models/DM-coach-rejection.md (full_doc) — 1 episode(s) failed

Summary:
  Added 1 file, 0 episodes
  Failed: 1 episode

Errors:
  Error: docs/design/models/DM-coach-rejection.md: Episode creation returned None (possible silent failure)
richardwoollcott@Richards-MBP agentic-dataset-factory %




failed - guardkit graphiti add-context docs/design/models/DM-agent-config.md

richardwoollcott@Richards-MBP agentic-dataset-factory % guardkit graphiti add-context docs/design/models/DM-agent-config.md
Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

ERROR:graphiti_core.llm_client.openai_generic_client:Error in generating LLM response: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 17335 input tokens (16384 > 32768 - 17335). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
WARNING:graphiti_core.llm_client.openai_generic_client:Retrying after application error (attempt 1/2): Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 17335 input tokens (16384 > 32768 - 17335). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
ERROR:graphiti_core.llm_client.openai_generic_client:Error in generating LLM response: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 17479 input tokens (16384 > 32768 - 17479). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
WARNING:graphiti_core.llm_client.openai_generic_client:Retrying after application error (attempt 2/2): Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 17479 input tokens (16384 > 32768 - 17479). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
ERROR:graphiti_core.llm_client.openai_generic_client:Error in generating LLM response: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 17623 input tokens (16384 > 32768 - 17623). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
ERROR:graphiti_core.llm_client.openai_generic_client:Max retries (2) exceeded. Last error: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 17623 input tokens (16384 > 32768 - 17623). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
WARNING:guardkit.knowledge.graphiti_client:Episode creation failed: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 17623 input tokens (16384 > 32768 - 17623). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
  ⚠ docs/design/models/DM-agent-config.md (full_doc) — 1 episode(s) failed

Summary:
  Added 1 file, 0 episodes
  Failed: 1 episode

Errors:
  Error: docs/design/models/DM-agent-config.md: Episode creation returned None (possible silent failure)
richardwoollcott@Richards-MBP agentic-dataset-factory %


failed - guardkit graphiti add-context docs/design/models/DM-rejected-example.md

richardwoollcott@Richards-MBP agentic-dataset-factory % guardkit graphiti add-context docs/design/models/DM-rejected-example.md
Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

ERROR:graphiti_core.llm_client.openai_generic_client:Error in generating LLM response: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 16591 input tokens (16384 > 32768 - 16591). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
WARNING:graphiti_core.llm_client.openai_generic_client:Retrying after application error (attempt 1/2): Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 16591 input tokens (16384 > 32768 - 16591). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
ERROR:graphiti_core.llm_client.openai_generic_client:Error in generating LLM response: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 16735 input tokens (16384 > 32768 - 16735). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
WARNING:graphiti_core.llm_client.openai_generic_client:Retrying after application error (attempt 2/2): Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 16735 input tokens (16384 > 32768 - 16735). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
ERROR:graphiti_core.llm_client.openai_generic_client:Error in generating LLM response: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 16879 input tokens (16384 > 32768 - 16879). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
ERROR:graphiti_core.llm_client.openai_generic_client:Max retries (2) exceeded. Last error: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 16879 input tokens (16384 > 32768 - 16879). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
WARNING:guardkit.knowledge.graphiti_client:Episode creation failed: Error code: 400 - {'error': {'message': "'max_tokens' or 'max_completion_tokens' is too large: 16384. This model's maximum context length is 32768 tokens and your request has 16879 input tokens (16384 > 32768 - 16879). None", 'type': 'BadRequestError', 'param': None, 'code': 400}}
  ⚠ docs/design/models/DM-rejected-example.md (full_doc) — 1 episode(s) failed

Summary:
  Added 1 file, 0 episodes
  Failed: 1 episode

Errors:
  Error: docs/design/models/DM-rejected-example.md: Episode creation returned None (possible silent failure)
richardwoollcott@Richards-MBP agentic-dataset-factory %


# Design decision records (3 DDRs)
*guardkit graphiti add-context docs/design/decisions/DDR-001.md
*guardkit graphiti add-context docs/design/decisions/DDR-002.md
*guardkit graphiti add-context docs/design/decisions/DDR-003.md
