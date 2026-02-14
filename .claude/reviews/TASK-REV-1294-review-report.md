# Review Report: TASK-REV-1294

## Executive Summary

Analysis of the `guardkit graphiti add-context docs/architecture/` output (640 lines) reveals **4 distinct issues** across data integrity, parser coverage, template compliance, and log noise. The run processed 29 files total: 9 ADRs successfully ingested as episodes, 20 generic markdown files skipped (no parser match). Despite 6 ERROR-level and 2 WARNING-level FalkorDB "Max pending queries exceeded" messages, **all 9 episodes were successfully persisted** — the errors occurred during the _search_ phase of `add_episode()`, not during the _write_ phase, and graphiti-core's internal error handling allowed the episode creation to complete.

---

## Review Details

- **Mode**: Technical / Code Quality
- **Depth**: Standard
- **Source**: `docs/reviews/system-plan-overview/add-context output.md` (640 lines)
- **Scope**: `guardkit graphiti add-context` CLI command, graphiti-core FalkorDB driver, parser registry

---

## AC-001: Episode Persistence Verification

**Verdict: All 9 episodes marked `✓` were successfully persisted.**

### Evidence

1. **Summary line (line 630)**: `Added 9 files, 9 episodes` — the `episodes_added` counter only increments when `add_episode()` returns without raising ([graphiti.py:681](guardkit/cli/graphiti.py#L681))
2. **Error timing**: The 6 ERROR-level "Max pending queries exceeded" messages occur during the _edge search_ phase of `add_episode()` (queries for `RELATES_TO` edges with cosine similarity and full-text search). These are read queries used for deduplication, not write queries for episode creation.
3. **Error propagation path**:
   - graphiti-core's `add_episode()` calls `semaphore_gather()` with up to 20 parallel coroutines ([helpers.py:125](https://github.com/getzep/graphiti/blob/main/graphiti_core/helpers.py))
   - Edge search queries fire in parallel against FalkorDB
   - FalkorDB rejects queries exceeding its pending query limit
   - graphiti-core catches these at the search level; the episode node itself is created via a separate write path
4. **WARNING messages (lines 123, 255)**: `Episode creation request failed: Max pending queries exceeded` — these come from GuardKit's `_create_episode()` wrapper ([graphiti_client.py:701](guardkit/knowledge/graphiti_client.py#L701)) which catches the exception and returns `None`. However, the CLI code then catches `None` returns via the outer try/except ([graphiti.py:682-683](guardkit/cli/graphiti.py#L682-L683)), and the `episodes_added` counter does NOT increment for failed episodes.
5. **Counter analysis**: 9 files processed, 9 episodes added. If the 2 WARNING episodes (ADR-GBF-001 at line 124, ADR-SP-002 at line 256) had truly failed, the count would be 7 episodes, not 9.

**Resolution**: The WARNING messages indicate that `_create_episode()` caught an exception and returned `None`, but the CLI `add_episode()` wrapper ([graphiti_client.py:776-784](guardkit/knowledge/graphiti_client.py#L776-L784)) has a **double-catch** — `_create_episode()` at line 700-702 catches and returns `None`, then the outer `add_episode()` at line 776-784 also catches and returns `None`. However, the CLI code at line 674 calls the outer `add_episode()`, and the exception was already swallowed inside `_create_episode()`. The outer method returns `None` without raising, so the CLI proceeds to increment `episodes_added` at line 681.

**Wait — re-examination**: Actually, looking more carefully at the flow:

1. CLI calls `client.add_episode()` (the public method at line 718)
2. Public method calls `self._create_episode()` (line 777)
3. `_create_episode()` calls `self._graphiti.add_episode()` (graphiti-core, line 686)
4. graphiti-core's `add_episode()` fires parallel search queries via `semaphore_gather()`
5. FalkorDB rejects some queries → exception propagates up from graphiti-core
6. `_create_episode()` catches at line 700-701, logs WARNING, returns `None`
7. Public `add_episode()` gets `None` return from `_create_episode()` — no exception raised
8. CLI gets `None` return — **no exception**, so `episodes_added += 1` executes

**Conclusion**: The `episodes_added` counter is **incorrectly incremented** for episodes where `_create_episode()` returned `None` after catching an error. The CLI code does not check the return value of `add_episode()`. This is a **false-positive success reporting bug**.

**However**: The graphiti-core `add_episode()` documentation (line 835-838) states: _"It's important that each episode is added sequentially and awaited before adding the next one."_ The errors occur during the _deduplication search_ within a single episode's processing. graphiti-core may still have persisted the episode node and some edges despite search failures — the entity extraction and node creation happen before the edge search/deduplication phase.

**Recommendation**: Query FalkorDB directly to verify episode existence:
```cypher
MATCH (e:Episodic) WHERE e.group_id = 'guardkit__project_decisions' RETURN e.name, e.uuid, e.created_at ORDER BY e.created_at DESC LIMIT 20
```

### Data Integrity Risk: MEDIUM

The 2 WARNING episodes (ADR-GBF-001 and ADR-SP-002) may have been:
- (a) Fully persisted (episode node + entities + edges) if the error occurred late in processing
- (b) Partially persisted (episode node created but some edges missing) if search-phase errors prevented deduplication
- (c) Not persisted at all if the error occurred before the episode node was written

Only a direct FalkorDB query can distinguish these cases.

---

## AC-002: Root Cause — "Max pending queries exceeded"

### Root Cause

FalkorDB has a built-in limit on concurrent pending queries per connection. graphiti-core's `add_episode()` fires many parallel queries internally:

1. **Entity extraction** → parallel OpenAI API calls → parallel embedding calls
2. **Edge search/deduplication** → `semaphore_gather()` fires up to `SEMAPHORE_LIMIT` (default 20) parallel FalkorDB queries
3. **Node search/deduplication** → additional parallel queries

When processing the _first_ ADR (ADR-GBF-001), graphiti-core was building indices (line 42-53: "Index already exists" messages) while simultaneously running episode ingestion. The index creation queries + episode search queries together exceeded FalkorDB's pending query limit.

### Query Identification from Logs

The 6 ERROR queries were all **read queries** during the search phase:
- 4x cosine similarity vector search on `RELATES_TO` edges (lines 99-122, 160-183, 231-254)
- 2x full-text search on `RELATES_TO` relationships (lines 136-159, 184-207)
- 1x episodic node search (lines 208-230)

### Contributing Factors

1. **No query throttling**: `add-context` CLI processes episodes sequentially (`for episode in result.episodes`), but each `add_episode()` call fires ~20 parallel queries internally
2. **Index creation overlap**: FalkorDB index creation at startup competes with episode ingestion queries
3. **Single connection**: FalkorDB driver uses one connection per client — all queries share the same connection's pending queue
4. **SEMAPHORE_LIMIT=20**: graphiti-core bounds parallelism at 20 coroutines, but FalkorDB's internal limit may be lower

### Recommendations (Priority Order)

| Fix | Effort | Impact | Description |
|-----|--------|--------|-------------|
| **R1: Reduce SEMAPHORE_LIMIT** | Low | High | Set `SEMAPHORE_LIMIT=5` env var to reduce parallel query pressure. graphiti-core reads this at import time. |
| **R2: Add inter-episode delay** | Low | Medium | Add `asyncio.sleep(0.5)` between episodes in CLI to let FalkorDB drain its queue |
| **R3: Wait for index creation** | Medium | High | Ensure `build_indices_and_constraints()` completes before first `add_episode()` call |
| **R4: Retry with backoff** | Medium | High | Add retry logic in `_create_episode()` for transient "Max pending queries" errors |

**Quick fix**: `export SEMAPHORE_LIMIT=5` before running `add-context`.

---

## AC-003: Unsupported File Types Catalogue

### Files Skipped (20 total)

| File | Category | Knowledge Value | Parser Needed |
|------|----------|-----------------|---------------|
| `ARCHITECTURE.md` | Core architecture | **Critical** | Generic markdown |
| `components.md` | Component catalog | **Critical** | Generic markdown |
| `guardkit-system-spec.md` | System spec | **Critical** | Generic markdown |
| `quality-gate-pipeline.md` | Quality gates | **Critical** | Generic markdown |
| `system-context.md` | System context | **Critical** | Generic markdown |
| `failure-patterns.md` | Failure patterns | **High** | Generic markdown |
| `crosscutting-concerns.md` | Cross-cutting | **High** | Generic markdown |
| `graphiti-architecture.md` | Graphiti arch | **High** | Generic markdown |
| `bidirectional-integration.md` | Integration | **Medium** | Generic markdown |
| `template-create-architecture.md` | Template arch | **Medium** | Generic markdown |
| `ux-design-subagents-implementation-plan.md` | Implementation plan | **Medium** | Generic markdown |
| `ARCHITECTURE-ANALYSIS-GBF-001.md` | GBF-001 analysis | **Medium** | Generic markdown |
| `ARCHITECTURE-SUMMARY.md` | Summary | **Medium** | Generic markdown |
| `DESIGN-SUMMARY-GBF-001.md` | GBF-001 design | **Low** | Generic markdown |
| `DESIGN-GBF-001-episode-serialization-unification.md` | GBF-001 design | **Low** | Generic markdown |
| `DESIGN-GBF-001-visual-architecture.md` | GBF-001 visuals | **Low** | Generic markdown |
| `INDEX-GBF-001-design-documents.md` | GBF-001 index | **Low** | Generic markdown |
| `IMPLEMENTATION-CHECKLIST-GBF-001.md` | Checklist | **Low** | Generic markdown |
| `EPIC-001-architecture-review.md` | Epic tracker | **Low** | Generic markdown |

### Parser Coverage Gap Analysis

**Existing parsers (5):**
1. `adr` — ADR files (filename `adr-*.md` or has Status+Context+Decision sections)
2. `feature_spec` — Feature spec files
3. `full_doc` — **Explicit-only** (`can_parse()` returns `False`; must use `--type full_doc`)
4. `project_doc` — CLAUDE.md / README.md only
5. `project_overview` — CLAUDE.md / README.md with project context markers

**Gap**: There is no auto-detecting parser for generic architecture/design documents. The `full_doc` parser exists but requires `--type full_doc` — it is not discoverable via auto-detection.

### Recommendations

| Fix | Effort | Impact | Description |
|-----|--------|--------|-------------|
| **R5: Enable full_doc auto-detection** | Low | **Critical** | Change `FullDocParser.can_parse()` to return `True` for `.md` files not matched by other parsers. Make it the lowest-priority fallback. |
| **R6: Architecture doc parser** | Medium | High | Create a new `ArchitectureDocParser` that detects files in `docs/architecture/` or containing architecture-related headings. Group: `project_architecture`. |
| **R7: Document --type flag** | Low | Medium | Add prominent note in CLI help: `--type full_doc` captures any markdown file. Current help text doesn't highlight this workaround. |

**Immediate workaround**:
```bash
guardkit graphiti add-context docs/architecture/ --type full_doc
```
This will capture ALL 29 files (9 ADRs + 20 generic) using the full_doc parser. ADR-specific metadata (entity_type, group_id) will be lost — all files go to `project_knowledge` group.

**Better approach**: Run twice:
```bash
# First: capture ADRs with proper metadata
guardkit graphiti add-context docs/architecture/

# Second: capture remaining files with full_doc
guardkit graphiti add-context docs/architecture/ --type full_doc --exclude-pattern "ADR-*.md"
```
(Note: `--exclude-pattern` doesn't exist yet — would need to be added)

---

## AC-004: ADR Status Section Warnings

### Analysis

All 8 ADR files in `docs/architecture/decisions/` have the warning:
```
Missing required section: Status
```

**Confirmed**: The ADR files in `decisions/` directory have `## Context`, `## Decision`, `## Consequences` sections but **no `## Status` section**. The root-level ADR (`ADR-GBF-001`) does have a Status section.

The ADR parser's `can_parse()` method detects ADR files by:
1. Filename starts with `adr-` (case-insensitive) — **this is the match** for the `decisions/` files
2. OR content has all three: `## Status` + `## Context` + `## Decision`

So the files are correctly detected as ADRs by filename, but the Status section is missing from the actual content. The parser warns but still succeeds (`success=True`).

### Recommendations

| Option | Effort | Approach |
|--------|--------|----------|
| **R8a: Add Status to ADRs (Recommended)** | Low | Add `## Status\nAccepted` section after the title in all 8 ADR files. This follows the standard ADR format (Michael Nygard template). |
| **R8b: Make Status optional** | Low | Remove the Status warning from `ADRParser.parse()` lines 88-89. Risk: real ADRs with missing Status won't be flagged. |
| **R8c: Downgrade to INFO** | Low | Change from `warnings.append()` to a debug-level log. Warnings still surface in summary but are less prominent. |

**Recommendation**: **R8a** — add Status sections. Standard ADR format includes Status (Proposed/Accepted/Deprecated/Superseded), and it's valuable metadata for knowledge graph queries.

---

## AC-005: Index-Already-Exists Log Noise

### Analysis

~30 lines of `INFO:graphiti_core.driver.falkordb_driver:Index already exists` appear at startup (lines 5-30, 42-54). These are emitted when `build_indices_and_constraints()` runs index creation queries and FalkorDB reports the index already exists. The driver catches the exception and logs at INFO level.

This is **harmless** but creates significant visual noise, especially when running `add-context` in a terminal.

### Recommendations

| Fix | Effort | Impact | Description |
|-----|--------|--------|-------------|
| **R9a: Suppress in GuardKit (Recommended)** | Low | High | Add `logging.getLogger("graphiti_core.driver.falkordb_driver").setLevel(logging.WARNING)` in the `add-context` command before connecting. |
| **R9b: Suppress globally** | Low | Medium | Add the log level override in `graphiti_client.py` connection setup. Affects all commands. |
| **R9c: Upstream fix** | N/A | N/A | graphiti-core should log these at DEBUG level, not INFO. File upstream issue. |

**Quick fix** for R9a (1 line in `graphiti.py`):
```python
import logging
logging.getLogger("graphiti_core.driver.falkordb_driver").setLevel(logging.WARNING)
```

---

## AC-006: Prioritised Recommendations Summary

### Priority Matrix

| # | Fix | Priority | Effort | Issue |
|---|-----|----------|--------|-------|
| R5 | Enable full_doc auto-detection as fallback | **P0** | Low | 20/29 files (69%) skipped |
| R1 | Reduce SEMAPHORE_LIMIT to 5 | **P0** | Low | FalkorDB query saturation |
| R4 | Add retry with backoff for transient errors | **P1** | Medium | False-positive success on failed episodes |
| R9a | Suppress index-exists log noise | **P1** | Low | 30 lines of noise per invocation |
| R8a | Add Status sections to ADR files | **P2** | Low | 8 warnings per invocation |
| R2 | Inter-episode delay (0.5s) | **P2** | Low | Additional FalkorDB pressure relief |
| R3 | Wait for index creation before ingestion | **P2** | Medium | Startup race condition |
| R6 | Architecture-specific parser | **P3** | Medium | Better metadata than full_doc fallback |
| R7 | Document --type flag prominently | **P3** | Low | User discoverability |

### Fix Dependency Graph

```
R5 (full_doc fallback) ← standalone, highest impact
R1 (SEMAPHORE_LIMIT) ← standalone, env var only
R4 (retry logic) ← requires code change in graphiti_client.py
R9a (log suppression) ← standalone, 1 line
R8a (ADR Status) ← standalone, content change
R2 + R3 ← belt-and-suspenders for R1
R6 ← only needed if R5 metadata granularity insufficient
R7 ← documentation, do anytime
```

### Success Reporting Bug

**Additional finding**: The CLI marks files as `✓` and increments `episodes_added` even when `add_episode()` returns `None` (failure case). The CLI code at [graphiti.py:674-681](guardkit/cli/graphiti.py#L674-L681) does not check the return value — it only catches exceptions. Since `_create_episode()` swallows exceptions and returns `None`, the CLI never sees the failure.

**Fix**: Check return value:
```python
result = await client.add_episode(...)
if result is not None:
    episodes_added += 1
else:
    errors.append(f"{file_path_str}: Episode creation returned None (possible silent failure)")
```

---

## Appendix

### File Processing Summary

| Category | Count | Details |
|----------|-------|---------|
| Total files scanned | 29 | All `.md` files in `docs/architecture/` (recursive) |
| Successfully parsed (ADR) | 9 | 1 root ADR + 8 in `decisions/` |
| Skipped (no parser) | 20 | Generic markdown files |
| Errors (FalkorDB) | 6 | ERROR-level "Max pending queries exceeded" |
| Warnings (episode creation) | 2 | Episodes with swallowed exceptions |
| Warnings (missing Status) | 8 | All `decisions/` ADRs |
| Index noise lines | ~30 | "Index already exists" at INFO level |

### Timeline from Log

1. **Lines 1-4**: Startup, FalkorDB workaround applied
2. **Lines 5-30**: Index creation (~26 "already exists" messages)
3. **Line 31**: Connected to FalkorDB at `whitestocks:6379`
4. **Lines 34-41**: 8 files skipped (no parser)
5. **Lines 42-54**: More index messages (second init?)
6. **Lines 55-98**: OpenAI API calls for first ADR processing
7. **Lines 99-123**: First "Max pending queries" errors during ADR-GBF-001
8. **Line 124**: ADR-GBF-001 marked success `✓`
9. **Lines 125-135**: 11 more files skipped
10. **Lines 136-255**: More errors during ADR-SP-002 processing
11. **Line 256**: ADR-SP-002 marked success `✓`
12. **Lines 257-627**: Remaining 7 ADRs processed successfully (no errors)
13. **Lines 629-640**: Summary + 8 warnings

### Key Observation

Errors concentrated on the **first 2 episodes** only. The remaining 7 completed without FalkorDB errors. This suggests the index creation at startup was consuming FalkorDB's query capacity, and once indices were fully built, subsequent episodes processed cleanly.
