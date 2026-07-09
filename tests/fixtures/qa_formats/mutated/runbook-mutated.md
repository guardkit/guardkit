<!-- qa-format: runbook format_version: 1.0 -->
# MUTATED runbook — must FAIL loudly: no Facts header, a phase with no Pass check,
# a phase with an unknown type.

## Phase 0: Pre-flight — type: preflight

Some prose but no pass check.

```bash
docker compose version
```

## Phase 1: Do a thing — type: teleport

**Pass:** the thing is done.
