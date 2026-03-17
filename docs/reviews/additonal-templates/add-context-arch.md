richardwoollcott@Richards-MBP agentic-dataset-factory % guardkit graphiti add-context docs/architecture/ --pattern "**/*.md"
Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

INFO:graphiti_core.graphiti:Completed add_episode in 88854.13098335266 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [docs/architecture/system-context.md]: nodes=13, edges=17, invalidated=0
  ✓ docs/architecture/system-context.md (full_doc)
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 120s: docs/architecture/ARCHITECTURE.md
  ⚠ docs/architecture/ARCHITECTURE.md (full_doc) — 1 episode(s) failed
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 120s: docs/architecture/container.md
  ⚠ docs/architecture/container.md (full_doc) — 1 episode(s) failed
WARNING:guardkit.knowledge.graphiti_client:Episode creation timed out after 120s: docs/architecture/domain-model.md
WARNING:guardkit.knowledge.graphiti_client:Graphiti disabled after 3 consecutive failures -- continuing without knowledge graph context
  ⚠ docs/architecture/domain-model.md (full_doc) — 1 episode(s) failed
  ⚠ docs/architecture/decisions/ADR-ARCH-001-modular-monolith.md (adr) — 1 episode(s) failed
  ⚠ docs/architecture/decisions/ADR-ARCH-004-chromadb-embedded-persistent.md (adr) — 1 episode(s) failed
  ⚠ docs/architecture/decisions/ADR-ARCH-006-sequential-generation.md (adr) — 1 episode(s) failed
  ⚠ docs/architecture/decisions/ADR-ARCH-009-non-deterministic-generation.md (adr) — 1 episode(s) failed
  ⚠ docs/architecture/decisions/ADR-ARCH-002-six-module-decomposition.md (adr) — 1 episode(s) failed
  ⚠ docs/architecture/decisions/ADR-ARCH-005-configurable-agent-models.md (adr) — 1 episode(s) failed
  ⚠ docs/architecture/decisions/ADR-ARCH-007-structured-json-logging.md (adr) — 1 episode(s) failed
  ⚠ docs/architecture/decisions/ADR-ARCH-003-docker-containerisation.md (adr) — 1 episode(s) failed
  ⚠ docs/architecture/decisions/ADR-ARCH-008-start-fresh-restart.md (adr) — 1 episode(s) failed

Summary:
  Added 13 files, 1 episode
  Failed: 12 episodes

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
  Error: docs/architecture/decisions/ADR-ARCH-001-modular-monolith.md: Episode creation returned None (possible silent failure)
  Error: docs/architecture/decisions/ADR-ARCH-004-chromadb-embedded-persistent.md: Episode creation returned None (possible silent
failure)
  Error: docs/architecture/decisions/ADR-ARCH-006-sequential-generation.md: Episode creation returned None (possible silent failure)
  Error: docs/architecture/decisions/ADR-ARCH-009-non-deterministic-generation.md: Episode creation returned None (possible silent
failure)
  Error: docs/architecture/decisions/ADR-ARCH-002-six-module-decomposition.md: Episode creation returned None (possible silent
failure)
  Error: docs/architecture/decisions/ADR-ARCH-005-configurable-agent-models.md: Episode creation returned None (possible silent
failure)
  Error: docs/architecture/decisions/ADR-ARCH-007-structured-json-logging.md: Episode creation returned None (possible silent
failure)
  Error: docs/architecture/decisions/ADR-ARCH-003-docker-containerisation.md: Episode creation returned None (possible silent
failure)
  Error: docs/architecture/decisions/ADR-ARCH-008-start-fresh-restart.md: Episode creation returned None (possible silent failure)
richardwoollcott@Richards-MBP agentic-dataset-factory %