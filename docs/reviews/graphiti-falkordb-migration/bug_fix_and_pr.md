The document has been created at docs/reviews/graphiti-falkordb-migration/upstream-decorator-bug-report.md. It
  includes:

  1. Bug Summary — one-paragraph description with the one-line fix
  2. Root Cause Analysis — the decorator condition (> 1 vs >= 1), the driver mutation mechanism in add_episode(), all
   4 affected methods, and why Neo4j isn't affected
  3. The Fix — exact diff of the one-character change with rationale
  4. Minimal Reproduction Script — standalone Python script that demonstrates the bug with FalkorDB Docker + expected
   vs actual output
  5. Test Cases — 7 unit tests covering: single group_id clone (the regression test), multi group_id, no group_ids,
  empty group_ids, Neo4j not affected, sequential add-then-search scenario, and a source inspection test to verify
  the fix
  6. Workaround — how GuardKit's monkey-patch works, including the critical detail about re-decorating already-bound
  methods via __wrapped__
  7. Impact Assessment — table showing which scenarios are affected
  8. Timeline — links to upstream issue #1161, PR #1170, and our reproduction comment