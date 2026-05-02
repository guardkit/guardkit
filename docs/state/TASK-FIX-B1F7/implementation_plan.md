# Implementation Plan: TASK-FIX-B1F7

**Task**: Graphiti MCP HTTP transport ignores client `group_id`; `/task-complete` should fall back to CLI
**Complexity**: 4 / 90 min estimate
**Workflow**: design-only (Phase 2.8 checkpoint pending user approval)
**Generated**: 2026-05-02

---

## 1. Files to Create / Modify

| Path | Action | Summary |
|------|--------|---------|
| `installer/core/commands/lib/graphiti_response_parser.py` | **Create** | Pure parser + override-detector; no I/O |
| `tests/unit/commands/test_graphiti_response_parser.py` | **Create** | Unit tests for the parser and detector |
| `installer/core/commands/task-complete.md` | **Modify** | Add "Step 2a: Detect group_id override" block after Write 1 |
| `.claude/rules/graphiti-knowledge-graph.md` | **Modify** | Add "Known MCP transport limitation" warning section |
| `docs/guides/graphiti-claude-code-integration.md` | **Modify** | Add "group_id coercion on HTTP transport" note under Troubleshooting |

No changes to `.mcp.json`, `infra/`, or any Python under `guardkit/` — see section 7.

---

## 2. Module Design

**`installer/core/commands/lib/graphiti_response_parser.py`**

```python
"""
Parser and override-detector for Graphiti MCP add_memory responses.

Used by task-complete.md prose logic and testable independently of Claude.

Public API:
  parse_queued_group(response_message: str) -> Optional[str]
  detect_group_override(requested: str, response_message: str) -> GroupOverrideResult
"""
```

Public functions:

```python
def parse_queued_group(response_message: str) -> Optional[str]:
    """
    Extract the actual group from an add_memory response message.

    Parses: "Episode '...' queued for processing in group '{group}'"
    Returns the group string, or None if the pattern is not found.
    """

def detect_group_override(
    requested_group_id: str,
    response_message: str,
) -> GroupOverrideResult:
    """
    Compare the caller-requested group_id against the server-reported group.

    Returns a GroupOverrideResult with:
      .overridden: bool       — True when actual != requested
      .requested: str         — the group the caller asked for
      .actual: Optional[str]  — the group the server reported (None if unparseable)
      .warning: Optional[str] — human-readable warning text, or None if no override
    """
```

`GroupOverrideResult` is a `dataclass` (no Pydantic; internal state only — follows `dataclasses.md` pattern). Fields: `overridden: bool`, `requested: str`, `actual: Optional[str]`, `warning: Optional[str]`.

Zero external dependencies beyond stdlib (`re`, `dataclasses`, `typing`). Does NOT import from `guardkit/` — keeps it importable in `installer/` path without namespace hazards (see `.claude/rules/namespace-hygiene.md`).

---

## 3. Prose Changes to `task-complete.md`

Insert **Step 2a** immediately after the Write 1 call block in the "Step 2: Check Graphiti Availability and Write" section:

- After receiving the MCP response from `mcp__graphiti__add_memory`, call the helper to check for override:
  - Pass the response message string and the requested `group_id` (`"guardkit__task_outcomes"`) to `detect_group_override`.
  - If `.overridden` is True:
    - Display the `.warning` text (yellow inline warning, not a failure).
    - Immediately fire CLI fallback: `guardkit graphiti capture-outcome --from-task-file <path> --timeout 300`.
    - Display: `[Graphiti] MCP group overridden → re-sent via CLI to correct group`.
  - If `.overridden` is False (or `.actual` is None / unparseable): proceed normally.
- The MCP write is NOT retried via MCP — only the CLI path bypasses the coercion.
- Step 2a is non-blocking: if CLI fallback fails, display warning and continue.

---

## 4. Cleanup of the Two Misfiled Episodes

**Locate:**
`mcp__graphiti__get_episodes` with `group_id="product_knowledge"` and `last_n=20`. Scan results for `name == "Task Completion: TASK-FPSG-003"`. Expect exactly two matching entries. Record both UUIDs.

**Confirmation gate (mandatory before deletion):**
```
Found 2 misfiled episodes in 'product_knowledge':
  1. UUID: <uuid-1>  name: "Task Completion: TASK-FPSG-003"
  2. UUID: <uuid-2>  name: "Task Completion: TASK-FPSG-003"

These will be permanently deleted. Proceed? [y/N]
```
Do not proceed without explicit `y`. This is destructive against a live database.

**Delete:** `mcp__graphiti__delete_episode` for each UUID.

**Verify:** `mcp__graphiti__search_nodes` with `query="TASK-FPSG-003"` and `group_ids=["product_knowledge"]`. Assert zero results.

**Cleanup timing:** Standalone step before any file modification.

---

## 5. Test Plan

**File:** `tests/unit/commands/test_graphiti_response_parser.py`

