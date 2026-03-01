# Feature Spec Summary: Eval Runner — GuardKit vs Vanilla Comparison Pipeline

**Stack**: python
**Generated**: 2026-03-01T00:00:00Z
**Scenarios**: 32 total (3 smoke, 0 regression)
**Assumptions**: 7 total (5 high / 2 medium / 0 low confidence)
**Review required**: No

## Scope

This specification covers the `guardkit_vs_vanilla` eval type within the Eval Runner system. It defines the behaviour of workspace provisioning (forked pairs from separate templates), input resolution (text, file, Linear ticket), sequential arm execution (GuardKit pipeline then vanilla Claude Code), quantitative metrics extraction from evidence files, delta-based LLM judging, result classification (PASSED/FAILED/ESCALATED), and Graphiti storage with comparison-specific fields. Edge cases cover arm failure isolation, sandbox enforcement, NATS delivery guarantees, API rate-limit retry, and Graphiti failure resilience.

## Scenario Counts by Category

| Category | Count |
|----------|-------|
| Key examples (@key-example) | 6 |
| Boundary conditions (@boundary) | 8 |
| Negative cases (@negative) | 6 |
| Edge cases (@edge-case) | 12 |

## Deferred Items

None — all groups accepted.

## Open Assumptions (low confidence)

None — all assumptions are high or medium confidence and have been confirmed by the human operator.

## Notable Assumption Overrides

- **ASSUM-004**: LLM judge retry count overridden from 3 to 5 retries with exponential backoff (user preference for eval stability over fail-fast).

## Integration with /feature-plan

This summary can be passed to `/feature-plan` as a context file:

```
/feature-plan "Eval Runner GuardKit vs Vanilla Pipeline" --context features/eval-runner-gkvv/eval-runner-gkvv_summary.md
```
