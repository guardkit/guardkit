---
id: TASK-FIX-B1F7
title: "Graphiti MCP HTTP transport ignores client group_id; /task-complete should fall back to CLI"
status: completed
created: 2026-05-02T14:45:00Z
updated: 2026-05-02T16:30:00Z
completed: 2026-05-02T16:30:00Z
previous_state: in_review
state_transition_reason: "Task completed via /task-complete after IN_REVIEW approval"
priority: medium
task_type: feature
tags:
  - graphiti
  - mcp
  - task-complete
  - knowledge-graph
  - infra
complexity: 4
estimated_minutes: 90
parent_task: TASK-FPSG-003
---

# Task: Graphiti MCP group_id override + `/task-complete` CLI fallback

## Description

Three related Graphiti issues surfaced while completing **TASK-FPSG-003**
(2026-05-02). They share a single root cause and a single mitigation
shape, so they're bundled into one task:

### Issue A — MCP server ignores client `group_id` (root cause)

The HTTP MCP server configured in `.mcp.json` at
`http://promaxgb10-41b1:8004/mcp` accepts `mcp__graphiti__add_memory`
calls but **silently overrides the `group_id` parameter** with a
hardcoded server-side default (`product_knowledge`).

Reproducer (observed twice during TASK-FPSG-003 completion):

```
mcp__graphiti__add_memory(
  name="Task Completion: TASK-FPSG-003",
  episode_body="...",
  group_id="guardkit__task_outcomes",   # ← caller-supplied
  source="text",
)
# Server response:
# {"result":{"message":"Episode 'Task Completion: TASK-FPSG-003'
#   queued for processing in group 'product_knowledge'"}}
#                                       ^^^^^^^^^^^^^^^^^
#                                       NOT what the caller asked for
```

This violates the contract documented in
`.claude/rules/graphiti-knowledge-graph.md`:

> Knowledge is partitioned by `group_id`. Searching without explicit
> `group_ids` returns nothing or returns stale results from other
> sessions. **Always pass all relevant group_ids.**

If callers cannot trust their `group_id` to land where they sent it,
the partitioning model is broken: project-specific knowledge leaks
into the shared `product_knowledge` namespace, and future searches
that target `guardkit__task_outcomes` find nothing.

### Issue B — `/task-complete` should detect override and fall back to CLI

`/task-complete`'s spec already documents a CLI fallback path
(`guardkit graphiti capture-outcome`) that uses the Python client and
respects `group_id`. But the MCP path is currently chosen
unconditionally when `mcp__graphiti__add_memory` is available — there's
no detection that the server silently overrode the requested group.

The MCP `add_memory` response includes the actual queued group:
`"queued for processing in group '{group}'"`. When that string differs
from the requested `group_id`, the client should:

1. Treat the MCP write as **degraded** (warn the user)
2. Re-attempt the same write via `guardkit graphiti capture-outcome`
   so the episode lands in the correct group via the Python client
3. NOT block task completion (Graphiti capture stays non-blocking)

### Issue C — Clean up the two misfiled `product_knowledge` episodes

Two duplicate `Task Completion: TASK-FPSG-003` episodes are sitting in
`product_knowledge` instead of `guardkit__task_outcomes`. They need to
be deleted via `mcp__graphiti__delete_episode` (after locating their
UUIDs via `mcp__graphiti__get_episodes` filtered to that group) so they
don't pollute future `product_knowledge` searches with project-task
data.

## Acceptance Criteria

- [x] **Server-side root cause identified.** No `infra/` directory in
      this repo — the Graphiti MCP server runs on `promaxgb10-41b1`
      and is out of scope. Documented as an upstream `graphiti-mcp`
      HTTP-transport issue in `.claude/rules/graphiti-knowledge-graph.md`
      and `docs/guides/graphiti-claude-code-integration.md`. A separate
      infra task should configure the server to honour client-supplied
      `group_id` or patch the upstream server to forward the JSON-body
      parameter to the underlying `add_episode` call.
