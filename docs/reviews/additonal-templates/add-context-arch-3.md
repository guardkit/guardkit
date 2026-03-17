richardwoollcott@Richards-MBP agentic-dataset-factory % guardkit graphiti add-context docs/architecture/ --pattern "**/*.md"
Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0-0 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [2] (valid range: 0-0 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 108724.84517097473 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [docs/architecture/system-context.md]: nodes=10, edges=19, invalidated=0
  ✓ docs/architecture/system-context.md (full_doc)
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 300s: docs/architecture/ARCHITECTURE.md
  ⚠ docs/architecture/ARCHITECTURE.md (full_doc) — 1 episode(s) failed
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 300s: docs/architecture/container.md
  ⚠ docs/architecture/container.md (full_doc) — 1 episode(s) failed
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 300s: docs/architecture/domain-model.md
  ⚠ docs/architecture/domain-model.md (full_doc) — 1 episode(s) failed
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 119346.55809402466 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-001-use-modular-monolith-structural-pattern]: nodes=14, edges=14, invalidated=0
  ✓ docs/architecture/decisions/ADR-ARCH-001-modular-monolith.md (adr)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [3] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 3] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 64782.13024139404 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-004-chromadb-embedded-persistentclient-for-generation]: nodes=8, edges=8, invalidated=0
  ✓ docs/architecture/decisions/ADR-ARCH-004-chromadb-embedded-persistent.md (adr)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 117815.54102897644 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-006-sequential-generation-for-v1]: nodes=14, edges=14, invalidated=0
  ✓ docs/architecture/decisions/ADR-ARCH-006-sequential-generation.md (adr)
INFO:graphiti_core.graphiti:Completed add_episode in 54505.873918533325 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-009-non-deterministic-generation-with-coach-quality-gate]: nodes=6, edges=10, invalidated=0
  ✓ docs/architecture/decisions/ADR-ARCH-009-non-deterministic-generation.md (adr)
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 300s: adr_adr-arch-002-six-module-decomposition
  ⚠ docs/architecture/decisions/ADR-ARCH-002-six-module-decomposition.md (adr) — 1 episode(s) failed
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 91070.22428512573 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-005-configurable-model-backends-for-both-player-and-coach]: nodes=11, edges=12, invalidated=0
  ✓ docs/architecture/decisions/ADR-ARCH-005-configurable-agent-models.md (adr)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 66009.10091400146 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-007-structured-json-logging]: nodes=7, edges=7, invalidated=0
  ✓ docs/architecture/decisions/ADR-ARCH-007-structured-json-logging.md (adr)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [5] (valid range: 0-0 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 96328.30905914307 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-003-docker-containerisation-from-day-one]: nodes=13, edges=11, invalidated=0
  ✓ docs/architecture/decisions/ADR-ARCH-003-docker-containerisation.md (adr)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [9] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 1] (valid range: 0--1 for EXISTING FACTS)
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [0, 1] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 81020.04289627075 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [adr_adr-arch-008-start-fresh-on-re-run]: nodes=10, edges=10, invalidated=0
  ✓ docs/architecture/decisions/ADR-ARCH-008-start-fresh-restart.md (adr)

Summary:
  Added 13 files, 9 episodes
  Failed: 4 episodes

Warnings:
  Warning: docs/architecture/decisions/ADR-ARCH-001-modular-monolith.md: Missing required section: Status
  Warning: docs/architecture/decisions/ADR-ARCH-004-chromadb-embedded-persistent.md: Missing required section: Status
  Warning: docs/architecture/decisions/ADR-ARCH-006-sequential-generation.md: Missing required section: Status
  Warning: docs/architecture/decisions/ADR-ARCH-009-non-deterministic-generation.md: Missing required section: Status
  Warning: docs/architecture/decisions/ADR-ARCH-002-six-module-decomposition.md: Missing required section: Status
  Warning: docs/architecture/decisions/ADR-ARCH-005-configurable-agent-models.md: Missing required section: Status
  Warning: docs/architecture/decisions/ADR-ARCH-007-structured-json-logging.md: Missing required section: Status
  Warning: docs/architecture/decisions/ADR-ARCH-003-docker-containerisation.md: Missing required section: Status
  Warning: docs/architecture/decisions/ADR-ARCH-008-start-fresh-restart.md: Missing required section: Status

Errors:
  Error: docs/architecture/ARCHITECTURE.md: Episode creation returned None (possible silent failure)
  Error: docs/architecture/container.md: Episode creation returned None (possible silent failure)
  Error: docs/architecture/domain-model.md: Episode creation returned None (possible silent failure)
  Error: docs/architecture/decisions/ADR-ARCH-002-six-module-decomposition.md: Episode creation returned None (possible silent
failure)
richardwoollcott@Richards-MBP agentic-dataset-factory %