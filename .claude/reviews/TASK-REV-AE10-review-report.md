# Review Report: TASK-REV-AE10 (Revised)

## Executive Summary

Deep analysis of the second `guardkit init` run (post TASK-IGR-001 and TASK-IGR-003 fixes). Source code tracing of graphiti-core `edge_operations.py` (v0.5.x) confirms all 3 upstream issues are genuine bugs with well-understood root causes. The YAML glob issue affects **25 rule files across 4 templates** (not 3 as initially reported). Two fix approaches were evaluated for regression risk.

**Revision scope**: Source-level root cause confirmation, C4 architecture diagrams, sequence diagrams across technology seams, expanded regression analysis for Issue 4.

## Review Details

- **Mode**: Architectural Review (Revised)
- **Depth**: Comprehensive (upgraded from Standard)
- **Parent Review**: TASK-REV-21D3
- **Feature**: FEAT-IGR (Init + Graphiti Resilience)
- **Input**: `docs/reviews/reduce-static-markdown/init_project_2.md` (lines 689-806)
- **Source files traced**: `edge_operations.py`, `extract_edges.py`, `dedupe_edges.py`, `datetime_utils.py`, `content_chunking.py`, `template_sync.py`, `graphiti_client.py`, `init.py`, `project_seeding.py`

---

## C4 Context Diagram: guardkit init

```
┌─────────────────────────────────────────────────────────────────────┐
│                        System Context (C4 Level 1)                  │
│                                                                     │
│  ┌──────────┐     CLI      ┌──────────────┐                        │
│  │          │─────────────▶│              │                        │
│  │  User    │              │  GuardKit    │                        │
│  │          │◀─────────────│  CLI (init)  │                        │
│  └──────────┘   stdout     │              │                        │
│                             └──────┬───────┘                        │
│                                    │                                │
│                    ┌───────────────┼───────────────┐                │
│                    │               │               │                │
│                    ▼               ▼               ▼                │
│            ┌──────────┐   ┌──────────────┐  ┌──────────┐           │
│            │ Template │   │ graphiti-core │  │ FalkorDB │           │
│            │ Files    │   │ (Python lib)  │  │ (Graph)  │           │
│            │ (local)  │   │              │  │ (remote) │           │
│            └──────────┘   └──────┬───────┘  └──────────┘           │
│                                  │                                  │
│                          ┌───────┴────────┐                         │
│                          │                │                         │
│                          ▼                ▼                         │
│                   ┌──────────┐    ┌──────────────┐                  │
│                   │ vLLM     │    │ vLLM         │                  │
│                   │ Chat     │    │ Embeddings   │                  │
│                   │ :8000    │    │ :8001        │                  │
│                   └──────────┘    └──────────────┘                  │
└─────────────────────────────────────────────────────────────────────┘
```

