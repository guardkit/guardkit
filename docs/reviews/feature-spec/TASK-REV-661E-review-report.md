# Review Report: TASK-REV-661E

## Executive Summary

Analysis of the Graphiti seed failures for the feature-spec v2 document (`FEATURE-SPEC-feature-spec-command-v2.md`). All four failure categories have been traced to root causes. **Three are upstream graphiti-core issues** (RediSearch sanitization gap, exception-path coroutine leak); **one is a GuardKit parser limitation** (FeatureSpecParser expects a specific document structure). The episode creation failure is a direct consequence of the RediSearch error — not a separate bug.

| # | Failure | Root Cause | Classification | Severity |
|---|---------|-----------|----------------|----------|
| 1 | RediSearch syntax errors | Backticks/slashes not stripped by `sanitize()` | **Upstream** (graphiti-core) + **GuardKit workaround gap** | High |
| 2 | Episode creation returned None | Consequence of #1 — `add_episode` raises, caught by GuardKit | Not a separate bug | High |
| 3 | Coroutine 'search' was never awaited | Exception during `add_episode` leaks a coroutine | **Upstream** (graphiti-core) | Low |
| 4 | Missing feature overview / no phases | FeatureSpecParser expects `## Feature Overview` and `### Phase N:` headers | **GuardKit** (parser limitation) | Low |

---

## Finding 1: RediSearch Fulltext Query Syntax Errors

### Symptoms

Three `FalkorDB query` errors during episode creation:

```
RediSearch: Syntax error at offset 22 near command
RediSearch: Syntax error at offset 18 near flags
RediSearch: Syntax error at offset 29 near tags
```

The failing query values all contain **backticks** and/or **forward slashes**:

```
(Slash | command | ` | claude/commands/feature | spec | md`)
(CLI | flags | ` | from` | ` | output` | ` | auto` | ...)
(Cross | cutting | tags | ` | smoke` | ` | regression`)
```

### Root Cause

**The `FalkorDriver.sanitize()` method in graphiti-core v0.26.3 does not strip backticks or forward slashes.**

Location: `.venv/lib/python3.14/site-packages/graphiti_core/driver/falkordb_driver.py:289-329`

The `sanitize()` method has a `separator_map` that strips common special characters (`,.<>{}[]"':;!@#$%^&*()-+=~?`) but **omits**:

| Character | In sanitize()? | RediSearch special? | Causes error? |
|-----------|---------------|--------------------|----|
| Backtick `` ` `` | **No** | Yes (query syntax) | **Yes** |
| Forward slash `/` | **No** | Yes (escaping/path) | **Yes** |
| Pipe `|` | **No** | Yes (OR operator) | Potentially |
| Backslash `\` | **No** | Yes (escape char) | Potentially |

The feature-spec document is rich in backtick-quoted code references (`` `claude/commands/feature-spec.md` ``, `` `from` ``, `` `output` ``, etc.). When graphiti-core extracts entities from the episode body, the entity names contain these backticks. During `add_episode`, graphiti-core calls `search` → `build_fulltext_query` → `sanitize` on those entity names, and the unsanitized backticks produce invalid RediSearch query syntax.

### Why the Existing Workaround Doesn't Help

The GuardKit `build_fulltext_query_fixed()` in `falkordb_workaround.py:257-274` addresses a **different** problem — it removes the `@group_id` filter from fulltext queries. But it delegates text sanitization to the **original** `build_fulltext_query`:

```python
result = _original_build_fulltext_query(self, query, None, max_query_length)
```

The original's `sanitize()` still runs with its incomplete character list, so backticks and slashes pass through.

### Upstream Status

The graphiti source repo at `/Users/richardwoollcott/Projects/appmilla_github/graphiti/` has a **slightly newer** version that strips `/`, `\`, and `|` — but still does not strip backticks. This is a bug in all versions.

### Classification

**Primary: Upstream** (graphiti-core `sanitize()` gap)
**Secondary: GuardKit workaround gap** (the workaround could add its own sanitization layer)

### Recommendation

**Extend GuardKit's `build_fulltext_query_fixed()`** to pre-sanitize the query text before passing to the original. This is the correct approach because:

1. Waiting for upstream is uncertain — backticks have been missed across multiple versions
2. The workaround already intercepts this exact method
3. The fix is minimal and testable

```python
# In build_fulltext_query_fixed:
_EXTRA_SANITIZE = str.maketrans({
    '`': ' ',
    '/': ' ',
    '\\': ' ',
    '|': ' ',
})

