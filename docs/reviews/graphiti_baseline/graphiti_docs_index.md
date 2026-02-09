
docs/reviews/graphiti_baseline/graphiti-technical-reference.md
docs/reviews/graphiti_baseline/graphiti-storage-theory.md
docs/deep-dives/graphiti/episode-metadata.md
docs/guides/graphiti-integration-guide.md
docs/architecture/graphiti-architecture.md


Revised Review Complete - TASK-GBF-REV

  Summary of All Documents Updated

  Original scope (3 baseline docs):
  Document: .claude/reviews/TASK-REV-C632-review-report.md
  Changes Made: Findings 3 & 6 marked RESOLVED, score 82->86, module count 30->50+, categories 16->18, task lineage updated
  ────────────────────────────────────────
  Document: docs/reviews/graphiti_baseline/graphiti-technical-reference.md
  Changes Made: Seeding layer expanded (9->24 rows), added unified serialization section, updated orchestrator code example
  ────────────────────────────────────────
  Document: docs/reviews/graphiti_baseline/graphiti-storage-theory.md
  Changes Made: Updated to_episode_body() convention, episode body notes, extension checklist
  Expanded scope (4 additional docs found during revision):
  Document: docs/deep-dives/graphiti/episode-metadata.md
  Changes Made: _add_episodes() location fixed (seeding.py -> seed_helpers.py), added seed_helpers.py reference
  ────────────────────────────────────────
  Document: docs/guides/graphiti-integration-guide.md
  Changes Made: "13 knowledge categories" -> "18 knowledge categories", expanded seeding table from 13 to 18 rows
  ────────────────────────────────────────
  Document: docs/architecture/graphiti-architecture.md
  Changes Made: to_episode_body() extension example updated to return domain-only dict, seeding orchestrator example updated, note updated to
  include
     FEAT-GBF
  ────────────────────────────────────────
  Document: docs/architecture/ADR-GBF-001-unified-episode-serialization.md
  Changes Made: Status changed from "Proposed" to "Accepted and Implemented"
  No changes needed:
  - docs/deep-dives/graphiti/episode-upsert.md - Already current

Revised for Per-Thread Factory Migration - TASK-DOC-GTP6

  Summary of Documents Updated (FEAT-C90E: Graphiti Per-Thread Migration)

  Document: docs/reviews/graphiti_baseline/graphiti-technical-reference.md
  Changes Made: Key exports table updated (added GraphitiClientFactory, get_factory). Connection lifecycle code updated from singleton to per-thread factory pattern.
  ────────────────────────────────────────
  Document: docs/reviews/graphiti_baseline/graphiti-storage-theory.md
  Changes Made: ADR-5 rewritten from "Singleton Pattern for Client" to "Per-Thread Factory Pattern for Client" with cross-loop error rationale.
  ────────────────────────────────────────
  Document: docs/architecture/graphiti-architecture.md
  Changes Made: init_graphiti/get_graphiti section rewritten for per-thread semantics. Added GraphitiClientFactory API section with full method reference.
  ────────────────────────────────────────
  Document: docs/guides/graphiti-integration-guide.md
  Changes Made: FAQ and multi-project sections updated to note thread-local client behavior.
  ────────────────────────────────────────
  Document: .claude/rules/graphiti-knowledge.md
  Changes Made: Added "Threading Model" section with per-thread factory rules and code examples.
  ────────────────────────────────────────
  No changes needed:
  - docs/deep-dives/graphiti/episode-metadata.md - No singleton references
  - docs/deep-dives/graphiti/episode-upsert.md - Already current (get_graphiti() API unchanged)
  - docs/architecture/ADR-GBF-001-unified-episode-serialization.md - No singleton references