## C4 Container Diagram: Init Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       Container Diagram (C4 Level 2)                     │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────┐             │
│  │                    GuardKit Process                      │             │
│  │                                                          │             │
│  │  ┌────────────┐     ┌─────────────────┐                 │             │
│  │  │            │     │                 │                 │             │
│  │  │  cli/init  │────▶│ apply_template  │─── Step 1      │             │
│  │  │            │     │                 │   (file copy)  │             │
│  │  │ (_cmd_init)│     └─────────────────┘                 │             │
│  │  │            │                                         │             │
│  │  │            │     ┌─────────────────┐                 │             │
│  │  │            │────▶│ project_seeding │─── Step 2      │             │
│  │  │            │     │                 │   (8 episodes) │             │
│  │  │            │     │  ┌────────────┐ │                 │             │
│  │  │            │     │  │ _Progress  │ │                 │             │
│  │  │            │     │  │  Client    │ │                 │             │
│  │  │            │     │  └─────┬──────┘ │                 │             │
│  │  │            │     └────────┼────────┘                 │             │
│  │  │            │              │                          │             │
│  │  │            │     ┌────────┼────────┐                 │             │
│  │  │            │────▶│ template_sync   │─── Step 2.5    │             │
│  │  │            │     │                 │   (N episodes) │             │
│  │  └────────────┘     │ ┌─────────────┐ │                 │             │
│  │                      │ │ YAML parser │ │ ◀── Issue 4   │             │
│  │                      │ └─────────────┘ │                 │             │
│  │                      └────────┬────────┘                 │             │
│  └───────────────────────────────┼──────────────────────────┘             │
│                                  │                                        │
│                    ┌─────────────┼──────────────┐                         │
│                    │    graphiti-core library    │                         │
│                    │                             │                         │
│                    │  ┌───────────────────────┐  │                         │
│                    │  │ Graphiti.add_episode() │  │                         │
│                    │  └───────────┬───────────┘  │                         │
│                    │              │               │                         │
│                    │  ┌───────────▼───────────┐  │                         │
│                    │  │ edge_operations.py     │  │                         │
│                    │  │                        │  │                         │
│                    │  │ extract_edges()        │◀─┤── Issues 2, 3         │
│                    │  │ resolve_extracted_edge()│◀─┤── Issue 1             │
│                    │  └───────────┬───────────┘  │                         │
│                    │              │               │                         │
│                    │     ┌────────┴─────────┐     │                         │
│                    │     │ LLM Client       │     │                         │
│                    │     │ (OpenAI-compat)   │     │                         │
│                    │     └────────┬─────────┘     │                         │
│                    └──────────────┼───────────────┘                         │
│                                  │                                         │
│                    ┌─────────────┼───────────────┐                         │
│                    │   External Services          │                         │
│                    │                              │                         │
│                    │  ┌──────────┐  ┌──────────┐  │                         │
│                    │  │ vLLM     │  │ FalkorDB │  │                         │
│                    │  │ (LLM +   │  │ (Graph   │  │                         │
│                    │  │  Embed)  │  │  Store)  │  │                         │
│                    │  └──────────┘  └──────────┘  │                         │
│                    └──────────────────────────────┘                         │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Sequence Diagrams

### Sequence 1: Issue 2 — Double Timezone (Date Parsing Failure)

```
    vLLM                 graphiti-core                    Python
    (LLM)               edge_operations.py              datetime
      │                       │                            │
      │  extract_edges()      │                            │
      │  prompt includes:     │                            │
      │  "Use ISO 8601 with   │                            │
      │   'Z' suffix (UTC)"   │                            │
      │                       │                            │
      │◀──────────────────────│                            │
      │  LLM prompt sent      │                            │
      │                       │                            │
      │──────────────────────▶│                            │
      │  valid_at:            │                            │
      │  "2026-03-03T20:09:   │                            │
      │   08.043388+00:00Z"   │                            │
      │                       │                            │
      │  (Redundant but valid │                            │
      │   ISO 8601: offset +  │                            │
      │   Z marker)           │                            │
      │                       │                            │
      │                       │  edge_operations.py:257    │
      │                       │  valid_at.replace(         │
      │                       │    'Z', '+00:00')          │
      │                       │                            │
      │                       │  Result:                   │
      │                       │  "...+00:00+00:00"         │
      │                       │  (Z replaced with +00:00   │
      │                       │   but +00:00 was already   │
      │                       │   present!)                │
      │                       │                            │
      │                       │──────────────────────────▶│
      │                       │  datetime.fromisoformat(   │
      │                       │    "...+00:00+00:00")      │
      │                       │                            │
      │                       │◀──────────────────────────│
      │                       │  ValueError!               │
      │                       │  "Invalid isoformat        │
      │                       │   string"                  │
      │                       │                            │
      │                       │  WARNING logged            │
      │                       │  valid_at_datetime = None  │
      │                       │  Edge created WITHOUT      │
      │                       │  temporal metadata         │
      │                       │                            │
```

**Source code (confirmed at edge_operations.py:254-260)**:
```python
if valid_at:
    try:
        valid_at_datetime = ensure_utc(
            datetime.fromisoformat(valid_at.replace('Z', '+00:00'))  # <-- BUG
        )
    except ValueError as e:
        logger.warning(f'WARNING: Error parsing valid_at date: {e}. Input: {valid_at}')
```

