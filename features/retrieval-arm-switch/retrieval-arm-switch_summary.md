# Feature Spec Summary: Fleet-Memory Retrieval Arm Switch and Retrieval Logging

**Feature ID**: FEAT-ABL-001 (memory ablation, scope §4)
**Stack**: python
**Generated**: 2026-07-03T12:00:00Z
**Scenarios**: 14 total (3 smoke, 2 regression)
**Assumptions**: 7 total (4 high / 3 medium / 0 low confidence)
**Review required**: No

## Scope

An in-client retrieval arm switch (`FLEET_MEMORY_RETRIEVAL=off|fixture:<id>`, read in
`_load_fleet_config_from_env`, enforced inside `FleetMemoryClient.search` exactly like the
existing `enabled=false` gate) so that the AutoBuildContextLoader, turn-continuation and
template-pattern paths stay byte-identical between ablation arms. Plus structured per-call
JSONL retrieval logging with per-item `natural_key` + `score`, captured between `fm_search()`
and `assemble_context()` where per-item identity still exists, via a new optional
`items:[{id,score}]` field on `query_logger.log_query`, called from the AutoBuild chain.

Explicitly out of scope: reusing `--no-context` or `FLEET_MEMORY_ENABLED=false` (both null
the whole loader), any fleet-memory repo change (the toggle lives in guardkit's client).

## Scenario Counts by Category

| Category | Count |
|----------|-------|
| Key examples (@key-example) | 4 |
| Boundary conditions (@boundary) | 3 |
| Negative cases (@negative) | 5 |
| Edge cases (@edge-case) | 4 |

## Acceptance mapping (scope §4 FEAT-ABL-001)

| Acceptance criterion | Scenarios |
|----------------------|-----------|
| Off-arm rollout shows zero retrieval calls in its log | "Off arm suppresses retrieval...", "A disabled backend returns no results...", "A fixture arm with an unresolvable DSN fails closed", "A failed store search writes no retrieval-log entry" |
| Fixture arm logs item ids + scores | "Fixture arm resolves the fixture corpus and logs per-item identity", "A fixture-arm search with no matching items still writes a retrieval-log entry" |
| No other code-path divergence | "Context loading reports the same retrieval status across arms", off gate placed inside `search()` mirroring the enabled gate |
| Three arm states (build-plan validation) | unset → "Unset arm preserves current retrieval behaviour"; off → "Off arm suppresses retrieval..."; fixture → "Fixture arm resolves the fixture corpus..." |

## Deferred Items

None.

## Open Assumptions (low confidence)

None. Medium-confidence items (fixture DSN env var naming ASSUM-002, fail-closed invalid
values ASSUM-003, log-on-every-store-reaching-arm ASSUM-005) were confirmed during the
autonomous review pass against scope §4 and build-plan P4.

## Files touched by implementation (expected)

- `guardkit/knowledge/fleet_memory_client.py` — `FLEET_MEMORY_RETRIEVAL` in
  `_load_fleet_config_from_env` (~:622); arm gate + per-item log emit inside `search()`
  (~:257-318); fixture DSN resolution
- `guardkit/knowledge/query_logger.py` — optional `items:[{id,score}]` schema field
- Tests for the three arm states

## Integration with /feature-plan

This summary can be passed to `/feature-plan` as a context file:

    /feature-plan FEAT-ABL-001 --context features/retrieval-arm-switch/retrieval-arm-switch_summary.md