Follows `importlib.util.spec_from_file_location` pattern (matching `test_smoke_gates_nudge.py`).

Test cases:

| Test | Input | Expected |
|------|-------|----------|
| `test_parse_queued_group_standard` | `"Episode 'X' queued for processing in group 'product_knowledge'"` | `"product_knowledge"` |
| `test_parse_queued_group_with_prefix` | `"Episode 'X' queued for processing in group 'guardkit__task_outcomes'"` | `"guardkit__task_outcomes"` |
| `test_parse_queued_group_no_match` | `"Some other message"` | `None` |
| `test_parse_queued_group_empty_string` | `""` | `None` |
| `test_detect_no_override` | requested=`"guardkit__task_outcomes"`, msg actual=`"guardkit__task_outcomes"` | `overridden=False`, `warning=None` |
| `test_detect_override_fires` | requested=`"guardkit__task_outcomes"`, msg actual=`"product_knowledge"` | `overridden=True`, `warning` non-empty |
| `test_detect_override_warning_content` | same as above | `warning` contains both group names |
| `test_detect_unparseable_response` | requested=`"guardkit__task_outcomes"`, msg=`""` | `overridden=False`, `actual=None` (safe default) |

No fixtures. No mocking. Coverage target: 100%.

---

## 6. Doc Updates

**`.claude/rules/graphiti-knowledge-graph.md`** — Add "Known Transport Limitation" warning under "Critical: Always Pass group_ids":

- HTTP MCP transport at `http://promaxgb10-41b1:8004/mcp` overrides client-supplied `group_id` with server default (`product_knowledge`).
- Detection: response message `"queued for processing in group '{actual}'"`.
- Workaround: `/task-complete` auto-detects + falls back to `guardkit graphiti capture-outcome` CLI.
- Direct MCP `add_memory` calls outside `/task-complete` still at risk — prefer CLI for writes that must land in specific group.

**`docs/guides/graphiti-claude-code-integration.md`** — Add "group_id coercion" subsection under Troubleshooting:

- Symptom: episodes appear in `product_knowledge` instead of requested group.
- Cause: HTTP MCP transport uses server-side default; client `group_id` not forwarded to FalkorDB.
- Detection pattern + CLI workaround (same as above).
- Status: upstream `graphiti-mcp` issue — see section 7.

---

## 7. Server-Side Investigation Outcome (AC #1)

No `infra/` directory in this repo. Server is on `promaxgb10-41b1`, out of scope here.

Likely causes (per task notes + observable schema):
- Upstream `graphiti-mcp` HTTP server doesn't forward `group_id` JSON body parameter to underlying `add_episode` call — uses only server-level config.
- HTTP transport schema accepts `group_id` but server implementation ignores it (stdio transport may behave differently).

**Realistic outcome: document-only, defer server fix to a separate infra task.** This task delivers detection + fallback + docs so future agents don't waste diagnosis time. Follow-up task should target `promaxgb10-41b1` host, not this repo.

---

## 8. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Destructive deletion hits wrong episode | High | Explicit UUID + name display with y/N gate before delete |
| MCP `get_episodes` doesn't support `group_id` filter | Medium | Fallback: retrieve last_n=50 and filter client-side by `name` |
| CLI fallback (`capture-outcome`) also fails | Low | Already non-blocking; warning + continue |
| Response message format changes upstream | Low | Parser returns `None` on no-match → safe default; add to doc |
| Re-capture produces third duplicate if parser bug | Medium | Verify cleanup confirmed complete before re-capture |

---

## 9. Estimated Effort

| File | LOC (new/changed) | Duration |
|------|-------------------|----------|
| `graphiti_response_parser.py` | ~60 | 20 min |
| `test_graphiti_response_parser.py` | ~90 | 20 min |
| `task-complete.md` prose edit | ~25 lines | 15 min |
| `graphiti-knowledge-graph.md` | ~15 lines | 10 min |
| `graphiti-claude-code-integration.md` | ~20 lines | 10 min |
| Episode cleanup (live MCP) | n/a | 10 min |
| Re-capture TASK-FPSG-003 | n/a | 5 min |
| **Total** | **~210 LOC** | **~90 min** |

Matches frontmatter complexity-4 / 90-min estimate.

---

## 10. Sequencing

1. **Episode cleanup** — destructive, time-sensitive, no code dependencies. Do first.
2. **Create `graphiti_response_parser.py`** — pure module.
3. **Create `test_graphiti_response_parser.py`** — depends on (2); run pytest to validate.
4. **Modify `task-complete.md`** — references module from (2).
5. **Doc updates** (`graphiti-knowledge-graph.md`, `graphiti-claude-code-integration.md`) — independent.
6. **Re-capture TASK-FPSG-003** — depends on (1) + (4). Use `guardkit graphiti capture-outcome --from-task-file ... --timeout 300`.