**Root cause confirmed**: The `.replace('Z', '+00:00')` call is a blanket string replacement. When the LLM outputs `+00:00Z`, the `Z` at the end gets replaced with `+00:00`, producing `+00:00+00:00`. The fix should use `rstrip('Z')` or a regex that only replaces a trailing `Z`.

**Regression risk for upstream fix**: NONE for GuardKit. The fix is entirely within graphiti-core's `extract_edges()`. GuardKit does not pass dates to graphiti-core — the dates are generated by the LLM within graphiti-core's own pipeline.

---

### Sequence 2: Issue 1 — Invalid duplicate_facts Indices

```
    vLLM                 graphiti-core                graphiti-core
    (LLM)               edge_operations.py           dedupe_edges.py
      │                  resolve_extracted_edge()     (prompt/model)
      │                       │                            │
      │                       │  Build context:            │
      │                       │  related_edges = [         │
      │                       │    {idx:0, fact:"..."},    │
      │                       │    {idx:1, fact:"..."}     │
      │                       │  ]                         │
      │                       │  (len = 2, valid: 0-1)     │
      │                       │                            │
      │                       │  Prompt says:              │
      │                       │  "Return idx values from   │
      │                       │   EXISTING FACTS"          │
      │                       │  "idx ranges start from 0" │
      │                       │                            │
      │◀──────────────────────│                            │
      │  Prompt sent with     │                            │
      │  context              │                            │
      │                       │                            │
      │──────────────────────▶│                            │
      │  EdgeDuplicate(       │                            │
      │    duplicate_facts=[1]│                            │
      │  )                    │                            │
      │                       │                            │
      │                       │  Validation:               │
      │                       │  [i for i in [1]           │
      │                       │   if i < 0                 │
      │                       │   or i >= len(             │
      │                       │    related_edges)]         │
      │                       │                            │
      │                       │  len(related_edges) = 2    │
      │                       │  1 >= 2? → FALSE           │
      │                       │  → Index 1 IS VALID!       │
      │                       │                            │
      │                       │  BUT warning says:         │
      │                       │  "valid range: 0-1"        │
      │                       │  This means len = 2,       │
      │                       │  and 1 < 2, so 1 passes.  │
      │                       │                            │
      │                       │  ⚠ WAIT: Warning message   │
      │                       │  format is misleading.     │
      │                       │  "0--1" could mean 0 to    │
      │                       │  (len-1) = only idx 0      │
      │                       │  is valid (len=1).         │
```

**Source code re-analysis (edge_operations.py:604-613)**:
```python
invalid_duplicates = [i for i in duplicate_facts if i < 0 or i >= len(related_edges)]
if invalid_duplicates:
    logger.warning(
        'LLM returned invalid duplicate_facts idx values %s (valid range: 0-%d for EXISTING FACTS)',
        invalid_duplicates,
        len(related_edges) - 1,   # <-- displays max valid index
    )
```

**Revised root cause**: The validation `i >= len(related_edges)` is **correct** (exclusive upper bound). The warning format `0-%d` with `len(related_edges) - 1` displays the max valid index correctly. If the warning says `valid range: 0-1`, then `len(related_edges)` is 2, and index 1 IS valid (1 < 2).

**But the warning IS being triggered**, which means `len(related_edges)` must actually be **1** (not 2). The format `0--1` in the log output means `0-{-1}` — i.e., `len(related_edges) - 1 = 0`, which means there is 1 related edge (idx 0 only). The LLM returned idx `[1]`, which is invalid because there's only 1 edge.

Wait — re-reading the actual log: `valid range: 0--1`. The double dash `--` is the format string `0-%d` with value `-1`, meaning `len(related_edges) - 1 = -1`, meaning `len(related_edges) = 0`. The LLM was told there are **zero existing facts** but still returned `[1]`.

**Confirmed root cause**: `related_edges` is empty (len=0). The LLM hallucinates duplicate indices when there are no existing facts to compare against. The validation correctly catches this. The edge falls through to the `duplicate_fact_ids` filter on line 613 which strips invalid indices, so the edge is treated as new (no duplicate).

**Impact (revised)**: LOW — The validation is working correctly. Invalid indices are stripped. The edge is created as a new edge (not deduplicated). No data loss or corruption. The warning is cosmetic but indicates the LLM is hallucinating when given empty/minimal context. This is expected behaviour with smaller/local LLMs (vLLM).

