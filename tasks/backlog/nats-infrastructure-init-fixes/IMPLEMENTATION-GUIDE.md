# Implementation Guide: Fix nats-infrastructure init failures

## Wave 1 — Immediate Fix (15 min)

### TASK-NIIF-001: Fix comma-separated quoted paths in nats-asyncio-service rules
**Mode**: Direct edit (no task-work needed)
**Files**: 9 rule files in `installer/core/templates/nats-asyncio-service/.claude/rules/patterns/`

Convert from invalid YAML (comma-separated quoted strings):
```yaml
# Before (broken — YAML parse error)
---
paths: "**/app.py", "**/handlers/*.py", "**/config.py"
---
```

To valid single-string format (already handled by template_sync.py split logic):
```yaml
# After (valid YAML — single quoted string with commas)
---
paths: "**/app.py, **/handlers/*.py, **/config.py"
---
```

**Affected files** (all under `installer/core/templates/nats-asyncio-service/.claude/rules/patterns/`):
1. `module-level-singleton-for-service-instances.md`
2. `explicit-unidirectional-dependency-flow-(handler-->-service).md`
3. `environment-variable-configuration-via-pydantic-settings.md`
4. `factory-function-pattern-for-test-data.md`
5. `marker-gated-integration-tests.md`
6. `in-memory-broker-testing-via-testnatsbroker.md`
7. `correlation-id-linking-for-request/response-tracing.md`
8. `pub/sub-messaging.md`
9. `handler/service-separation.md`

**Verification**: `python -c "import yaml; yaml.safe_load('paths: \"**/app.py, **/handlers/*.py\"')"` should return dict.

## Wave 2 — Improvements (backlog, parallel)

### TASK-NIIF-002: Add YAML paths validation to template-validate pipeline
**Mode**: task-work
**Complexity**: 3/10

Add a validation check that detects invalid YAML in rule frontmatter `paths:` fields. Specifically catch the comma-separated quoted string pattern that fails `yaml.safe_load()`.

Key file: `installer/core/lib/template_validation/sections/` (add check to existing section or new section)

Expected interface: The validator should parse each rule file's frontmatter with `yaml.safe_load()` and report any `YAMLError` as a validation failure with the file path and error message.

### TASK-NIIF-003: Document --timeout override for local LLM users
**Mode**: direct
**Complexity**: 1/10

Add a note to `guardkit init` help text or output that mentions the `--timeout` flag for local LLM scenarios. Consider adding a hint when a timeout occurs during seeding.

## Execution Order

```
Wave 1: TASK-NIIF-001 (direct, 15 min)

Wave 2: TASK-NIIF-002 ──┐ (parallel, backlog)
        TASK-NIIF-003 ──┘
```