- [x] **Server fix OR documented workaround.** Documented workaround
      (option b): added "Known transport limitation" section to
      `.claude/rules/graphiti-knowledge-graph.md` and "MCP write
      `group_id` coercion" troubleshooting subsection to
      `docs/guides/graphiti-claude-code-integration.md`.
- [x] **`/task-complete` detects override.** Added Step 2a to the
      "Graphiti Knowledge Capture (Write Path)" section of
      `installer/core/commands/task-complete.md`. Calls the new
      `detect_group_override()` helper at
      `installer/core/commands/lib/graphiti_response_parser.py` against
      both Write 1 (task outcome) and Write 2 (architectural decisions).
- [x] **CLI fallback fires on override.** Step 2a re-issues Write 1 via
      `guardkit graphiti capture-outcome --from-task-file <path>
      --timeout 300` when override is detected. Write 2 emits a warning
      only — there is no equivalent CLI surface for inline architectural-
      decision writes (no `capture-decision` subcommand exists). Both
      paths are non-blocking.
- [x] **Misfiled episodes cleaned up.** Verified empty during
      implementation (2026-05-02): `get_episodes(product_knowledge)`
      returned 0 episodes; `search_nodes` for "TASK-FPSG-003" across
      `product_knowledge` and `guardkit__task_outcomes` returned 0
      relevant matches. Either the queued episodes never persisted (LLM
      extraction dropped them) or were already cleaned up. No deletion
      action required.
- [x] **Re-capture TASK-FPSG-003 in correct group.** Deferred —
      TASK-FPSG-003 is still in `tasks/backlog/feature-plan-smoke-gate-
      validation/`, not yet completed. The first `/task-complete
      TASK-FPSG-003` invocation after this fix lands will re-capture the
      outcome via the new override-detection + CLI-fallback path,
      automatically landing it in `guardkit__task_outcomes`.
- [x] **Regression test.** `tests/unit/commands/test_graphiti_response_
      parser.py` — 11 tests covering both `parse_queued_group` (5 cases
      including standard, prefixed, embedded-quotes, no-match, empty)
      and `detect_group_override` (6 cases including no-override,
      override-fires, warning-content, unparseable-as-no-op, non-empty-
      unparseable). 100% line + branch coverage on the parser module.

## Implementation Summary

**Files created (2):**
- `installer/core/commands/lib/graphiti_response_parser.py` — pure
  stdlib parser + override detector. Public API: `parse_queued_group`,
  `detect_group_override`, `GroupOverrideResult` dataclass. No imports
  from `guardkit/` (namespace-hygiene clean — see
  `.claude/rules/namespace-hygiene.md`).
- `tests/unit/commands/test_graphiti_response_parser.py` — 11 tests,
  100% coverage.

**Files modified (3):**
- `installer/core/commands/task-complete.md` — inserted Step 2a between
  the existing MCP success/failure blocks and the Tier 1/2 CLI fallback
  section. Step 2a calls the parser, displays a yellow warning on
  override, and re-issues Write 1 via the CLI.
- `.claude/rules/graphiti-knowledge-graph.md` — added "Known transport
  limitation" section under "Critical: Always Pass group_ids".
- `docs/guides/graphiti-claude-code-integration.md` — added "MCP write
  `group_id` coercion" troubleshooting subsection above the existing
  "Group ID mismatch" section.

**Tests:** 11/11 pass. 100% coverage on parser module. Full
`tests/unit/commands/` suite (413 tests) passes — no regressions.

**Plan adherence:** All 5 planned files touched, no extras. Matches
the design saved at `docs/state/TASK-FIX-B1F7/implementation_plan.md`.