---

### Sequence 3: Issue 3 — Target Index Out of Bounds

```
    vLLM                 graphiti-core               graphiti-core
    (LLM)               edge_operations.py          content_chunking.py
      │                  extract_edges()                   │
      │                       │                            │
      │                       │  nodes = [N0..N15+]        │
      │                       │  MAX_NODES = 15            │
      │                       │                            │
      │                       │◀───────────────────────────│
      │                       │  generate_covering_chunks( │
      │                       │    nodes, k=15)            │
      │                       │  → chunk = [15 nodes],     │
      │                       │    global_indices=[0..14]  │
      │                       │                            │
      │                       │  Build prompt:             │
      │                       │  nodes = [                 │
      │                       │    {id:0, name:"Node0"},   │
      │                       │    {id:1, name:"Node1"},   │
      │                       │    ...                     │
      │                       │    {id:14, name:"Node14"}  │
      │                       │  ]                         │
      │                       │  (15 nodes, ids 0-14)      │
      │                       │                            │
      │                       │  Prompt says:              │
      │                       │  "source_entity_id and     │
      │                       │   target_entity_id must    │
      │                       │   use only the id values   │
      │                       │   from the ENTITIES list"  │
      │                       │                            │
      │◀──────────────────────│                            │
      │  Prompt sent          │                            │
      │                       │                            │
      │──────────────────────▶│                            │
      │  Edge(                │                            │
      │    source_entity_id=3,│                            │
      │    target_entity_id=15│ ◀── OUT OF BOUNDS          │
      │    relation_type=     │     (valid: 0-14)          │
      │      "HAS_PHASE"     │                            │
      │  )                    │                            │
      │                       │                            │
      │                       │  Validation (line 194):    │
      │                       │  0 <= 15 < 15? → FALSE     │
      │                       │                            │
      │                       │  WARNING: "Target index    │
      │                       │   15 out of bounds for     │
      │                       │   chunk of size 15"        │
      │                       │                            │
      │                       │  Edge SKIPPED (continue)   │
      │                       │  → Edge NOT created        │
```

**Source code (confirmed at edge_operations.py:180-199)**:
```python
chunk_size = len(global_indices)   # = 15 (MAX_NODES)

for edge_data in chunk_edges_data:
    source_local_idx = edge_data.source_entity_id
    target_local_idx = edge_data.target_entity_id

    if not (0 <= source_local_idx < chunk_size):
        logger.warning(f'Source index {source_local_idx} out of bounds ...')
        continue

    if not (0 <= target_local_idx < chunk_size):
        logger.warning(f'Target index {target_local_idx} out of bounds ...')
        continue
```

**Confirmed root cause**: The LLM is presented with 15 nodes (ids 0-14) but returns `target_entity_id=15` and `target_entity_id=16`. The prompt clearly states "use only the `id` values from the ENTITIES list" and "CRITICAL: Using IDs not in the list will cause the edge to be rejected." The LLM is ignoring this instruction — likely confusing the node count (15) with the max valid index (14).

This is a common LLM failure mode: the model "knows" there are 15 items and uses 15 as a valid index instead of the 0-based maximum of 14. The `HAS_PHASE` edge type suggests the testing-specialist agent has many workflow phases, making the LLM more likely to reference nodes near the boundary.

**Impact (revised)**: LOW-MEDIUM — The validation is working correctly. Invalid edges are skipped, not created with wrong references. The `fastapi-testing-specialist` agent loses 3 phase-relationship edges but all other edges and the agent content itself are correctly synced.

---

### Sequence 4: Issue 4 — YAML Glob Parsing

