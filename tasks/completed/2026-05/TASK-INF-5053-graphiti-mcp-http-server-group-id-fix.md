---
id: TASK-INF-5053
title: "Fix upstream graphiti-mcp HTTP server to honour client-supplied group_id"
status: completed
created: 2026-05-02T16:30:00Z
updated: 2026-05-03T10:30:00Z
completed: 2026-05-03T10:30:00Z
previous_state: in_review
state_transition_reason: "Task completed via /task-complete. Documented and closed per AC #2 option (c) — bug premise invalidated by direct verification against running server. Real issue (LLM endpoint misrouting) tracked as TASK-INF-5054."
completed_location: tasks/completed/2026-05/
priority: medium
task_type: feature
tags:
  - infra
  - graphiti
  - mcp
  - upstream
  - knowledge-graph
complexity: 5
estimated_minutes: 180
parent_task: TASK-FIX-B1F7
follow_up: TASK-INF-5054
---

# Task: Fix upstream `graphiti-mcp` HTTP server to honour client `group_id`

## Description

Root-cause fix for the bug surfaced and client-side-mitigated by
**TASK-FIX-B1F7**: the Graphiti MCP HTTP server at
`http://promaxgb10-41b1:8004/mcp` accepts `mcp__graphiti__add_memory`
calls with a `group_id` parameter but silently overrides it with a
server-side default (typically `product_knowledge`).

This task targets the **upstream server**, not this repo. The
client-side mitigation (override detection + CLI fallback in
`/task-complete`) is already in place from TASK-FIX-B1F7, but every
ad-hoc `mcp__graphiti__add_memory` call outside `/task-complete` is
still silently misfiled. The proper fix is server-side.

## Background

- Server location: `promaxgb10-41b1:8004` (Synology / Tailscale).
- Server-side config files for this MCP server are NOT in this repo's
  `infra/` directory — that directory does not exist. Investigation
  must start by locating the actual deployment artefacts on the host
  (likely a `docker-compose.yml` or `systemd` unit on
  `promaxgb10-41b1`).
- The bug: `group_id` is documented in the MCP tool schema and accepted
  in the HTTP request body, but the HTTP transport implementation
  apparently does not forward it to the underlying `add_episode` call
  — only the server-level config value is honoured.
- The MCP response message reveals the override:
  `Episode 'X' queued for processing in group '<actual>'`.

See **`.claude/rules/graphiti-knowledge-graph.md`** "Known transport
limitation" section and **TASK-FIX-B1F7** for full context.

## Acceptance Criteria

- [ ] **Locate the deployment artefacts.** SSH/Tailscale onto
      `promaxgb10-41b1`, identify the `graphiti-mcp` HTTP server
      container/process, and document the deployment config (compose
      file, env vars, CLI args, image tag/version).
- [ ] **Identify the override mechanism.** Determine why client
      `group_id` is ignored. Likely options:
      (a) The HTTP transport in this version of `graphiti-mcp` doesn't
          forward `group_id` from the JSON body to `add_episode`.
      (b) Server-side env var (e.g. `GRAPHITI_DEFAULT_GROUP_ID`) is
          coercing the value.
      (c) Single-tenant isolation enforced by design (in which case
          this task pivots to "document and close").
- [ ] **Apply server-side fix.** Either:
      (a) Update the server config so client `group_id` is honoured
          (env var change, server arg flip, or version upgrade), OR
      (b) Patch the upstream `graphiti-mcp` source if a forwarding bug
          is identified, OR
      (c) Document that the override is intentional and update
          `.claude/rules/graphiti-knowledge-graph.md` to make the
          client-side mitigation permanent.
- [ ] **Verify end-to-end.** From a fresh Claude Code session, call
      `mcp__graphiti__add_memory` with `group_id="guardkit__test_inf5053"`
      and confirm the response message reports the same group. Then
      `mcp__graphiti__get_episodes(group_ids=["guardkit__test_inf5053"])`
      returns the episode. Clean up the test episode after.
- [ ] **Update documentation.** Once fixed, update
      `.claude/rules/graphiti-knowledge-graph.md` and
      `docs/guides/graphiti-claude-code-integration.md` to remove the
      "Known transport limitation" warnings (or pin the warning to a
      specific server version range if the fix is version-gated).
- [ ] **Decide fate of client-side mitigation.** Once the server is
      fixed, the override-detection + CLI fallback in
      `installer/core/commands/task-complete.md` Step 2a becomes a
      defence-in-depth no-op. Decide whether to:
      (a) Keep it (cheap, defends against future regression), OR
      (b) Remove it (less prose to maintain).
      Recommend (a) unless the prose proves a maintenance burden.

