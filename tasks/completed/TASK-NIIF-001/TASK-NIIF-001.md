---
id: TASK-NIIF-001
title: Fix comma-separated quoted paths in template rule files (4 templates, 15 files)
status: completed
created: 2026-04-04T14:00:00Z
updated: 2026-04-04T15:10:00Z
completed: 2026-04-04T15:10:00Z
completed_location: tasks/completed/TASK-NIIF-001/
priority: high
tags: [yaml, templates, rules, nats-asyncio-service, default, langchain-deepagents-orchestrator, fastmcp-python, bug-fix]
parent_review: TASK-REV-2266
feature_id: FEAT-NIIF
implementation_mode: direct
wave: 1
complexity: 1
---

# Task: Fix comma-separated quoted paths in template rule files (4 templates, 15 files)

## Description

15 rule files across 4 templates use comma-separated quoted strings for the `paths:` frontmatter field. This is invalid YAML — `yaml.safe_load()` fails with "expected block end, but found comma". The paths are individually quoted but not wrapped as a YAML list or single string.

This is distinct from TASK-NIF-001 (completed) which fixed **unquoted** glob patterns in other templates.

## Affected Files

### nats-asyncio-service (9 files)

All under `installer/core/templates/nats-asyncio-service/.claude/rules/patterns/`:

1. `module-level-singleton-for-service-instances.md`
   - Before: `paths: "**/app.py", "**/handlers/*.py", "**/config.py"`
   - After: `paths: "**/app.py, **/handlers/*.py, **/config.py"`

2. `explicit-unidirectional-dependency-flow-(handler-->-service).md`
   - Before: `paths: "**/handlers/*.py", "**/services/*.py", "**/app.py"`
   - After: `paths: "**/handlers/*.py, **/services/*.py, **/app.py"`

3. `environment-variable-configuration-via-pydantic-settings.md`
   - Before: `paths: "**/config.py", "**/.env*", "**/docker-compose*.yml"`
   - After: `paths: "**/config.py, **/.env*, **/docker-compose*.yml"`

4. `factory-function-pattern-for-test-data.md`
   - Before: `paths: "**/tests/conftest.py", "**/tests/*.py"`
   - After: `paths: "**/tests/conftest.py, **/tests/*.py"`

5. `marker-gated-integration-tests.md`
   - Before: `paths: "**/tests/test_integration*.py", "**/pyproject.toml", "**/docker-compose*.yml"`
   - After: `paths: "**/tests/test_integration*.py, **/pyproject.toml, **/docker-compose*.yml"`

6. `in-memory-broker-testing-via-testnatsbroker.md`
   - Before: `paths: "**/tests/test_handler*.py", "**/tests/test_*.py"`
   - After: `paths: "**/tests/test_handler*.py, **/tests/test_*.py"`

7. `correlation-id-linking-for-request/response-tracing.md`
   - Before: `paths: "**/schemas/*.py", "**/schemas.py", "**/services/*.py"`
   - After: `paths: "**/schemas/*.py, **/schemas.py, **/services/*.py"`

8. `pub/sub-messaging.md`
   - Before: `paths: "**/handlers/*.py", "**/app.py"`
   - After: `paths: "**/handlers/*.py, **/app.py"`

9. `handler/service-separation.md`
   - Before: `paths: "**/handlers/*.py", "**/services/*.py"`
   - After: `paths: "**/handlers/*.py, **/services/*.py"`

### default (1 file)

10. `installer/core/templates/default/.claude/rules/code-style.md`
    - Before: `paths: "**/*.py", "**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx"`
    - After: `paths: "**/*.py, **/*.ts, **/*.tsx, **/*.js, **/*.jsx"`

### langchain-deepagents-orchestrator (3 files)

All under `installer/core/templates/langchain-deepagents-orchestrator/.claude/rules/patterns/`:

11. `two-model-orchestration.md`
    - Before: `paths: "**/agent.py", "**/agents.py", "**/orchestrator*.py", "**/config*.yaml"`
    - After: `paths: "**/agent.py, **/agents.py, **/orchestrator*.py, **/config*.yaml"`

12. `domain-prompt-injection.md`
    - Before: `paths: "**/agent.py", "**/domains/**", "**/prompts/**"`
    - After: `paths: "**/agent.py, **/domains/**, **/prompts/**"`

13. `subagent-composition.md`
    - Before: `paths: "**/agents.py", "**/agent.py"`
    - After: `paths: "**/agents.py, **/agent.py"`

### fastmcp-python (2 files)

14. `installer/core/templates/fastmcp-python/.claude/rules/config.md`
    - Before: `paths: "**/.mcp.json", "**/pyproject.toml", "**/.env", "**/config.py", "**/config/*.py"`
    - After: `paths: "**/.mcp.json, **/pyproject.toml, **/.env, **/config.py, **/config/*.py"`

15. `installer/core/templates/fastmcp-python/.claude/rules/docker.md`
    - Before: `paths: "**/Dockerfile", "**/docker-compose.yml", "**/docker-compose.yaml"`
    - After: `paths: "**/Dockerfile, **/docker-compose.yml, **/docker-compose.yaml"`

## Acceptance Criteria

- [x] All 15 files updated to single-string comma-separated format
- [x] `python -c "import yaml; yaml.safe_load(open(f).read().split('---')[1])"` passes for each file
- [x] Existing unit tests still pass (71 passed, 34 skipped)

## Implementation Notes

The template_sync.py parser at line 528-530 already handles single-string comma-separated paths correctly via `.split(',')`. No parser changes needed — only data fixes.