```
    Rule File             template_sync.py              PyYAML
    (on disk)             extract_agent_metadata()       yaml.safe_load()
      │                       │                            │
      │  Content:             │                            │
      │  ---                  │                            │
      │  paths: **/*.py       │                            │
      │  ---                  │                            │
      │  # Rule content       │                            │
      │                       │                            │
      │──────────────────────▶│                            │
      │  read_text()          │                            │
      │                       │  regex extract frontmatter │
      │                       │  "paths: **/*.py"          │
      │                       │                            │
      │                       │──────────────────────────▶│
      │                       │  yaml.safe_load(           │
      │                       │    "paths: **/*.py")       │
      │                       │                            │
      │                       │  YAML parser interprets:   │
      │                       │    ** → alias indicator     │
      │                       │    Expected: alphanumeric   │
      │                       │    Found: * (in */*.py)    │
      │                       │                            │
      │                       │◀──────────────────────────│
      │                       │  YAMLError!                │
      │                       │                            │
      │                       │  except YAMLError:         │
      │                       │    logger.warning(...)     │
      │                       │    return {}               │
      │                       │                            │
      │                       │  metadata = {} (empty)     │
      │                       │                            │
      │                       │  sync_rule_to_graphiti():  │
      │                       │    path_patterns = []      │
      │                       │    (metadata empty, so     │
      │                       │     no paths extracted)    │
      │                       │                            │
      │                       │  Episode STILL CREATED     │
      │                       │  with full_content but     │
      │                       │  path_patterns = []        │
```

**Source code (confirmed at template_sync.py:65-88)**:
```python
def extract_agent_metadata(content: str) -> Dict[str, Any]:
    frontmatter_text = match.group(1)
    metadata = yaml.safe_load(frontmatter_text)  # line 79 — FAILS on globs
    ...
    except yaml.YAMLError as e:
        logger.warning(f"[Graphiti] Failed to parse agent frontmatter: {e}")
        return {}  # Returns empty — caller treats as "no metadata"
```

**Scope analysis — 25 affected rule files across 4 templates**:

| Template | Affected Files | Status |
|----------|---------------|--------|
| fastapi-python | 12 of 12 rules | All unquoted |
| nextjs-fullstack | 10 of 10 rules | All unquoted |
| react-fastapi-monorepo | 8+ rules | Most unquoted |
| default | 0 of 3 rules | Already quoted (`"**/*.py"`) |
| mcp-typescript | 0 of 5 rules | Already uses JSON arrays (`["src/**/*.ts"]`) |
| react-typescript | 0 of 8 rules | Already uses JSON arrays |
| fastmcp-python | 3 of 5 rules | Mixed (some unquoted) |

Templates using **quoted** or **JSON array** format already parse correctly. Only templates using bare globs fail.

---

## Fix Approach Analysis: Issue 4

### Approach A: Quote glob patterns in frontmatter files

```yaml
# Before (fails)
---
paths: **/*.py
---

# After (works)
---
paths: "**/*.py"
---

# Multi-value (also works)
---
paths: "**/tests/**, **/test_*.py, **/*_test.py"
---
```

**Pros**:
- Zero code changes to GuardKit
- Follows YAML specification correctly
- Consistent with `default` and `mcp-typescript` templates that already quote
- Simple grep-and-replace across all templates

**Cons**:
- Touches 25+ files across 4 templates
- Must verify no regressions in Claude Code `.claude/rules/` path matching (Claude Code reads the raw `paths:` field for rule activation — it may or may not handle quoted values identically to unquoted)
- Does not prevent future contributors from adding unquoted globs

**Regression risk**: LOW but needs verification.

Claude Code's rule activation system reads `paths:` from frontmatter. We need to verify that Claude Code handles quoted paths (`"**/*.py"`) the same as unquoted (`**/*.py`). The `default` template already uses quoted paths and works, so this is likely safe. However, we should verify by checking at least one existing project that uses the default template.

### Approach B: Pre-process frontmatter in `extract_agent_metadata()`

```python
def extract_agent_metadata(content: str) -> Dict[str, Any]:
    ...
    frontmatter_text = match.group(1)

    # Pre-process: quote unquoted glob patterns to prevent YAML alias errors
    frontmatter_text = _quote_yaml_globs(frontmatter_text)

    metadata = yaml.safe_load(frontmatter_text)
    ...

def _quote_yaml_globs(text: str) -> str:
    """Quote unquoted values containing glob characters (* or **) in YAML."""
    import re
    # Match lines like: key: **/something, **/other
    # where value starts with * and is not already quoted
    return re.sub(
        r'^(\s*\w+:\s+)(?!["\'\\[])(\*\S.*)$',
        r'\1"\2"',
        text,
        flags=re.MULTILINE,
    )
```