def build_fulltext_query_fixed(self, query, group_ids=None, max_query_length=128):
    # Pre-sanitize characters missing from upstream sanitize()
    query = query.translate(_EXTRA_SANITIZE)
    result = _original_build_fulltext_query(self, query, None, max_query_length)
    stripped = result.strip()
    if stripped == '()' or stripped == '':
        return '*'
    return result
```

**Also consider**: Filing an upstream issue on `getzep/graphiti` for the backtick gap in `sanitize()`.

---

## Finding 2: Episode Creation Returned None

### Symptom

```
Error: Episode creation returned None (possible silent failure)
```

### Root Cause

**This is not a separate bug — it is a direct consequence of Finding 1.**

The call chain:

1. `_cmd_add_context` calls `client.add_episode()` (graphiti.py:702)
2. `GraphitiClient.add_episode()` calls `_create_episode()` (graphiti_client.py:833)
3. `_create_episode()` calls `self._graphiti.add_episode()` (graphiti_client.py:738)
4. Inside graphiti-core's `add_episode()`, it calls `resolve_extracted_nodes()` → `search()` → `build_fulltext_query()` → **RediSearch error**
5. The RediSearch error propagates as an exception up to graphiti-core's `add_episode()` which re-raises (graphiti.py:996)
6. GuardKit's `_create_episode()` catches it at line 755: `except Exception as e:` → logs `"Episode creation request failed: {e}"` → returns `None`
7. Back in `_cmd_add_context`, the `None` return triggers the `"Episode creation returned None"` error message (graphiti.py:715)

The seed log confirms the sequence: the RediSearch errors appear first (`ERROR:graphiti_core.driver.falkordb_driver`), followed by the episode failure (`WARNING:guardkit.knowledge.graphiti_client`), and finally the summary error.

### Classification

**Not a separate bug.** Resolving Finding 1 will resolve this.

### Recommendation

No separate fix needed. However, the error message `"Episode creation returned None (possible silent failure)"` is misleading — the failure was not silent, it was logged as a WARNING. Consider improving the error message to reference the preceding error.

---

## Finding 3: Coroutine 'search' Was Never Awaited

### Symptom

```
<sys>:0: RuntimeWarning: coroutine 'search' was never awaited
RuntimeWarning: Enable tracemalloc to get the object allocation traceback
```

### Root Cause

**Unawaited coroutine created during exception cleanup in graphiti-core.**

When `add_episode` fails mid-way (due to the RediSearch error), the exception propagates through `graphiti_core/graphiti.py:993-996`:

```python
except Exception as e:
    span.set_status('error', str(e))
    span.record_exception(e)
    raise e
```

During the unwinding, if graphiti-core's internal search operations created coroutine objects that were scheduled but not yet awaited (e.g., within `semaphore_gather` or `resolve_extracted_nodes`), those coroutines become orphaned. Python's GC detects these and emits the `RuntimeWarning`.

The `search` method is one of the methods in `_DECORATED_METHODS` that was re-decorated by the GuardKit workaround. The workaround's wrapper creates coroutines via `execute_for_group(gid)` inside `semaphore_gather`. If an exception interrupts before `semaphore_gather` completes, some of these coroutines may never be awaited.

### Classification

**Upstream** (graphiti-core exception handling doesn't clean up pending coroutines)

### Severity

**Low.** This is a warning, not a functional error. It indicates a resource leak but has no impact on the outcome (the episode already failed for other reasons).

### Recommendation

1. **No immediate fix needed** in GuardKit — this warning is cosmetic during an already-failed operation
2. **Optional**: Add a `warnings.filterwarnings("ignore", "coroutine.*was never awaited", RuntimeWarning)` in `_cmd_add_context` to suppress the noisy warning during batch seeding operations
3. **Upstream**: This is a known pattern in async Python when exceptions interrupt coroutine gathering — not likely to be fixed in graphiti-core soon

---

## Finding 4: Content Parsing Warnings

### Symptoms

```
Warning: Missing feature overview section
Warning: No phases found in feature spec
```

### Root Cause

**`FeatureSpecParser` expects a specific markdown structure that the feature-spec v2 document does not follow.**

The parser at `guardkit/integrations/graphiti/parsers/feature_spec.py` looks for:

1. **`## Feature Overview`** section (line 296): `r"##\s*Feature\s+Overview\s*\n+"`
2. **`### Phase N: Name (Xh)`** headers (line 319): `r"###\s*(Phase\s+\d+[^(\n]*)\s*\([^)]*\)"`