## Test Requirements

- [ ] Manual end-to-end test from a Claude Code session (the AC #4
      verification) — there is no automated test surface for the
      remote server's behaviour.
- [ ] If a test fixture is added in this repo (e.g. a script under
      `scripts/` that exercises an MCP write and asserts the response
      group matches), document its expected exit codes and add it to
      the README.

## Implementation Notes

### Investigation starting points

1. **SSH to host**: `ssh promaxgb10-41b1` (assumes Tailscale + SSH key
   are configured for this user on this machine).
2. **Find the container**: `docker ps | grep -i graphiti` or
   `docker ps | grep 8004`.
3. **Inspect compose**: `docker inspect <container>` or read the
   compose file referenced in the inspect output.
4. **Check upstream**: The upstream project is likely
   `getzep/graphiti` (PyPI: `graphiti-core`). The MCP server may be a
   separate repo or a sibling under that org. Check the running image
   tag and find the corresponding source.
5. **Look for**: `GRAPHITI_DEFAULT_GROUP_ID` env var, `--group-id` CLI
   flag, hardcoded `group_id="product_knowledge"` in the server's
   `add_memory` handler, or a single-tenant config flag.

### Why this is medium-complexity, not low

- Requires shell access to a separate host outside this repo.
- May require upstream patch + redeploy, not just config change.
- Verification needs a Claude Code session against the live server.
- Documentation updates fan out to two files.

### Why this is medium-priority, not high

- Client-side mitigation is already in place (TASK-FIX-B1F7).
- Only ad-hoc `mcp__graphiti__add_memory` calls outside `/task-complete`
  are still affected. The bulk of automated knowledge writes go through
  `/task-complete` or the Python CLI, which both honour `group_id`.

### Pattern relevance

Same shape as **TASK-REV-MCPS** (MCP namespace collision) and
**TASK-FIX-B1F7** itself: a local design decision (group-based
partitioning) silently broken by an externally-controlled component.
See `.claude/rules/namespace-hygiene.md` for the broader meta-rule.

## Files

This task primarily touches infrastructure outside this repo. Likely
in-repo touch points (only after the server fix lands):

- `.claude/rules/graphiti-knowledge-graph.md` — remove or version-gate
  the "Known transport limitation" warning
- `docs/guides/graphiti-claude-code-integration.md` — same for the
  troubleshooting subsection
