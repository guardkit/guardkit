# Cross-Cutting Concerns

> 7 shared concerns affecting multiple components

## XC-error-handling: Error Handling & Graceful Degradation

- **Approach**: 3-layer degradation pattern for all Graphiti operations -- try operation, catch exception, return None/empty list (never crash). All knowledge-dependent features work without Graphiti by falling back to training knowledge.
- **Affected Components**: Knowledge Layer, Planning Engine, AutoBuild, CLI Layer
- **Constraints**: No Graphiti operation may raise an exception to the caller. All returns must be Optional or have empty defaults. Connection failures during init are logged as warnings, not errors.

## XC-thread-safety: Thread Safety

- **Approach**: Per-thread Graphiti clients via GraphitiClientFactory. Each thread gets its own client instance to avoid shared connection state. Factory maintains thread-local storage.
- **Affected Components**: Knowledge Layer, Feature Orchestrator (parallel wave execution)
- **Constraints**: Never share a GraphitiClient across threads. Always use get_graphiti() which returns the thread-local instance. macOS FD soft limit raised to 4096 for parallel task execution.

## XC-logging: Structured Logging

- **Approach**: Module-prefixed log messages using `[Graphiti]`, `[AutoBuild]`, `[QualityGate]`, `[Planning]` prefixes for easy grep/filtering. Python logging module with configurable levels.
- **Affected Components**: All
- **Constraints**: Never log sensitive data (API keys, credentials). Always log at WARNING for degradation events, INFO for normal operations, DEBUG for verbose output.

## XC-token-budgeting: Token Budgeting & Progressive Disclosure

- **Approach**: Progressive disclosure via core/ext file splits -- agents have a core file (always loaded) and ext file (loaded on demand). Context injection has per-category token budgets: Feature Context 15%, Similar Outcomes 25%, Relevant Patterns 20%, Architecture Context 20%, Warnings 15%, Domain Knowledge 5%.
- **Affected Components**: Planning Engine, AutoBuild (Coach context injection), Agent System
- **Constraints**: Coach context total ~4000 tokens. System overview condensed to 800 tokens for injection. /feature-plan context capped at 600 tokens.

## XC-test-enforcement: Test Enforcement

- **Approach**: Zero-test anomaly detection blocks completion when a task claims done but has zero tests. Auto-fix loop attempts up to 3 test repairs before blocking. 100% test pass rate required -- no partial passes accepted.
- **Affected Components**: Quality Gates, AutoBuild, task-work command
- **Constraints**: Tasks of type DOCUMENTATION and SCAFFOLDING are exempt from test requirements. All other types require tests.

## XC-backward-compat: Backward Compatibility

- **Approach**: All Graphiti-dependent features degrade gracefully when Graphiti is unavailable. Projects that haven't been seeded or haven't run /system-plan work identically to pre-Graphiti GuardKit. New entity types (role_constraints, quality_gate_configs) have hardcoded fallback defaults.
- **Affected Components**: All (especially Knowledge Layer, Planning Engine)
- **Constraints**: Never require Graphiti for basic task workflow. Never require /system-plan before /feature-plan. Always provide hardcoded defaults for missing knowledge.

## XC-httpx-cleanup: httpx Connection Cleanup

- **Approach**: Custom exception handler suppresses closed-loop errors from httpx when FalkorDB connections are torn down. Prevents noisy stack traces on normal shutdown.
- **Affected Components**: Knowledge Layer
- **Constraints**: Only suppress known httpx closed-transport errors. Log unexpected exceptions normally.