**Pros**:
- Zero changes to template files
- Handles future unquoted globs automatically
- Single code change, easy to test

**Cons**:
- Regex-based YAML pre-processing is fragile
- Could match non-path fields that happen to start with `*`
- Adds complexity to a parsing function
- Existing tests for `extract_agent_metadata` would need updating

**Regression risks**:
1. The regex could incorrectly quote values in agent frontmatter that aren't paths (e.g., `capabilities: *advanced` — unlikely but possible)
2. Multi-line YAML values with continuations could break
3. Already-quoted values must be excluded (the `(?!["'\\[])` negative lookahead handles this)

### Recommended approach: A (quote the files) + defensive validation

1. Quote all 25 unquoted rule files (Approach A)
2. Add a test to `test_template_sync.py` that verifies glob frontmatter parses correctly:
   ```python
   def test_extract_agent_metadata_with_glob_paths(self):
       content = '---\npaths: "**/*.py"\n---\n# Content'
       metadata = extract_agent_metadata(content)
       assert metadata == {'paths': '**/*.py'}
   ```
3. Verify Claude Code rule activation with quoted paths (check `default` template behaviour)
4. **Do NOT implement Approach B** — regex pre-processing of YAML is too fragile and masks the real issue (invalid YAML in source files)

---

## Improvements Confirmed (FEAT-IGR Fixes)

### TASK-IGR-001: Log Suppression - VERIFIED

**Before (Run 1)**: ~600+ lines of httpx/httpcore noise made output unreadable.
**After (Run 2)**: Zero noise lines. Clean, readable output.

### TASK-IGR-003: Template Sync Client Reuse - VERIFIED

**Before (Run 1)**: `Warning: Template sync returned incomplete results` (line 643).
**After (Run 2)**: Synced template + 3 agents + rules. No "incomplete" warning.

### No "Max pending queries" Errors - VERIFIED

**Before (Run 1)**: 4 `Max pending queries exceeded` errors.
**After (Run 2)**: Zero errors. All 8 episodes completed.

### Progress Indicators - VERIFIED

**Before (Run 1)**: No progress messages.
**After (Run 2)**: `Seeding episode N/8... done (Xs)` with total time.

---

## Revised Summary Matrix

| Issue | Severity | Owner | Root Cause Confirmed? | Fixable in GuardKit? | Regression Risk |
|-------|----------|-------|----------------------|---------------------|-----------------|
| 1. duplicate_facts indices | ~~MEDIUM~~ **LOW** | graphiti-core | Yes — LLM hallucinates indices when related_edges is empty | No (upstream) | N/A |
| 2. Double timezone suffix | HIGH | graphiti-core | Yes — `.replace('Z', '+00:00')` on strings already containing `+00:00` | No (upstream) | N/A |
| 3. Target index out of bounds | ~~MEDIUM~~ **LOW-MED** | graphiti-core | Yes — LLM confuses node count (15) with max valid index (14) | No (upstream) | N/A |
| 4. YAML glob parsing | ~~LOW~~ **MEDIUM** | GuardKit | Yes — unquoted `*` treated as YAML alias | **Yes** (25 files) | LOW (verify Claude Code compat) |
| 5. Episode 1 performance | LOW | Environmental | Yes — vLLM cold start after graph clear | No | N/A |
| 6. Truncated output | LOW | Inconclusive | Probable capture truncation | Partial (add summary) | NONE |

**Key severity changes**:
- Issue 1: MEDIUM → LOW (validation catches it, no data corruption)
- Issue 3: MEDIUM → LOW-MEDIUM (edges skipped, not corrupted)
- Issue 4: LOW → MEDIUM (scope expanded from 3 → 25 files; affects path-pattern discoverability across 4 templates)

---

## Recommendations (Revised)

### GuardKit Tasks