- `installer/core/commands/task-complete.md` — possibly remove Step 2a
  if the mitigation is decided to be redundant (see AC #6)
- `installer/core/commands/lib/graphiti_response_parser.py` — possibly
  delete (only if Step 2a is also removed)
- `tests/unit/commands/test_graphiti_response_parser.py` — same

Out-of-repo touch points (the actual fix):

- Deployment artefacts on `promaxgb10-41b1` (compose file, env vars,
  systemd unit, container image tag)
- Possibly an upstream `graphiti-mcp` PR if the bug is in source

## Notes

Filed 2026-05-02 as a follow-up to TASK-FIX-B1F7. The client-side
mitigation in TASK-FIX-B1F7 is sufficient for the `/task-complete`
path; this task closes the residual gap for ad-hoc MCP writes.

### Observation 2026-05-02 (during TASK-FIX-B1F7 completion)

The override was **NOT reproducible** when capturing TASK-FIX-B1F7's
own outcome via `mcp__graphiti__add_memory`. The server response was:

```
Episode 'Task Completion: TASK-FIX-B1F7' queued for processing
  in group 'guardkit__task_outcomes'
```

That is the requested group, not `product_knowledge`. Step 2a's
override detector correctly reported `overridden=False`. So either:

1. **Intermittent bug** — fired during TASK-FPSG-003 but not now.
2. **Recently fixed** — server config or upstream patch landed
   between 2026-05-02 morning (when TASK-FPSG-003 was attempted)
   and 2026-05-02 afternoon (when TASK-FIX-B1F7 completed).
3. **Group-name dependent** — perhaps only certain group names
   trigger the coercion (worth testing several when this task is
   picked up).

**Implication for this task**: First step on pickup should be to
**reproduce the bug**. If it no longer reproduces against a range of
group names, this task may downgrade to "verify the fix landed and
update docs" rather than a server-side investigation. Try writes to
`guardkit__project_decisions`, `guardkit__feature_specs`, and a fresh
unused group name to see if the coercion fires under any of them.

## Resolution (2026-05-02, /task-work session)

**Outcome: documented and closed (AC #2 option c).** The override bug
described in the original premise does not exist in the running
server. The full audit is in `docs/state/TASK-INF-5053/audit.md`;
key findings:

- Image `graphiti-mcp-standalone:local` (sha `2f486a69120c`) built
  2026-04-24, container restarted 2026-05-02T10:34Z. No code changes
  between the TASK-FIX-B1F7 reproducer (claimed 14:45Z) and this
  investigation.
- Source at `/app/mcp/src/graphiti_mcp_server.py:374-375` uses
  standard "client wins, fall back to default" routing
  (`effective_group_id = group_id or config.graphiti.group_id`).
- Live probe with `group_id="guardkit__test_inf5053"` returned
  response `Episode 'TASK-INF-5053 probe2' queued for processing in
  group 'guardkit__test_inf5053'` and the server log confirmed
  `services.queue_service - INFO - Processing episode None for
  group guardkit__test_inf5053`. No coercion observed.
- The "Observation 2026-05-02" note already in this task body
  corroborates: the same TASK-FIX-B1F7 author failed to reproduce
  the bug during their own completion.

**The actual root cause** of the symptom that motivated TASK-FIX-B1F7
("episode never appears under requested group on subsequent search")
is silent LLM-extraction failure: graphiti-core 0.28.1's `OpenAIClient`
calls `https://api.openai.com/v1/responses` instead of the configured
local LLM endpoint, because the MCP server's LLM factory `openai`
branch (`/app/mcp/src/services/factories.py:109-141`) silently
ignores `config.providers.openai.api_url`. Filed as **TASK-INF-5054**
(`tasks/backlog/TASK-INF-5054-graphiti-mcp-llm-endpoint-misrouting.md`).

### Acceptance criteria — final status

- [x] **AC #1 — Locate deployment artefacts.** Container is
      `graphiti-mcp` on `promaxgb10-41b1`, image
      `graphiti-mcp-standalone:local`, bootstrap and config mounted
      from this repo's `scripts/graphiti-mcp-{bootstrap.py,config.yaml}`.
      Documented in audit.
- [x] **AC #2 — Identify override mechanism.** None exists. Pivoted to
      option (c): document and close.
- [x] **AC #3 — Apply server-side fix.** Not applicable — no bug to
      fix. Documentation updated to reflect actual behaviour.
- [x] **AC #4 — Verify end-to-end.** Probe sent and confirmed against
      both the response message AND the server log. Test group
      `guardkit__test_inf5053` was used. The probe episode failed
      background extraction (TASK-INF-5054), so `get_episodes`
      returns nothing — but that's a separate issue and does not
      affect group_id routing verification.
- [x] **AC #5 — Update documentation.** Updated
      `.claude/rules/graphiti-knowledge-graph.md` (replaced "Known
      transport limitation" section) and
      `docs/guides/graphiti-claude-code-integration.md` (replaced
      "MCP write group_id coercion" troubleshooting subsection with
      "Episode written but not retrievable on search (LLM-extraction
      failure)" pointing at TASK-INF-5054).
- [x] **AC #6 — Decide fate of client-side mitigation.** Kept as
      defence-in-depth (option a). `installer/core/commands/task-complete.md`
      Step 2a heading and prose updated to reframe it from
      "addressing a known live bug" to "cheap regression insurance,
      no live bug observed". The 11-test parser suite remains the
      automated guard.

### Files modified

- `.claude/rules/graphiti-knowledge-graph.md` — replaced "Known
  transport limitation" section.
- `docs/guides/graphiti-claude-code-integration.md` — replaced "MCP
  write group_id coercion" troubleshooting subsection.
- `installer/core/commands/task-complete.md` — softened Step 2a
  heading + status note.
- `tasks/in_progress/TASK-INF-5053-...md` (this file) — added this
  Resolution section.
- `tasks/backlog/TASK-INF-5054-graphiti-mcp-llm-endpoint-misrouting.md`
  (NEW) — separate task for the real LLM-endpoint problem.
- `docs/state/TASK-INF-5053/audit.md` (NEW) — full investigation
  audit trail.

### Test cleanup

The probe episode `TASK-INF-5053 probe2` (group
`guardkit__test_inf5053`) never persisted past the queue (extraction
failed), so there is no node/edge to delete. No cleanup action needed.
Once TASK-INF-5054 is fixed and writes persist, this group can be
formally cleared via `mcp__graphiti__delete_episode` if any orphan
records exist.