The feature-spec v2 document (`FEATURE-SPEC-feature-spec-command-v2.md`) uses a different structure:

- Section `## 1. Problem Statement` (not `## Feature Overview`)
- Section `## 5. Implementation Plan` with `### Task N:` headers (not `### Phase N:`)
- No `(Xh)` time estimates in section headers

The parser was designed for the Graphiti Refinement MVP spec format, not the `/feature-spec` command's own specification format.

### Impact

**Low.** Despite the warnings, the parser still succeeds (`success=True`) and generates a single overview episode from the full document content. The warnings are informational — the document was still seeded (or would have been, if not for Finding 1). However, no individual task episodes are extracted, so the seeding loses granularity.

### Classification

**GuardKit** (parser limitation — not a bug, but a design gap)

### Recommendation

Two options:

**Option A (Quick fix):** Use the `full-doc` parser type for this document:
```bash
guardkit-py graphiti add-context docs/research/feature-spec/FEATURE-SPEC-feature-spec-command-v2.md --type full-doc
```

**Option B (Enhancement):** Extend `FeatureSpecParser` to handle multiple feature spec formats. The current parser is tightly coupled to one markdown structure. A more flexible approach would:
- Accept `## N. Section Name` as well as `## Feature Overview`
- Accept `### Task N:` as well as `### Phase N:`
- Make the `(Xh)` estimate in headers optional

This is a low-priority enhancement since the `full-doc` parser serves as a fallback.

---

## Summary of Recommendations

| # | Action | Priority | Effort | Type |
|---|--------|----------|--------|------|
| R1 | **Extend `build_fulltext_query_fixed()` to pre-sanitize backticks, slashes, pipes, backslashes** | **High** | Small (~10 lines) | GuardKit fix |
| R2 | File upstream issue on `getzep/graphiti` for backtick gap in `sanitize()` | Medium | Minimal | Upstream report |
| R3 | Improve "Episode creation returned None" error message to reference preceding error | Low | Minimal | GuardKit UX |
| R4 | Optionally suppress coroutine RuntimeWarning during batch seeding | Low | Minimal | GuardKit cosmetic |
| R5 | Re-run seed after R1 fix to verify end-to-end | **High** | Minimal | Verification |
| R6 | Use `--type full-doc` for non-standard feature spec documents, or extend parser | Low | Small-Medium | GuardKit enhancement |

### Blocking Fix

**R1 is the only blocking fix.** Once `build_fulltext_query_fixed()` strips backticks and slashes, the RediSearch errors (Finding 1) will resolve, which will also resolve the episode creation failure (Finding 2). The coroutine warning (Finding 3) will also disappear since it only occurs on the error path.

---

## Appendix: Files Investigated

| File | Relevance |
|------|-----------|
| `guardkit/knowledge/falkordb_workaround.py` | Existing FalkorDB patches — needs extension for backtick sanitization |
| `guardkit/knowledge/graphiti_client.py` | Episode creation flow, error handling |
| `guardkit/cli/graphiti.py` | `add-context` command, error reporting |
| `guardkit/integrations/graphiti/parsers/feature_spec.py` | Feature spec document parser |
| `.venv/.../graphiti_core/driver/falkordb_driver.py` | Upstream `sanitize()` and `build_fulltext_query()` |
| `.venv/.../graphiti_core/graphiti.py` | Upstream `add_episode()` flow |
| `docs/reviews/feature-spec/graphiti_seed_1.md` | Seed log with error output |
| `docs/research/feature-spec/FEATURE-SPEC-feature-spec-command-v2.md` | Source document that failed to seed |