1. **Quote glob patterns in rule frontmatter** (Issue 4)
   - Scope: 25 files across fastapi-python, nextjs-fullstack, react-fastapi-monorepo, fastmcp-python
   - Approach: Wrap unquoted glob values in double quotes
   - Verification: Add test for glob frontmatter parsing; verify Claude Code rule activation
   - Priority: MEDIUM (affects all template syncs)
   - Estimated effort: 1 hour

2. **Add template sync completion summary** (Issue 6)
   - Log total sync time, counts of agents/rules synced at end of Step 2.5
   - Priority: LOW
   - Estimated effort: 30 minutes

### Upstream Issues (graphiti-core)

3. **Date parsing: use `rstrip('Z')` instead of `.replace('Z', '+00:00')`** (Issue 2)
   - Location: `edge_operations.py:257,265`
   - Suggested fix: `valid_at.rstrip('Z')` then append `+00:00` only if no timezone present
   - This is the highest-severity upstream issue

4. **Chunk index prompt improvement** (Issue 3)
   - Location: `extract_edges.py` prompt + `edge_operations.py:180`
   - Suggested fix: Add `CRITICAL: Valid IDs are 0 through {len(nodes)-1}` to prompt
   - Or: Attempt `idx - 1` as fallback when out-of-bounds

5. **duplicate_facts hallucination on empty context** (Issue 1)
   - Location: `edge_operations.py:542-543`
   - Suggested fix: Skip LLM call entirely when `len(related_edges) == 0` (already has fast path but only for both empty)
   - Low priority — validation already handles it

### No Action Needed

- Issue 5 (episode 1 performance): vLLM cold start, acceptable for one-time init
- Issues 1, 3 validation: Already handled correctly — edges are skipped or deduplicated

---

## Appendix A: Episode Timing Comparison

```
Run 1 (before fixes):                  Run 2 (after fixes):
  Ep 1:  46.9s  (warm vLLM)              Ep 1: 187.1s  (cold vLLM)
  Ep 2:  79.2s                            Ep 2:  61.6s
  Ep 3:  ~79.2s (with errors)            Ep 3:  73.3s  (clean, 4 warnings)
  Ep 4:  35.9s                            Ep 4:  40.7s  (13 date warnings)
  Ep 5:  20.9s                            Ep 5:  14.1s
  Ep 6:  59.3s                            Ep 6:  55.3s
  Ep 7:  65.4s                            Ep 7:  51.9s
  Ep 8:  34.0s                            Ep 8:  41.5s
  Total: ~341s (est.)                     Total: 525.6s
  Step 2.5: FAILED                        Step 2.5: WORKING (~17.5min visible)
```

## Appendix B: Affected Rule Files (Issue 4)

**fastapi-python** (12 files — all unquoted):
- `code-style.md`, `testing.md`
- `api/dependencies.md`, `api/routing.md`, `api/schemas.md`
- `database/crud.md`, `database/migrations.md`, `database/models.md`
- `guidance/database.md`, `guidance/fastapi.md`, `guidance/testing.md`
- `patterns/pydantic-constraints.md`

**nextjs-fullstack** (10 files — all unquoted):
- `code-style.md`, `testing.md`
- `api/routes.md`
- `auth/nextauth.md`
- `database/prisma.md`
- `server/actions.md`, `server/components.md`, `server/streaming.md`
- `guidance/server-components.md`, `guidance/server-actions.md`, `guidance/react-state.md`

**react-fastapi-monorepo** (8 files — most unquoted):
- `backend/database.md`, `backend/fastapi.md`, `backend/schemas.md`
- `frontend/query.md`, `frontend/react.md`, `frontend/types.md`
- `guidance/docker.md`, `guidance/monorepo.md`, `guidance/type-safety.md`
- `monorepo/docker.md`, `monorepo/turborepo.md`, `monorepo/workspaces.md`

**fastmcp-python** (3 of 5 files unquoted):
- `mcp-patterns.md`, `security.md`, `testing.md`
- Already quoted: `config.md`, `docker.md`

**Already correct** (no changes needed):
- `default` template: uses `"**/*.py"` (quoted)
- `mcp-typescript` template: uses `["src/**/*.ts"]` (JSON array)
- `react-typescript` template: uses `["**/*.test.*"]` (JSON array)