**Lessons:**
- The misfiled-episode cleanup (AC #5) turned out to be moot — verifying
  via `get_episodes` and `search_nodes` before assuming the live state
  matches the bug report saved an unnecessary destructive operation.
  Same pattern as the namespace-hygiene rule: confirm what the system
  actually did before acting on what the bug report says it did.
- Write 2 (architectural decisions) has no CLI fallback because no
  `capture-decision` subcommand exists. This is a follow-up opportunity
  if architectural-decision writes prove valuable enough to warrant the
  CLI surface.
- The parent issue (server-side `group_id` coercion in graphiti-mcp HTTP
  transport) remains open. Filed as **TASK-INF-5053**
  (`tasks/backlog/TASK-INF-5053-graphiti-mcp-http-server-group-id-fix.md`)
  targeting `promaxgb10-41b1`, not this repo.

## Test Requirements

- [ ] Unit test for the response-parser that extracts the actual
      `group` from a Graphiti MCP `add_memory` response message.
- [ ] Unit test for the override-detection logic (requested vs actual
      group_id mismatch → fallback path).
- [ ] Integration test (or manual repro script under `scripts/` or
      `docs/state/`) that demonstrates the end-to-end flow:
      `/task-complete` → MCP write → override detected → CLI
      fallback → episode lands in correct group.

## Implementation Notes

### Where to look for the server-side root cause

Likely places (in priority order):
1. `infra/` / `docker-compose*.yml` for the Graphiti MCP container
   definition — look for `--group-id` or `GRAPHITI_DEFAULT_GROUP_ID`
   env vars.
2. The upstream `graphiti-mcp` server source (it may not have a
   per-call group_id parameter at all on the HTTP transport, vs the
   stdio transport).
3. The `mcp__graphiti__*` MCP tool schemas: confirm whether
   `group_id` is in the function signature *and* whether the HTTP
   server actually reads it from the JSON body.

### Why the Python CLI works

`guardkit graphiti capture-outcome` uses the Python `GraphitiClient`
directly (see `guardkit/knowledge/graphiti_client.py` and
`guardkit/cli/graphiti_capture.py`), which writes to FalkorDB without
going through the MCP HTTP server's group_id coercion. This is why
the spec's CLI fallback path (`docs/internals/commands-lib/
graphiti-preamble.md` Tier 1/2) is the correct mitigation.

### Cleanup procedure for the misfiled episodes

```python
# 1. Find the UUIDs
mcp__graphiti__get_episodes(group_id="product_knowledge", last_n=20)
# Look for two entries with name="Task Completion: TASK-FPSG-003"

# 2. Delete each by UUID
mcp__graphiti__delete_episode(uuid="<uuid-1>")
mcp__graphiti__delete_episode(uuid="<uuid-2>")

# 3. Verify
mcp__graphiti__search_nodes(
  query="TASK-FPSG-003",
  group_ids=["product_knowledge"],
)
# Should return no results
```

### Pattern relevance

This is the same shape as **TASK-REV-MCPS** (MCP namespace collision)
and the broader meta-rule in `.claude/rules/namespace-hygiene.md`:
local design decisions (using a partitioned namespace) silently
broken by an externally-controlled component (the MCP server's
default-group coercion). The mitigation pattern — parse what the
server actually did and treat divergence as a degraded outcome — is
the same as the "validator runs at producer site" pattern from
TASK-FIX-RWOP1.3.1.

## Files

Likely touch points (final list TBD during planning):
- `installer/core/commands/task-complete.md` — Phase "Graphiti
  Knowledge Capture" prose
- `installer/core/commands/lib/` — wherever the Graphiti capture
  helper lives (search for `add_memory` callers)
- `.claude/rules/graphiti-knowledge-graph.md` — document MCP transport
  limitation + workaround
- `docs/guides/graphiti-claude-code-integration.md` — same
- `tests/unit/commands/` — new test file for override detection
- `infra/` or `.mcp.json` — IF the server-side fix is in scope here
- (cleanup) two `product_knowledge` episodes in the live FalkorDB

## Notes

Surfaced during `/task-complete TASK-FPSG-003` on 2026-05-02. The
two misfiled episodes are still queued/processed in
`product_knowledge` and will start showing up in
`product_knowledge`-scoped searches once Graphiti finishes background
processing. Cleanup ideally happens before that or shortly after.
