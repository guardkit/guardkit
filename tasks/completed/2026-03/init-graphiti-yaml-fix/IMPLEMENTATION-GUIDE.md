# Implementation Guide: Init Graphiti YAML Fix

**Feature**: FEAT-IGR (Init + Graphiti Resilience)
**Parent Review**: TASK-REV-AE10
**Created**: 2026-03-03

## Problem Statement

`guardkit init` Step 2.5 (template sync) fails to parse YAML frontmatter in rule files containing unquoted glob patterns. This causes rule metadata (path patterns) to be missing from the Graphiti knowledge graph, reducing discoverability. Additionally, Step 2.5 produces no completion summary, making it impossible to verify sync completion.

## Wave 1 (Parallel — No Dependencies)

Both tasks are independent and can execute in parallel.

| Task | Description | Method | Complexity |
|------|-------------|--------|------------|
| TASK-IGR-YQ01 | Quote glob patterns in 38 rule frontmatter files | task-work | 2 |
| TASK-IGR-TS01 | Add template sync completion summary | task-work | 2 |

## Execution Strategy

### TASK-IGR-YQ01: Quote Glob Patterns

**Approach**: For each affected rule file, wrap the `paths:` value in double quotes.

**Verification**:
```bash
# Verify no unquoted glob patterns remain
grep -rn '^paths: \*' installer/core/templates/ --include="*.md" | grep -v '"' | grep -v '\['
# Should return 0 results

# Verify YAML parsing works
python3 -c "
import yaml
yaml.safe_load('paths: \"**/*.py\"')
print('OK')
"
```

**Test to add** in `tests/knowledge/test_template_sync.py`:
```python
def test_extract_agent_metadata_with_glob_paths(self):
    content = '---\npaths: \"**/*.py\"\n---\n# Content'
    metadata = extract_agent_metadata(content)
    assert metadata == {'paths': '**/*.py'}
```

### TASK-IGR-TS01: Template Sync Summary

**Approach**: Add counters to `sync_template_to_graphiti()` and log a summary at the end.

**Key change** in `guardkit/knowledge/template_sync.py`:
```python
async def sync_template_to_graphiti(template_path: Path, client=None) -> bool:
    import time
    start_time = time.time()
    agents_synced = 0
    rules_synced = 0
    warnings = 0

    # ... existing sync logic, increment counters ...

    elapsed = time.time() - start_time
    logger.info(
        f"[Graphiti] Template sync complete: "
        f"{agents_synced} agents, {rules_synced} rules synced ({elapsed:.1f}s)"
        + (f", {warnings} warnings" if warnings else "")
    )
    return True
```

## Upstream Issues (Not in Scope)

These were identified in the review but are graphiti-core bugs, not GuardKit fixes:

1. **Issue 2 (HIGH)**: Double timezone suffix — `edge_operations.py:257` uses `.replace('Z', '+00:00')` which doubles timezone when input has `+00:00Z`
2. **Issue 3 (LOW-MED)**: LLM returns 1-based indices for 0-based chunk arrays
3. **Issue 1 (LOW)**: LLM hallucinates duplicate indices on empty context

## Post-Implementation Verification

After both tasks complete:
1. Run `guardkit init fastapi-python -n test-project --copy-graphiti-from .` on a test project
2. Verify Step 2.5 output shows completion summary with counts
3. Verify no YAML parse warnings for rule frontmatter
4. Verify rule metadata appears in Graphiti (path_patterns field populated)
