# Implementation Guide: Fix nats-core init failures

## Wave 1 — Immediate Fix (15 min)

### TASK-NIF-001: Quote glob patterns in rule files
**Mode**: Direct edit (no task-work needed)
**Files**: 8 rule files across 4 templates

Simply add quotes around the `paths:` values in YAML frontmatter:
```yaml
# Before (broken)
---
paths: **/*.py
---

# After (fixed)
---
paths: "**/*.py"
---
```

**Verification**: Run `python -c "import yaml; yaml.safe_load('paths: \"**/*.py\"')"` — should return dict without error.

## Wave 2 — Improvements (backlog, parallel)

### TASK-NIF-002: LLM health check in guardkit init
**Mode**: task-work
**Complexity**: 4/10

Add a pre-flight GET request to `/v1/models` on the configured LLM endpoint before Step 3 (system knowledge seeding). If unreachable within 5s, offer to skip seeding.

Key file: `guardkit/cli/init.py` (or wherever Step 3 seeding is triggered)

### TASK-NIF-003: Glob validation in template-validate
**Mode**: task-work
**Complexity**: 3/10

Add a check to the template validation pipeline that catches unquoted glob patterns in rule frontmatter before they ship.

Key file: Template validation module (see `/template-validate` command spec)

## Manual Step (outside this repo)

Update nats-core `.guardkit/graphiti.yaml`:
```bash
cd /Users/richardwoollcott/Projects/appmilla_github/nats-core
# Edit .guardkit/graphiti.yaml — change LLM endpoint from GB10 to MacBook
```

## Execution Order

```
Wave 1: TASK-NIF-001 (direct, 15 min)
         └── Manual: fix nats-core config

Wave 2: TASK-NIF-002 ──┐ (parallel, backlog)
        TASK-NIF-003 ──┘
```
